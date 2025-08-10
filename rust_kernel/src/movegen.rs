use crate::bitboards::*;
use crate::popcount::popcount;

/// Generate legal move mask using simple ray casting
pub fn generate_legal_mask(b: u64, w: u64, stm: u8) -> u64 {
    let (own, opp) = if stm == 0 { (b, w) } else { (w, b) };
    let empty = !(b | w);
    let mut legal = 0u64;
    
    // Check each empty square
    for sq in 0..64 {
        let sq_bit = 1u64 << sq;
        if empty & sq_bit == 0 {
            continue; // Not empty
        }
        
        // Check if this square has valid moves in any direction
        for &dir in &DIRECTIONS {
            if has_captures_in_direction(own, opp, sq, dir) {
                legal |= sq_bit;
                break;
            }
        }
    }
    
    legal
}

/// Check if a move at square sq captures pieces in given direction
fn has_captures_in_direction(own: u64, opp: u64, sq: u8, dir: i8) -> bool {
    let mut pos = sq as i8;
    let mut captured_count = 0;
    
    // Walk in direction until we hit edge, empty square, or own piece
    loop {
        pos += dir;

        if pos < 0 || pos >= 64 {
            return false; // Hit edge
        }

        // Check for edge wrap-around
        match dir {
            1 | 9 | -7 => if pos % 8 == 0 { return false; }, // East-bound wrap
            -1 | -9 | 7 => if pos % 8 == 7 { return false; }, // West-bound wrap
            _ => {}
        }
        
        let pos_bit = 1u64 << pos;
        
        if opp & pos_bit != 0 {
            captured_count += 1;
        } else if own & pos_bit != 0 {
            return captured_count > 0; // Valid if we captured at least one opponent piece
        } else {
            return false; // Hit empty square
        }
    }
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
    
    opp_potential - own_potential
}
