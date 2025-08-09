use crate::bitboards::*;

/// Generate legal move mask using precomputed ray approach
pub fn generate_legal_mask(b: u64, w: u64, stm: u8) -> u64 {
    let (own, opp) = if stm == 0 { (b, w) } else { (w, b) };
    let empty = !(b | w);
    let mut legal = 0u64;
    
    // For each direction
    for &dir in &DIRECTIONS {
        let mut captures = 0u64;
        let mut x = opp;
        let shifted = shift_dir(own, dir);
        let mut t = x & shifted;
        
        while t != 0 {
            captures |= t;
            t = x & shift_dir(t, dir);
        }
        
        legal |= shift_dir(captures, -dir) & empty;
    }
    
    legal
}

/// Generate flip mask for a specific move
pub fn generate_flip_mask(b: u64, w: u64, stm: u8, sq: u8) -> u64 {
    if sq >= 64 {
        return 0;
    }
    
    let (own, opp) = if stm == 0 { (b, w) } else { (w, b) };
    let move_bit = 1u64 << sq;
    
    // Check if square is empty
    if (b | w) & move_bit != 0 {
        return 0;
    }
    
    let mut flips = 0u64;
    
    // Check each direction
    for &dir in &DIRECTIONS {
        let mut temp_flips = 0u64;
        let mut pos = sq as i8;
        
        loop {
            pos += dir;
            if pos < 0 || pos >= 64 {
                break;
            }
            
            let pos_bit = 1u64 << pos;
            
            // Check bounds based on direction
            match dir {
                1 | 9 | -7 => if pos % 8 == 0 { break; }, // East-bound
                -1 | -9 | 7 => if pos % 8 == 7 { break; }, // West-bound
                _ => {}
            }
            
            if opp & pos_bit != 0 {
                temp_flips |= pos_bit;
            } else if own & pos_bit != 0 {
                flips |= temp_flips;
                break;
            } else {
                break; // Empty square
            }
        }
    }
    
    flips
}

/// Calculate potential mobility (opponent discs adjacent to empties)
pub fn calculate_potential_mobility(b: u64, w: u64, stm: u8) -> i16 {
    let (own, opp) = if stm == 0 { (b, w) } else { (w, b) };
    let empty = !(b | w);
    
    let mut adjacent_to_empty = 0u64;
    for &dir in &DIRECTIONS {
        adjacent_to_empty |= shift_dir(empty, dir);
    }
    
    let opp_potential = popcount(opp & adjacent_to_empty) as i16;
    let own_potential = popcount(own & adjacent_to_empty) as i16;
    
    own_potential - opp_potential
}
