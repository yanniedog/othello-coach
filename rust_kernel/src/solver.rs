use crate::bitboards::*;
use crate::movegen::*;
use crate::popcount::popcount;
use std::collections::HashMap;
use std::time::{Duration, Instant};

/// Exact solver for endgame positions (≤16 empties)
pub fn solve_exact(b: u64, w: u64, stm: u8, empties: u8, tt_mb: u32) -> i16 {
    if empties > 16 {
        return 0; // Fallback to evaluation
    }
    
    let mut solver = ExactSolver::new(tt_mb);
    solver.solve(b, w, stm, empties)
}

struct ExactSolver {
    tt: HashMap<u64, TTEntry>,
    nodes: u64,
    start_time: Instant,
    max_duration: Duration,
}

#[derive(Clone, Copy)]
struct TTEntry {
    score: i16,
    depth: u8,
}

impl ExactSolver {
    fn new(_tt_mb: u32) -> Self {
        Self {
            tt: HashMap::new(),
            nodes: 0,
            start_time: Instant::now(),
            max_duration: Duration::from_secs(30), // 30 second timeout
        }
    }
    
    fn solve(&mut self, b: u64, w: u64, stm: u8, empties: u8) -> i16 {
        self.nodes = 0;
        self.start_time = Instant::now();
        self.negamax(b, w, stm, empties, -6400, 6400)
    }
    
    fn negamax(&mut self, b: u64, w: u64, stm: u8, empties: u8, mut alpha: i16, beta: i16) -> i16 {
        self.nodes += 1;
        
        // Check timeout periodically (every 10000 nodes)
        if self.nodes % 10000 == 0 && self.start_time.elapsed() > self.max_duration {
            // Return evaluation instead of exact score on timeout
            return 0; // Neutral score fallback
        }
        
        // Prevent runaway memory usage - limit TT size
        if self.tt.len() > 50_000_000 {
            self.tt.clear();
        }
        
        // Terminal position
        if empties == 0 {
            let disc_diff = if stm == 0 {
                popcount(b) as i16 - popcount(w) as i16
            } else {
                popcount(w) as i16 - popcount(b) as i16
            };
            return disc_diff * 100;
        }
        
        // Generate hash for transposition table
        let hash = zobrist_hash(b, w, stm);
        
        // Check transposition table
        if let Some(entry) = self.tt.get(&hash) {
            if entry.depth >= empties {
                return entry.score;
            }
        }
        
        let legal = generate_legal_mask(b, w, stm);
        
        // No legal moves - pass
        if legal == 0 {
            let pass_legal = generate_legal_mask(b, w, 1 - stm);
            if pass_legal == 0 {
                // Game over
                let disc_diff = if stm == 0 {
                    popcount(b) as i16 - popcount(w) as i16
                } else {
                    popcount(w) as i16 - popcount(b) as i16
                };
                return disc_diff * 100;
            } else {
                // Pass to opponent
                return -self.negamax(b, w, 1 - stm, empties, -beta, -alpha);
            }
        }
        
        let mut best_score = -6400;
        
        // Try each legal move
        for sq in 0..64 {
            if (legal & (1u64 << sq)) != 0 {
                let flips = generate_flip_mask(b, w, stm, sq);
                let (new_b, new_w) = make_move(b, w, stm, sq, flips);
                
                let score = -self.negamax(new_w, new_b, 1 - stm, empties - 1, -beta, -alpha);
                
                if score > best_score {
                    best_score = score;
                    if score > alpha {
                        alpha = score;
                        if alpha >= beta {
                            break; // Beta cutoff
                        }
                    }
                }
            }
        }
        
        // Store in transposition table only if we have reasonable memory usage
        if self.tt.len() < 40_000_000 {
            self.tt.insert(hash, TTEntry {
                score: best_score,
                depth: empties,
            });
        }
        
        best_score
    }
}

/// Make a move and return new board state
fn make_move(b: u64, w: u64, stm: u8, sq: u8, flips: u64) -> (u64, u64) {
    let move_bit = 1u64 << sq;
    
    if stm == 0 {
        // Black to move
        let new_b = b | move_bit | flips;
        let new_w = w & !flips;
        (new_b, new_w)
    } else {
        // White to move
        let new_w = w | move_bit | flips;
        let new_b = b & !flips;
        (new_b, new_w)
    }
}

/// Simple Zobrist hash (simplified for solver)
fn zobrist_hash(b: u64, w: u64, stm: u8) -> u64 {
    // Simple hash combining position and side to move
    let mut hash = b ^ (w << 1);
    if stm == 1 {
        hash ^= 0x123456789ABCDEF0;
    }
    hash
}
