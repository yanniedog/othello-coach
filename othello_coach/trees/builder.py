from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

from othello_coach.engine.board import Board, make_move, legal_moves_mask
from .presets import get_preset


@dataclass
class TreeNode:
    stm: int
    score: int
    attrs: dict


class TreeBuilder:
    """GDL-aware tree builder for v1.1"""
    
    def __init__(self, gdl_program=None):
        self.gdl_program = gdl_program
        self.alpha = 1.0  # Primary goal weight
        self.beta = 0.1   # PV bias weight
        self.gamma = 0.3  # Novelty weight
        
        # Load novelty radar if available
        self.novelty_radar = None
        try:
            from ..novelty.radar import NoveltyRadar
            self.novelty_radar = NoveltyRadar()
        except ImportError:
            pass
    
    def build_tree(self, root: Board, max_depth: int = None, width: int = None, 
                   max_time_ms: int = 2000) -> dict:
        """Build tree using GDL goal"""
        start = time.perf_counter()
        
        # Get parameters from GDL or defaults
        if self.gdl_program and self.gdl_program.params:
            max_depth = max_depth or self.gdl_program.params.max_depth
            width = width or self.gdl_program.params.width
        
        max_depth = max_depth or 8
        width = width or 12
        
        # Initialize tree structures
        nodes: Dict[int, TreeNode] = {root.hash: TreeNode(root.stm, 0, {})}
        edges: List[dict] = []
        frontier: List[Tuple[float, float, Board, int, List[int]]] = []  # (priority, novelty, board, depth, move_history)
        
        # Get scorer function
        scorer = self._get_scorer()
        root_score = scorer(root)
        
        # Initialize with root
        frontier.append((root_score + 0.01, 1.0, root, 0, []))
        
        while frontier and len(nodes) < 1000 and (time.perf_counter() - start) * 1000 < max_time_ms:
            # Best-first: pop max priority
            frontier.sort(key=lambda t: (t[0], t[1]), reverse=True)
            cur_priority, cur_novelty, cur, d, move_history = frontier.pop(0)
            
            if d >= max_depth:
                continue
            
            mask = legal_moves_mask(cur)
            legal_moves = []
            m = mask
            while m:
                lsb = m & -m
                sq = lsb.bit_length() - 1
                legal_moves.append(sq)
                m ^= lsb
            
            # Apply move ordering preferences
            legal_moves = self._order_moves(cur, legal_moves)
            
            # Expand up to width moves
            for i, sq in enumerate(legal_moves[:width]):
                b2, _ = make_move(cur, sq)
                new_move_history = move_history + [sq]
                
                # Calculate scores
                primary_score = scorer(b2)
                pv_bonus = 0.001 * (max_depth - d)
                
                # Calculate novelty
                novelty_score = self._calculate_novelty(b2, new_move_history)
                
                # Combined priority
                priority = (self.alpha * primary_score + 
                           self.beta * pv_bonus + 
                           self.gamma * novelty_score)
                
                # Add node if not seen
                if b2.hash not in nodes:
                    nodes[b2.hash] = TreeNode(b2.stm, int(primary_score), {
                        'novelty': novelty_score,
                        'depth': d + 1
                    })
                    frontier.append((priority, novelty_score, b2, d + 1, new_move_history))
                
                edges.append({
                    "from": cur.hash, 
                    "to": b2.hash, 
                    "move": sq, 
                    "score": int(primary_score)
                })
        
        return {
            "root": root.hash, 
            "nodes": {h: {"stm": n.stm, "score": n.score, "attrs": n.attrs} for h, n in nodes.items()}, 
            "edges": edges
        }
    
    def _get_scorer(self):
        """Get scoring function from GDL goal"""
        if not self.gdl_program:
            # Fallback to default scorer
            return lambda board: 0
        
        goal = self.gdl_program.goal
        
        if goal.goal_type == 'score':
            # Maximize eval for specified side
            from ..engine.eval import evaluate_position
            if goal.side == 'stm':
                return lambda board: evaluate_position(board)
            elif goal.side == 'white':
                return lambda board: evaluate_position(board) if board.stm == 1 else -evaluate_position(board)
            elif goal.side == 'black':
                return lambda board: evaluate_position(board) if board.stm == 0 else -evaluate_position(board)
        
        elif goal.goal_type == 'min_opp_mob':
            # Minimize opponent mobility
            def mobility_scorer(board):
                from ..engine.movegen_fast import generate_legal_mask
                opp_legal = generate_legal_mask(board.B, board.W, 1 - board.stm)
                return -bin(opp_legal).count('1')
            return mobility_scorer
        
        elif goal.goal_type == 'earliest_corner':
            # Reward corner capture within max_plies
            def corner_scorer(board):
                corners = 0x8100000000000081  # A1, H1, A8, H8
                own_corners = bin((board.B if board.stm == 0 else board.W) & corners).count('1')
                return own_corners * 500
            return corner_scorer
        
        elif goal.goal_type == 'max_stability':
            # Maximize stability
            def stability_scorer(board):
                try:
                    import rust_kernel
                    return rust_kernel.stability_proxy(board.B, board.W)
                except ImportError:
                    from ..insights.features import extract_features
                    features = extract_features(board)
                    return features.get('stability_proxy', 0)
            return stability_scorer
        
        elif goal.goal_type == 'custom':
            # Custom weighted combination
            def custom_scorer(board):
                from ..insights.features import extract_features
                features = extract_features(board)
                
                score = 0.0
                for feature_name, weight in goal.weights.items():
                    if feature_name in features:
                        score += weight * features[feature_name]
                
                return score
            return custom_scorer
        
        # Fallback
        return lambda board: 0
    
    def _order_moves(self, board: Board, moves: List[int]) -> List[int]:
        """Order moves based on preferences"""
        if not self.gdl_program or not self.gdl_program.params or not self.gdl_program.params.prefer:
            return moves
        
        prefer = self.gdl_program.params.prefer
        
        if prefer == 'corners':
            # Prioritize corners
            corners = {0, 7, 56, 63}
            corner_moves = [m for m in moves if m in corners]
            other_moves = [m for m in moves if m not in corners]
            return corner_moves + other_moves
        
        elif prefer == 'mobility':
            # Prioritize high-mobility moves (simplified)
            return moves  # Would implement proper mobility sorting
        
        elif prefer == 'stability':
            # Prioritize stability-enhancing moves (simplified)
            return moves  # Would implement proper stability sorting
        
        return moves
    
    def _calculate_novelty(self, board: Board, move_history: List[int]) -> float:
        """Calculate novelty score for position"""
        if self.novelty_radar and len(move_history) >= 3:
            try:
                # Convert move history to boards
                boards = self._moves_to_boards(move_history)
                scores = [0.0] * len(boards)  # Simplified
                
                novelty_score = self.novelty_radar.score_novelty(move_history, boards, scores)
                return novelty_score.novelty_score
            except:
                pass
        
        # Simple novelty: 1.0 for new positions, 0.3 for transpositions
        return 1.0  # Simplified for now
    
    def _moves_to_boards(self, moves: List[int]) -> List[Board]:
        """Convert move sequence to board sequence"""
        from ..engine.board import Board
        
        boards = []
        current = Board(B=0x0000000810000000, W=0x0000001008000000, stm=0, ply=0, hash=0)
        boards.append(current)
        
        for move in moves:
            try:
                current, _ = make_move(current, move)
                boards.append(current)
            except:
                break
        
        return boards


# Legacy function for backward compatibility
def build_tree(root: Board, preset: str, depth: int = 4, width: int = 8, time_ms: int = 2000) -> dict:
    """Legacy tree building function using presets"""
    start = time.perf_counter()
    nodes: Dict[int, TreeNode] = {root.hash: TreeNode(root.stm, 0, {})}
    edges: List[dict] = []
    frontier: List[Tuple[float, float, Board, int]] = []  # (priority, novelty, board, depth)
    scorer = get_preset(preset).scorer
    root_score = scorer(root)
    # Novelty v1.0 simple: 1.0 at root
    frontier.append((root_score + 0.01, 1.0, root, 0))
    while frontier and len(nodes) < 1_000 and (time.perf_counter() - start) * 1000 < time_ms:
        # best-first: pop max score
        frontier.sort(key=lambda t: (t[0], t[1]), reverse=True)
        cur_score, cur_novelty, cur, d = frontier.pop(0)
        mask = legal_moves_mask(cur)
        m = mask
        w = 0
        while m and w < width and d < depth:
            lsb = m & -m
            sq = lsb.bit_length() - 1
            m ^= lsb
            w += 1
            b2, _ = make_move(cur, sq)
            if b2.hash not in nodes:
                score = scorer(b2)
                # Simple novelty: prefer positions not present yet (transposition-aware)
                novelty = 1.0 if b2.hash not in nodes else 0.3
                nodes[b2.hash] = TreeNode(b2.stm, int(score), {})
                # Priority tuple: primary score + small PV bonus + novelty
                pv_bonus = 0.001 * (depth - d)
                frontier.append((float(score) + pv_bonus + novelty, novelty, b2, d + 1))
            edges.append({"from": cur.hash, "to": b2.hash, "move": sq, "score": int(cur_score)})
    return {"root": root.hash, "nodes": {h: {"stm": n.stm, "score": n.score, "attrs": n.attrs} for h, n in nodes.items()}, "edges": edges}
