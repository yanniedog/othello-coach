/// Population count utilities and bit manipulation

/// Fast population count using built-in instruction
#[inline]
pub fn popcount(x: u64) -> u32 {
    x.count_ones()
}
