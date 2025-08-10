"""
Coordinate notation for Othello moves.

This module provides functions to convert between board coordinates (0-63) and
coordinate notation (e.g., 'a4', 'b2') for compact move representation in the database.
"""

# Special string for pass moves (no available moves)
PASS_NOTATION = '--'

def coord_to_notation(coord: int) -> str:
    """Convert board coordinate (0-63) to coordinate notation (e.g., 'e4')."""
    if coord < 0 or coord > 63:
        raise ValueError(f"Invalid coordinate: {coord}")
    
    file = coord % 8  # 0-7 (a-h)
    rank = coord // 8 + 1  # 1-8
    
    file_char = chr(ord('a') + file)
    return f"{file_char}{rank}"

def notation_to_coord(notation: str) -> int:
    """Convert coordinate notation (e.g., 'e4') to board coordinate (0-63)."""
    if notation == PASS_NOTATION:
        raise ValueError(f"Cannot convert pass notation '{PASS_NOTATION}' to coordinate")
    
    if len(notation) != 2:
        raise ValueError(f"Invalid notation format: {notation}")
    
    file_char = notation[0].lower()
    rank_char = notation[1]
    
    if not file_char.isalpha() or not rank_char.isdigit():
        raise ValueError(f"Invalid notation format: {notation}")
    
    file = ord(file_char) - ord('a')
    rank = int(rank_char) - 1
    
    if file < 0 or file > 7 or rank < 0 or rank > 7:
        raise ValueError(f"Invalid notation: {notation}")
    
    return rank * 8 + file

def moves_to_string(moves: list[int]) -> str:
    """Convert list of move coordinates to coordinate notation string."""
    if not moves:
        return ""
    return ''.join(coord_to_notation(move) for move in moves)

def string_to_moves(moves_str: str) -> list[int]:
    """Convert coordinate notation string to list of move coordinates."""
    if not moves_str:
        return []
    
    moves = []
    i = 0
    while i < len(moves_str):
        if i + 1 < len(moves_str) and moves_str[i:i+2] == PASS_NOTATION:
            # Handle pass move
            moves.append(-1)  # Use -1 to represent pass
            i += 2
        elif i + 1 < len(moves_str):
            # Handle regular move (2 characters)
            notation = moves_str[i:i+2]
            try:
                coord = notation_to_coord(notation)
                moves.append(coord)
            except ValueError:
                # Skip invalid notation
                pass
            i += 2
        else:
            # Skip incomplete notation at end
            break
    
    return moves

def is_valid_notation(moves_str: str) -> bool:
    """Check if a moves string contains valid coordinate notation."""
    if not moves_str:
        return True
    
    i = 0
    while i < len(moves_str):
        if i + 1 < len(moves_str) and moves_str[i:i+2] == PASS_NOTATION:
            i += 2
        elif i + 1 < len(moves_str):
            notation = moves_str[i:i+2]
            try:
                notation_to_coord(notation)
            except ValueError:
                return False
            i += 2
        else:
            return False
    
    return True

def get_coordinate_description(coord: int) -> str:
    """Get human-readable description of a board coordinate (e.g., 'e4')."""
    if coord < 0 or coord > 63:
        return "invalid"
    return coord_to_notation(coord)

def get_notation_description(notation: str) -> str:
    """Get human-readable description of a notation string."""
    if notation == PASS_NOTATION:
        return "pass"
    try:
        coord = notation_to_coord(notation)
        return get_coordinate_description(coord)
    except ValueError:
        return "invalid"

def format_moves_with_passes(moves: list[int], passes: list[int]) -> str:
    """Convert moves and pass information to coordinate notation string with passes.
    
    Args:
        moves: List of move coordinates
        passes: List of move indices after which passes occur (0-based)
    
    Returns:
        String with moves and passes interleaved
    """
    if not moves and not passes:
        return ""
    
    result = ""
    move_idx = 0
    pass_idx = 0
    
    # Process each move and check if a pass should follow
    for i, move in enumerate(moves):
        # Add the move
        result += coord_to_notation(move)
        
        # Check if a pass should follow this move
        if pass_idx < len(passes) and passes[pass_idx] == i:
            result += PASS_NOTATION
            pass_idx += 1
    
    # Handle case where there are only passes (no moves)
    if not moves and passes:
        for _ in passes:
            result += PASS_NOTATION
    
    return result
