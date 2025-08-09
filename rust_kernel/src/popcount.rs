/// Population count utilities and bit manipulation

/// Fast population count using built-in instruction
#[inline]
pub fn popcount(x: u64) -> u32 {
    x.count_ones()
}

/// Population count for multiple bitboards
pub fn popcount_multiple(boards: &[u64]) -> Vec<u32> {
    boards.iter().map(|&b| popcount(b)).collect()
}

/// Find all set bits in a bitboard
pub fn get_set_bits(mut board: u64) -> Vec<u8> {
    let mut bits = Vec::new();
    while board != 0 {
        let lsb = board.trailing_zeros() as u8;
        bits.push(lsb);
        board &= board - 1; // Clear least significant bit
    }
    bits
}

/// Count set bits in each rank
pub fn popcount_by_rank(board: u64) -> [u32; 8] {
    let mut counts = [0u32; 8];
    for rank in 0..8 {
        let rank_mask = 0xFFu64 << (rank * 8);
        counts[rank] = popcount(board & rank_mask);
    }
    counts
}

/// Count set bits in each file
pub fn popcount_by_file(board: u64) -> [u32; 8] {
    let mut counts = [0u32; 8];
    for file in 0..8 {
        let file_mask = 0x0101010101010101u64 << file;
        counts[file] = popcount(board & file_mask);
    }
    counts
}
