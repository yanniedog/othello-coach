use crate::bitboards::*;

/// Calculate stability proxy using flood fill from corners and edges
pub fn calculate_stability_proxy(b: u64, w: u64) -> i16 {
    let black_stable = flood_stability(b, b | w);
    let white_stable = flood_stability(w, b | w);
    
    popcount(black_stable) as i16 - popcount(white_stable) as i16
}

/// Flood fill stability calculation from corners and safe edges
fn flood_stability(pieces: u64, all_pieces: u64) -> u64 {
    let mut stable = 0u64;
    let corners = 0x8100000000000081u64; // A1, H1, A8, H8
    
    // Start with corners
    stable |= pieces & corners;
    
    let mut changed = true;
    while changed {
        changed = false;
        let old_stable = stable;
        
        // Flood along ranks and files
        for &dir in &[1, -1, 8, -8] { // E, W, N, S
            let adjacent = shift_dir(stable, dir);
            let new_stable = pieces & adjacent & all_pieces;
            stable |= new_stable;
        }
        
        // Flood along diagonals
        for &dir in &[9, -9, 7, -7] { // NE, SW, NW, SE
            let adjacent = shift_dir(stable, dir);
            let new_stable = pieces & adjacent & all_pieces;
            stable |= new_stable;
        }
        
        if stable != old_stable {
            changed = true;
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
