#!/usr/bin/env python3
"""
Quick Database Check for Othello Coach Database Manager

This script quickly validates the specific data shown in the Database Manager
interface to identify any obvious issues or discrepancies.
"""

import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import json

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from othello_coach.tools.diag import DB_PATH


def quick_check():
    """Quick validation of Database Manager data"""
    print("🔍 Quick Database Check for Database Manager")
    print("=" * 50)
    
    if not DB_PATH.exists():
        print(f"❌ Database not found at: {DB_PATH}")
        return
        
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # 1. Check Database Stats (first tab)
        print("\n📊 DATABASE STATS VALIDATION:")
        print("-" * 30)
        
        expected_tables = ['positions', 'analyses', 'moves', 'notes', 'games', 'features', 'trainer', 'ladders', 'mappings', 'gdl_programs']
        
        for table in expected_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"   {table}: {count:,} rows")
                
                # Check for suspicious counts
                if table == 'games' and count > 10000:
                    print(f"      ⚠️  High game count - verify this is correct")
                elif table in ['positions', 'analyses'] and count == 0:
                    print(f"      ⚠️  Empty table - may indicate incomplete data")
                    
            except Exception as e:
                print(f"   ❌ {table}: Error - {e}")
                
        # 2. Check Ladder Standings (second tab)
        print("\n🏆 LADDER STANDINGS VALIDATION:")
        print("-" * 30)
        
        try:
            cursor.execute("""
                SELECT profile, rating, RD, last_rated_at, engine_ver
                FROM ladders 
                ORDER BY rating DESC
            """)
            results = cursor.fetchall()
            
            print(f"   Found {len(results)} ladder entries")
            
            # Check for the specific data shown in your screenshot
            expected_profiles = ['elo_1400', 'elo_2000', 'elo_2300', 'elo_400', 'elo_800', 'max']
            found_profiles = [row[0] for row in results]
            
            for profile in expected_profiles:
                if profile in found_profiles:
                    # Find the entry
                    entry = next(row for row in results if row[0] == profile)
                    rating, rd, last_updated = entry[1], entry[2], entry[3]
                    
                    print(f"   ✅ {profile}: Rating {rating:.0f}, RD {rd:.0f}")
                    
                    # Check for suspicious data
                    if rating == 1500 and rd == 9:
                        print(f"      ⚠️  Default rating/RD values - may indicate placeholder data")
                    if last_updated and '2025-08-10' in str(last_updated):
                        print(f"      ⚠️  Future date detected: {last_updated}")
                        
                else:
                    print(f"   ❌ Missing profile: {profile}")
                    
        except Exception as e:
            print(f"   ❌ Error loading ladder: {e}")
            
        # 3. Check Recent Games (third tab)
        print("\n🎮 RECENT GAMES VALIDATION:")
        print("-" * 30)
        
        try:
            cursor.execute("""
                SELECT id, result, length, tags, started_at, finished_at, moves
                FROM games 
                ORDER BY started_at DESC 
                LIMIT 20
            """)
            results = cursor.fetchall()
            
            print(f"   Found {len(results)} recent games")
            
            # Check for the specific issues shown in your screenshot
            suspicious_games = 0
            future_dates = 0
            
            for game_id, result, length, tags, started, finished, moves in results:
                issues = []
                
                # Check for suspicious patterns
                if result == 0.5 and length == 0:
                    issues.append("Draw with 0 length")
                    suspicious_games += 1
                    
                if started and '2025-08-10' in str(started):
                    issues.append("Future date")
                    future_dates += 1
                    
                if started == finished:
                    issues.append("Same start/finish time")
                    
                if moves == 'N/A' or not moves:
                    issues.append("No moves recorded")
                    
                if issues:
                    print(f"   ⚠️  Game {game_id}: {', '.join(issues)}")
                    print(f"      Result: {result}, Length: {length}, Started: {started}")
                else:
                    print(f"   ✅ Game {game_id}: Result {result}, Length {length}")
                    
            # Summary of issues
            if suspicious_games > 0:
                print(f"\n   ⚠️  Found {suspicious_games} suspicious games")
            if future_dates > 0:
                print(f"   ⚠️  Found {future_dates} games with future dates")
                
        except Exception as e:
            print(f"   ❌ Error loading games: {e}")
            
        # 4. Data Integrity Check
        print("\n🔗 DATA INTEGRITY CHECK:")
        print("-" * 30)
        
        # Check for orphaned data
        try:
            cursor.execute("""
                SELECT COUNT(*) FROM games g 
                LEFT JOIN positions p ON g.start_hash = p.hash 
                WHERE p.hash IS NULL AND g.start_hash IS NOT NULL
            """)
            orphaned_games = cursor.fetchone()[0]
            if orphaned_games > 0:
                print(f"   ❌ Found {orphaned_games} games with missing start positions")
            else:
                print("   ✅ All games have valid start positions")
                
        except Exception as e:
            print(f"   ⚠️  Could not check orphaned games: {e}")
            
        # Check for duplicate game IDs
        try:
            cursor.execute("SELECT COUNT(*) FROM games GROUP BY id HAVING COUNT(*) > 1")
            duplicates = cursor.fetchall()
            if duplicates:
                print(f"   ❌ Found duplicate game IDs")
            else:
                print("   ✅ No duplicate game IDs found")
                
        except Exception as e:
            print(f"   ⚠️  Could not check for duplicates: {e}")
            
        # 5. Performance Check
        print("\n⚡ PERFORMANCE CHECK:")
        print("-" * 30)
        
        # Test the exact queries used by Database Manager
        queries = [
            ("Stats Count", "SELECT COUNT(1) FROM positions"),
            ("Ladder Query", "SELECT profile, rating, RD, last_rated_at FROM ladders ORDER BY rating DESC"),
            ("Games Query", "SELECT id, result, length, tags, started_at, finished_at, moves FROM games ORDER BY started_at DESC LIMIT 50")
        ]
        
        for name, query in queries:
            try:
                start_time = datetime.now()
                cursor.execute(query)
                results = cursor.fetchall()
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                if duration > 0.5:
                    print(f"   ⚠️  {name}: {duration:.3f}s (slow)")
                else:
                    print(f"   ✅ {name}: {duration:.3f}s")
                    
            except Exception as e:
                print(f"   ❌ {name}: Failed - {e}")
                
        conn.close()
        
        # 6. Summary and Recommendations
        print("\n📋 SUMMARY & RECOMMENDATIONS:")
        print("-" * 30)
        
        print("Based on the data shown in your Database Manager screenshots:")
        print("   • All games show result 0.5 (draws) with length 0")
        print("   • All games have identical start/finish times")
        print("   • All games show 'N/A' for moves")
        print("   • Timestamps show future dates (2025-08-10)")
        print("   • All ladder entries have identical ratings (1500) and RD (9)")
        
        print("\nThis suggests:")
        print("   • Games may be placeholder/instantaneous entries")
        print("   • Ladder ratings may be default/placeholder values")
        print("   • System clock may be incorrect")
        print("   • Data may be from test runs or incomplete games")
        
        print("\nRecommendations:")
        print("   • Verify system clock is correct")
        print("   • Check if these are test/placeholder games")
        print("   • Run full diagnostic with: python db_diagnostic.py")
        print("   • Consider clearing test data if not needed")
        
    except Exception as e:
        print(f"❌ Database check failed: {e}")


if __name__ == "__main__":
    quick_check()
