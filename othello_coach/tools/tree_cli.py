from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from othello_coach.engine.board import start_board, Board
from othello_coach.trees.builder import build_tree, TreeBuilder
from othello_coach.gdl.parser import GDLParser, GDLParseError


def main() -> None:
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
            print(f"Loading position with hash {args.root}...")
            root = start_board()  # Simplified - would load from DB
        elif args.root_moves:
            # Apply moves from start position
            root = start_board()
            moves = [int(m.strip()) for m in args.root_moves.split(',')]
            for move in moves:
                from othello_coach.engine.board import make_move
                root = make_move(root, move)
            if args.verbose:
                print(f"Applied moves: {moves}")
        else:
            root = start_board()
        
        if args.verbose:
            print(f"Root position: {root}")
        
        # Build tree based on goal type
        if args.preset:
            # Use legacy preset system
            if args.verbose:
                print(f"Using preset: {args.preset}")
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
                print("Error: No GDL program specified", file=sys.stderr)
                sys.exit(1)
            
            if args.verbose:
                print(f"Parsing GDL program...")
                print(f"Source: {gdl_source}")
            
            try:
                parser = GDLParser()
                program = parser.parse(gdl_source)
                
                if args.verbose:
                    print(f"Parsed GDL: {program}")
                
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
                print(f"GDL parse error: {e}", file=sys.stderr)
                if hasattr(e, 'line') and e.line > 0:
                    print(f"Line {e.line}, column {e.column}", file=sys.stderr)
                sys.exit(1)
        
        # Generate output based on format
        if args.format == "json":
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(tree, f, indent=2)
            print(f"Wrote JSON tree to {args.out}")
            
        elif args.format == "dot":
            # Export as DOT format
            from othello_coach.trees.export import export_dot
            dot_content = export_dot(tree)
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(dot_content)
            print(f"Wrote DOT graph to {args.out}")
            
        elif args.format == "png":
            # Export as PNG
            from othello_coach.trees.export import export_png
            success = export_png(tree, args.out)
            if success:
                print(f"Wrote PNG image to {args.out}")
            else:
                print("Failed to export PNG (graphviz not available?)", file=sys.stderr)
                sys.exit(1)
        
        if args.verbose:
            node_count = len(tree.get('nodes', {}))
            edge_count = len(tree.get('edges', []))
            print(f"Tree statistics: {node_count} nodes, {edge_count} edges")
        
    except FileNotFoundError as e:
        print(f"File not found: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error building tree: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
