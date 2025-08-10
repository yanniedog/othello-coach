#!/usr/bin/env python3
"""
Demonstration of the new coordinate notation system for Othello moves.
"""

from othello_coach.engine.notation import (
    coord_to_notation,
    notation_to_coord,
    moves_to_string,
    string_to_moves,
    format_moves_with_passes,
    get_coordinate_description
)

def main():
    print("Othello Coordinate Notation System")
    print("=" * 40)
    
    # Show board coordinate mapping
    print("\nBoard Coordinate Mapping:")
    print("   a  b  c  d  e  f  g  h")
    for rank in range(8, 0, -1):
        row = f"{rank} "
        for file in range(8):
            coord = (rank - 1) * 8 + file
            notation = coord_to_notation(coord)
            row += f" {notation}"
        print(row)
    
    # Example moves
    print("\nExample Move Sequences:")
    
    # Simple opening sequence
    moves1 = [19, 26, 34, 37]  # d3, c4, c5, f5
    moves_str1 = moves_to_string(moves1)
    print(f"Opening moves: {moves1} -> '{moves_str1}'")
    
    # Convert back
    converted1 = string_to_moves(moves_str1)
    print(f"Converted back: '{moves_str1}' -> {converted1}")
    
    # Game with passes
    moves2 = [19, 26, 34]  # d3, c4, c5
    passes2 = [2]  # Pass after move 2
    moves_str2 = format_moves_with_passes(moves2, passes2)
    print(f"\nGame with passes: moves={moves2}, passes={passes2} -> '{moves_str2}'")
    
    # Convert back
    converted2 = string_to_moves(moves_str2)
    print(f"Converted back: '{moves_str2}' -> {converted2}")
    
    # Multiple passes
    moves3 = [19, 26, 34, 37]  # d3, c4, c5, f5
    passes3 = [1, 2]  # Pass after move 1 and 2
    moves_str3 = format_moves_with_passes(moves3, passes3)
    print(f"\nMultiple passes: moves={moves3}, passes={passes3} -> '{moves_str3}'")
    
    # Convert back
    converted3 = string_to_moves(moves_str3)
    print(f"Converted back: '{moves_str3}' -> {converted3}")
    
    # Edge cases
    print("\nEdge Cases:")
    print(f"Empty moves: '{moves_to_string([])}'")
    print(f"Only passes: '{format_moves_with_passes([], [0, 1])}'")
    
    # Human-readable descriptions
    print("\nHuman-Readable Descriptions:")
    for coord in [0, 27, 63]:  # a1, d4, h8
        desc = get_coordinate_description(coord)
        print(f"Coordinate {coord}: {desc}")
    
    print("\nNotation system is ready for use!")

if __name__ == "__main__":
    main()
