/// Bitboard constants and utilities

// File masks
pub const NOT_A: u64 = 0xFEFEFEFEFEFEFEFE;
pub const NOT_H: u64 = 0x7F7F7F7F7F7F7F7F;
pub const NOT_AB: u64 = 0xFCFCFCFCFCFCFCFC;
pub const NOT_GH: u64 = 0x3F3F3F3F3F3F3F3F;

// Direction deltas for 8x8 board
pub const DIRECTIONS: [i8; 8] = [8, -8, 1, -1, 9, 7, -7, -9]; // N, S, E, W, NE, NW, SE, SW

// Direction masks for edge checking
pub const DIR_MASKS: [u64; 8] = [
    0xFFFFFFFFFFFFFF00, // N: not rank 8
    0x00FFFFFFFFFFFFFF, // S: not rank 1  
    NOT_H,              // E: not file H
    NOT_A,              // W: not file A
    NOT_H,              // NE: not file H
    NOT_A,              // NW: not file A
    NOT_H,              // SE: not file H
    NOT_A,              // SW: not file A
];

/// Get bit at square
#[inline]
pub fn get_bit(board: u64, sq: u8) -> bool {
    (board & (1u64 << sq)) != 0
}

/// Set bit at square
#[inline]
pub fn set_bit(board: u64, sq: u8) -> u64 {
    board | (1u64 << sq)
}

/// Clear bit at square
#[inline]
pub fn clear_bit(board: u64, sq: u8) -> u64 {
    board & !(1u64 << sq)
}

/// Population count (number of set bits)
#[inline]
pub fn popcount(x: u64) -> u32 {
    x.count_ones()
}

/// Find first set bit (0-63, or 64 if none)
#[inline]
pub fn first_set_bit(x: u64) -> u8 {
    if x == 0 { 64 } else { x.trailing_zeros() as u8 }
}

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
