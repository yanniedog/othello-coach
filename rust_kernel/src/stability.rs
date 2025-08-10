use crate::bitboards::*;
use crate::popcount::popcount;

/// Calculate stability proxy using same algorithm as Python
pub fn calculate_stability_proxy(b: u64, w: u64) -> i16 {
    let black_stable = stable_count(b, w);
    let white_stable = stable_count(w, b);
    
    black_stable as i16 - white_stable as i16
}

/// Stable count matching Python algorithm exactly  
fn stable_count(mask_color: u64, _mask_other: u64) -> u32 {
    let mut stable = 0u32;
    let corners = [0, 7, 56, 63]; // A1, H1, A8, H8
    
    for &corner in &corners {
        if (mask_color & (1u64 << corner)) == 0 {
            continue; // No piece at this corner
        }
        
        // Extend along two edges from the corner
        let directions = match corner {
            0 => [1, 8],      // A1: East, North
            7 => [-1, 8],     // H1: West, North  
            56 => [1, -8],    // A8: East, South
            63 => [-1, -8],   // H8: West, South
            _ => [0, 0],      // Should never happen
        };
        
        for &d in &directions {
            if d == 0 { continue; }
            
            let mut cur = corner as i8;
            loop {
                let nr = cur + d;
                if nr < 0 || nr >= 64 {
                    break;
                }
                
                // Stop at edge crossings  
                if d == 1 && (nr % 8 == 0) {
                    break;
                }
                if d == -1 && (nr % 8 == 7) {
                    break;
                }
                
                if (mask_color & (1u64 << nr)) == 0 {
                    break; // No piece here
                }
                
                stable += 1;
                cur = nr;
            }
        }
    }
    
    stable
}

/// Calculate parity regions (empty regions and their controllers)
pub fn calculate_parity_regions(b: u64, w: u64) -> Vec<(u64, u8)> {
    let empty = !(b | w);
    let mut visited = 0u64;
    let mut regions = Vec::new();
    
    for sq in 0..64 {
        let sq_bit = 1u64 << sq;
        if (empty & sq_bit) != 0 && (visited & sq_bit) == 0 {
            let (region_mask, size) = flood_region(empty, sq, &mut visited);
            if size >= 3 { // Only consider regions of size 3+
                let controller = determine_controller(region_mask, b, w);
                regions.push((region_mask, controller));
            }
        }
    }
    
    regions
}

/// Flood fill to find connected empty region
fn flood_region(empty: u64, start_sq: u8, visited: &mut u64) -> (u64, u8) {
    let mut region = 0u64;
    let mut stack = vec![start_sq];
    let mut size = 0u8;
    
    while let Some(sq) = stack.pop() {
        let sq_bit = 1u64 << sq;
        if (*visited & sq_bit) != 0 || (empty & sq_bit) == 0 {
            continue;
        }
        
        *visited |= sq_bit;
        region |= sq_bit;
        size += 1;
        
        // Add adjacent squares
        for &dir in &DIRECTIONS {
            let new_sq = sq as i8 + dir;
            if new_sq >= 0 && new_sq < 64 {
                // Check bounds for wrap-around
                let valid = match dir {
                    1 | 9 | -7 => sq % 8 != 7,  // East-bound
                    -1 | -9 | 7 => sq % 8 != 0, // West-bound
                    _ => true,
                };
                if valid {
                    stack.push(new_sq as u8);
                }
            }
        }
    }
    
    (region, size)
}

/// Determine which player controls a region (has more adjacent pieces)
fn determine_controller(region: u64, b: u64, w: u64) -> u8 {
    let mut black_adjacent = 0u64;
    let mut white_adjacent = 0u64;
    
    for &dir in &DIRECTIONS {
        black_adjacent |= shift_dir(region, dir) & b;
        white_adjacent |= shift_dir(region, dir) & w;
    }
    
    let black_count = popcount(black_adjacent);
    let white_count = popcount(white_adjacent);
    
    if black_count > white_count {
        0 // Black controls
    } else if white_count > black_count {
        1 // White controls
    } else {
        2 // Neutral/contested
    }
}
