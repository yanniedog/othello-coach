/// Bitboard constants and utilities

// File masks
pub const NOT_A: u64 = 0xFEFEFEFEFEFEFEFE;
pub const NOT_H: u64 = 0x7F7F7F7F7F7F7F7F;

// Direction deltas for 8x8 board
pub const DIRECTIONS: [i8; 8] = [8, -8, 1, -1, 9, 7, -7, -9]; // N, S, E, W, NE, NW, SE, SW

/// Shift in a direction with bounds checking
#[inline]
pub fn shift_dir(board: u64, dir: i8) -> u64 {
    match dir {
        8 => board << 8,   // N
        -8 => board >> 8,  // S
        1 => (board & NOT_H) << 1,   // E
        -1 => (board & NOT_A) >> 1,  // W
        9 => (board & NOT_H) << 9,   // NE
        7 => (board & NOT_A) << 7,   // NW
        -7 => (board & NOT_H) >> 7,  // SE
        -9 => (board & NOT_A) >> 9,  // SW
        _ => 0,
    }
}
