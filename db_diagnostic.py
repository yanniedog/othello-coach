#!/usr/bin/env python3
"""
Database Diagnostic Tool for Othello Coach

This script validates the data shown in the Database Manager interface to ensure
accuracy and identify any discrepancies or data integrity issues.
"""

import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime
import json
from typing import Dict, List, Tuple, Any, Optional
import hashlib

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from othello_coach.tools.diag import DB_PATH, ensure_database
from othello_coach.engine.board import Board
from othello_coach.engine.notation import string_to_moves, coord_to_notation


class DatabaseDiagnostic:
    """Comprehensive database validation and diagnostic tool"""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self.conn = None
        self.cursor = None
        self.issues = []
        self.warnings = []
        
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        
    def connect(self):
        """Connect to the database"""
        try:
            self.conn = sqlite3.connect(str(self.db_path))
            self.cursor = self.conn.cursor()
            # Enable foreign key constraints
            self.cursor.execute("PRAGMA foreign_keys = ON")
            print(f"✅ Connected to database: {self.db_path}")
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            sys.exit(1)
            
    def disconnect(self):
        """Disconnect from the database"""
        if self.conn:
            self.conn.close()
            
    def log_issue(self, category: str, message: str, details: Dict[str, Any] = None):
        """Log an issue found during validation"""
        issue = {
            'category': category,
            'message': message,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
        self.issues.append(issue)
        print(f"❌ {category}: {message}")
        
    def log_warning(self, category: str, message: str, details: Dict[str, Any] = None):
        """Log a warning found during validation"""
        warning = {
            'category': category,
            'message': message,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
        self.warnings.append(warning)
        print(f"⚠️  {category}: {message}")
        
    def validate_schema(self) -> Dict[str, int]:
        """Validate database schema and return table counts"""
        print("\n🔍 Validating Database Schema...")
        
        # Check if all expected tables exist
        expected_tables = [
            'positions', 'analyses', 'moves', 'features', 'games', 
            'notes', 'trainer', 'ladders', 'mappings', 'gdl_programs'
        ]
        
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in self.cursor.fetchall()}
        
        missing_tables = set(expected_tables) - existing_tables
        if missing_tables:
            self.log_issue("Schema", f"Missing tables: {missing_tables}")
            
        # Get row counts for each table
        counts = {}
        for table in expected_tables:
            try:
                self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = self.cursor.fetchone()[0]
                counts[table] = count
                print(f"   {table}: {count:,} rows")
            except Exception as e:
                counts[table] = 0
                self.log_issue("Schema", f"Failed to count rows in {table}: {e}")
                
        return counts
        
    def validate_database_stats(self, counts: Dict[str, int]):
        """Validate the Database Stats tab data"""
        print("\n📊 Validating Database Stats...")
        
        # Verify each count matches what we calculated
        for table, expected_count in counts.items():
            try:
                self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
                actual_count = self.cursor.fetchone()[0]
                if actual_count != expected_count:
                    self.log_issue("Stats", f"Count mismatch for {table}: expected {expected_count}, got {actual_count}")
                else:
                    print(f"   ✅ {table}: {actual_count:,} rows")
            except Exception as e:
                self.log_issue("Stats", f"Failed to validate {table} count: {e}")
                
    def validate_ladder_standings(self):
        """Validate the Ladder Standings tab data"""
        print("\n🏆 Validating Ladder Standings...")
        
        try:
            # Get all ladder entries
            self.cursor.execute("""
                SELECT profile, rating, RD, last_rated_at, engine_ver
                FROM ladders 
                ORDER BY rating DESC
            """)
            results = self.cursor.fetchall()
            
            print(f"   Found {len(results)} ladder entries")
            
            # Validate each entry
            for profile, rating, rd, last_updated, engine_ver in results:
                # Check for reasonable rating values
                if not (0 <= rating <= 4000):
                    self.log_warning("Ladder", f"Unusual rating for {profile}: {rating}")
                    
                # Check for reasonable RD values
                if not (0 <= rd <= 1000):
                    self.log_warning("Ladder", f"Unusual RD for {profile}: {rd}")
                    
                # Check for valid timestamps
                if last_updated:
                    try:
                        dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                        if dt.year > 2030 or dt.year < 2020:
                            self.log_warning("Ladder", f"Unusual timestamp for {profile}: {last_updated}")
                    except Exception:
                        self.log_issue("Ladder", f"Invalid timestamp format for {profile}: {last_updated}")
                        
                print(f"   ✅ {profile}: Rating {rating:.0f}, RD {rd:.0f}, Updated {last_updated}")
                
        except Exception as e:
            self.log_issue("Ladder", f"Failed to validate ladder standings: {e}")
            
    def validate_recent_games(self):
        """Validate the Recent Games tab data"""
        print("\n🎮 Validating Recent Games...")
        
        try:
            # Get recent games
            self.cursor.execute("""
                SELECT id, result, length, tags, started_at, finished_at, moves, start_hash
                FROM games 
                ORDER BY started_at DESC 
                LIMIT 100
            """)
            results = self.cursor.fetchall()
            
            print(f"   Found {len(results)} recent games")
            
            # Validate each game
            for game_id, result, length, tags, started, finished, moves, start_hash in results:
                # Validate game ID
                if game_id <= 0:
                    self.log_issue("Games", f"Invalid game ID: {game_id}")
                    
                # Validate result (should be 0, 0.5, or 1)
                if result not in [0, 0.5, 1]:
                    self.log_warning("Games", f"Unusual result for game {game_id}: {result}")
                    
                # Validate length
                if length < 0 or length > 64:
                    self.log_warning("Games", f"Unusual game length for game {game_id}: {length}")
                    
                # Validate timestamps
                if started:
                    try:
                        start_dt = datetime.fromisoformat(started.replace('Z', '+00:00'))
                        if start_dt.year > 2030 or start_dt.year < 2020:
                            self.log_warning("Games", f"Unusual start time for game {game_id}: {started}")
                    except Exception:
                        self.log_issue("Games", f"Invalid start timestamp for game {game_id}: {started}")
                        
                if finished and finished != started:
                    try:
                        finish_dt = datetime.fromisoformat(finished.replace('Z', '+00:00'))
                        if finish_dt < start_dt:
                            self.log_issue("Games", f"Finish time before start time for game {game_id}")
                    except Exception:
                        self.log_issue("Games", f"Invalid finish timestamp for game {game_id}: {finished}")
                        
                # Validate moves
                if moves:
                    try:
                        move_coords = string_to_moves(moves)
                        if len(move_coords) != length:
                            self.log_warning("Games", f"Move count mismatch for game {game_id}: length={length}, moves={len(move_coords)}")
                    except Exception as e:
                        self.log_issue("Games", f"Invalid moves format for game {game_id}: {e}")
                        
                # Validate start_hash format
                if start_hash and len(start_hash) != 64:  # SHA-256 hash length
                    self.log_warning("Games", f"Unusual start_hash length for game {game_id}: {len(start_hash)}")
                    
                print(f"   ✅ Game {game_id}: Result {result}, Length {length}, Started {started}")
                
        except Exception as e:
            self.log_issue("Games", f"Failed to validate recent games: {e}")
            
    def validate_data_integrity(self):
        """Validate referential integrity and data consistency"""
        print("\n🔗 Validating Data Integrity...")
        
        # Check for orphaned analyses
        try:
            self.cursor.execute("""
                SELECT COUNT(*) FROM analyses a 
                LEFT JOIN positions p ON a.hash = p.hash 
                WHERE p.hash IS NULL
            """)
            orphaned_analyses = self.cursor.fetchone()[0]
            if orphaned_analyses > 0:
                self.log_issue("Integrity", f"Found {orphaned_analyses} orphaned analyses")
            else:
                print("   ✅ No orphaned analyses found")
        except Exception as e:
            self.log_warning("Integrity", f"Could not check orphaned analyses: {e}")
            
        # Check for orphaned moves
        try:
            self.cursor.execute("""
                SELECT COUNT(*) FROM moves m 
                LEFT JOIN positions p ON m.from_hash = p.hash 
                WHERE p.hash IS NULL
            """)
            orphaned_moves = self.cursor.fetchone()[0]
            if orphaned_moves > 0:
                self.log_issue("Integrity", f"Found {orphaned_moves} orphaned moves")
            else:
                print("   ✅ No orphaned moves found")
        except Exception as e:
            self.log_warning("Integrity", f"Could not check orphaned moves: {e}")
            
        # Check for orphaned features
        try:
            self.cursor.execute("""
                SELECT COUNT(*) FROM features f 
                LEFT JOIN positions p ON f.hash = p.hash 
                WHERE p.hash IS NULL
            """)
            orphaned_features = self.cursor.fetchone()[0]
            if orphaned_features > 0:
                self.log_issue("Integrity", f"Found {orphaned_features} orphaned features")
            else:
                print("   ✅ No orphaned features found")
        except Exception as e:
            self.log_warning("Integrity", f"Could not check orphaned features: {e}")
            
    def validate_performance(self):
        """Validate database performance and query execution"""
        print("\n⚡ Validating Performance...")
        
        # Test the exact queries used by the Database Manager
        queries = {
            "Stats Count": "SELECT COUNT(1) FROM positions",
            "Ladder Query": "SELECT profile, rating, RD, last_rated_at FROM ladders ORDER BY rating DESC",
            "Games Query": "SELECT id, result, length, tags, started_at, finished_at, moves FROM games ORDER BY started_at DESC LIMIT 50"
        }
        
        for name, query in queries.items():
            try:
                start_time = datetime.now()
                self.cursor.execute(query)
                results = self.cursor.fetchall()
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                if duration > 1.0:
                    self.log_warning("Performance", f"{name} took {duration:.3f}s (slow)")
                else:
                    print(f"   ✅ {name}: {duration:.3f}s ({len(results)} results)")
                    
            except Exception as e:
                self.log_issue("Performance", f"{name} failed: {e}")
                
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive diagnostic report"""
        print("\n📋 Generating Diagnostic Report...")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'database_path': str(self.db_path),
            'database_size_mb': self.db_path.stat().st_size / (1024 * 1024) if self.db_path.exists() else 0,
            'issues': self.issues,
            'warnings': self.warnings,
            'summary': {
                'total_issues': len(self.issues),
                'total_warnings': len(self.warnings),
                'critical_issues': len([i for i in self.issues if 'Integrity' in i['category']]),
                'data_issues': len([i for i in self.issues if 'Games' in i['category'] or 'Ladder' in i['category']]),
                'performance_issues': len([i for i in self.issues if 'Performance' in i['category']])
            }
        }
        
        # Print summary
        print(f"\n📊 DIAGNOSTIC SUMMARY:")
        print(f"   Total Issues: {report['summary']['total_issues']}")
        print(f"   Total Warnings: {report['summary']['total_warnings']}")
        print(f"   Critical Issues: {report['summary']['critical_issues']}")
        print(f"   Data Issues: {report['summary']['data_issues']}")
        print(f"   Performance Issues: {report['summary']['performance_issues']}")
        
        if report['summary']['total_issues'] == 0:
            print("   🎉 Database appears to be healthy!")
        else:
            print("   ⚠️  Issues found - review details above")
            
        return report
        
    def run_full_diagnostic(self):
        """Run the complete diagnostic suite"""
        print("🚀 Starting Database Diagnostic...")
        print(f"Database: {self.db_path}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        try:
            # Ensure database exists
            if not self.db_path.exists():
                print("Database does not exist, creating...")
                ensure_database()
                
            # Run all validation steps
            counts = self.validate_schema()
            self.validate_database_stats(counts)
            self.validate_ladder_standings()
            self.validate_recent_games()
            self.validate_data_integrity()
            self.validate_performance()
            
            # Generate final report
            report = self.generate_report()
            
            # Save report to file
            report_path = self.db_path.parent / f"db_diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            print(f"\n📄 Detailed report saved to: {report_path}")
            
            return report
            
        except Exception as e:
            self.log_issue("System", f"Diagnostic failed: {e}")
            return None


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database Diagnostic Tool for Othello Coach")
    parser.add_argument("--db-path", help="Path to database file (default: auto-detect)")
    parser.add_argument("--output", help="Output file for detailed report")
    parser.add_argument("--quick", action="store_true", help="Run quick validation only")
    
    args = parser.parse_args()
    
    db_path = Path(args.db_path) if args.db_path else None
    
    with DatabaseDiagnostic(db_path) as diag:
        if args.quick:
            # Quick validation
            counts = diag.validate_schema()
            diag.validate_database_stats(counts)
            diag.validate_ladder_standings()
            diag.validate_recent_games()
        else:
            # Full diagnostic
            report = diag.run_full_diagnostic()
            
            if args.output and report:
                with open(args.output, 'w') as f:
                    json.dump(report, f, indent=2)
                print(f"Report saved to: {args.output}")


if __name__ == "__main__":
    main()
