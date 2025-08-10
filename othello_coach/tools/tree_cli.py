from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
import logging
from ..logging_setup import setup_logging

from othello_coach.engine.board import start_board, Board
from othello_coach.trees.builder import build_tree, TreeBuilder
from othello_coach.gdl.parser import GDLParser, GDLParseError


def main() -> None:
    setup_logging(overwrite=False)
    p = argparse.ArgumentParser(prog="othello-tree", description="Build tree using presets or GDL")
    
    # Goal specification (mutually exclusive)
    goal_group = p.add_mutually_exclusive_group(required=True)
    goal_group.add_argument("--preset", choices=["score_side", "min_opp_mob", "early_corner"], 
                           help="Use a built-in preset goal")
    goal_group.add_argument("--gdl", help="GDL program string")
    goal_group.add_argument("--gdl-file", help="Path to GDL program file")
    
    # Tree parameters
    p.add_argument("--depth", type=int, default=8, help="Maximum tree depth (default: 8)")
    p.add_argument("--width", type=int, default=12, help="Maximum width per ply (default: 12)")
    p.add_argument("--time-ms", type=int, default=2000, help="Time limit in milliseconds (default: 2000)")
    
    # Root position
    p.add_argument("--root", type=int, help="Root position hash (default: start position)")
    p.add_argument("--root-moves", help="Comma-separated moves from start position")
    
    # Output
    p.add_argument("--out", required=True, help="Output file path")
    p.add_argument("--format", choices=["json", "dot", "png"], default="json", 
                   help="Output format (default: json)")
    
    # Options
    p.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = p.parse_args()
    
    try:
        # Determine root position
        if args.root:
            # Load from hash (would need database lookup)
            logging.getLogger(__name__).info("Loading position with hash %s...", args.root)
            root = start_board()  # Simplified - would load from DB
        elif args.root_moves:
            # Apply moves from start position
            root = start_board()
            moves = [int(m.strip()) for m in args.root_moves.split(',')]
            for move in moves:
                from othello_coach.engine.board import make_move
                root, _ = make_move(root, move)
            if args.verbose:
                logging.getLogger(__name__).info("Applied moves: %s", moves)
        else:
            root = start_board()
        
        if args.verbose:
            logging.getLogger(__name__).info("Root position: %s", root)
        
        # Build tree based on goal type
        if args.preset:
            # Use legacy preset system
            if args.verbose:
                logging.getLogger(__name__).info("Using preset: %s", args.preset)
            tree = build_tree(root, args.preset, depth=args.depth, width=args.width)
        else:
            # Use GDL system
            gdl_source = None
            if args.gdl:
                gdl_source = args.gdl
            elif args.gdl_file:
                with open(args.gdl_file, 'r') as f:
                    gdl_source = f.read()
            
            if not gdl_source:
                logging.getLogger(__name__).error("Error: No GDL program specified")
                sys.exit(1)
            
            if args.verbose:
                logging.getLogger(__name__).info("Parsing GDL program...")
                logging.getLogger(__name__).info("Source: %s", gdl_source)
            
            try:
                parser = GDLParser()
                program = parser.parse(gdl_source)
                
                if args.verbose:
                    logging.getLogger(__name__).info("Parsed GDL: %s", program)
                
                # Override parameters if specified
                if program.params:
                    if args.depth != 8:
                        program.params.max_depth = args.depth
                    if args.width != 12:
                        program.params.width = args.width
                
                # Build tree using GDL
                builder = TreeBuilder(program)
                tree = builder.build_tree(root, max_time_ms=args.time_ms)
                
            except GDLParseError as e:
                logging.getLogger(__name__).exception("GDL parse error: %s", e)
                if hasattr(e, 'line') and e.line > 0:
                    logging.getLogger(__name__).error("Line %s, column %s", e.line, e.column)
                sys.exit(1)
        
        # Generate output based on format
        if args.format == "json":
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(tree, f, indent=2)
            logging.getLogger(__name__).info("Wrote JSON tree to %s", args.out)
            
        elif args.format == "dot":
            # Export as DOT format
            from othello_coach.trees.export import export_dot
            dot_content = export_dot(tree)
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(dot_content)
            logging.getLogger(__name__).info("Wrote DOT graph to %s", args.out)
            
        elif args.format == "png":
            # Export as PNG
            from othello_coach.trees.export import export_png
            success = export_png(tree, args.out)
            if success:
                logging.getLogger(__name__).info("Wrote PNG image to %s", args.out)
            else:
                logging.getLogger(__name__).error("Failed to export PNG (graphviz not available?)")
                sys.exit(1)
        
        if args.verbose:
            node_count = len(tree.get('nodes', {}))
            edge_count = len(tree.get('edges', []))
            logging.getLogger(__name__).info("Tree statistics: %s nodes, %s edges", node_count, edge_count)
        
    except FileNotFoundError as e:
        logging.getLogger(__name__).exception("File not found: %s", e)
        sys.exit(1)
    except Exception as e:
        logging.getLogger(__name__).exception("Error building tree: %s", e)
        sys.exit(1)
