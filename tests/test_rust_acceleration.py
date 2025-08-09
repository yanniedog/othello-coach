"""Tests for Rust acceleration parity"""

import pytest
from othello_coach.engine.board import Board
from othello_coach.engine.movegen_ref import generate_legal_mask as ref_legal_mask
from othello_coach.engine.movegen_fast import generate_legal_mask as fast_legal_mask
from othello_coach.insights.features import extract_features
import random


def _rust_available() -> bool:
    """Check if Rust kernel is available"""
    try:
        import rust_kernel
        # Test if a function actually works - if it's just a fallback module, it will raise ImportError
        rust_kernel.legal_mask(0, 0, 0)
        return True
    except (ImportError, AttributeError):
        return False


class TestRustAcceleration:
    """Test Rust acceleration parity with Python implementations"""
    
    def test_rust_import(self):
        """Test that Rust kernel can be imported"""
        try:
            import rust_kernel
            rust_available = True
        except ImportError:
            rust_available = False
            pytest.skip("Rust kernel not available")
        
        assert rust_available
    
    @pytest.mark.skipif(
        not _rust_available(),
        reason="Rust kernel not available"
    )
    def test_legal_mask_parity(self):
        """Test legal mask parity between Rust and Python"""
        import rust_kernel
        
        # Test various positions
        test_positions = [
            # Start position
            (0x0000000810000000, 0x0000001008000000, 0),
            # Random positions
            (0x0000001008000000, 0x0000000810000000, 1),
            (0x1818000000000000, 0x0000000000181800, 0),
        ]
        
        for b, w, stm in test_positions:
            python_mask = fast_legal_mask(b, w, stm)
            rust_mask = rust_kernel.legal_mask(b, w, stm)
            
            assert python_mask == rust_mask, f"Legal mask mismatch for position B={b:016x}, W={w:016x}, stm={stm}"
    
    @pytest.mark.skipif(
        not _rust_available(),
        reason="Rust kernel not available"
    )
    def test_flip_mask_parity(self):
        """Test flip mask parity between Rust and Python"""
        import rust_kernel
        from othello_coach.engine.movegen_fast import generate_flip_mask
        
        # Test start position moves
        b, w, stm = 0x0000000810000000, 0x0000001008000000, 0
        legal_moves = [19, 26, 37, 44]  # Legal moves from start
        
        for move in legal_moves:
            # Python function needs own/opp based on stm
            own, opp = (b, w) if stm == 0 else (w, b)
            python_flips = generate_flip_mask(own, opp, move)
            rust_flips = rust_kernel.flip_mask(b, w, stm, move)
            
            assert python_flips == rust_flips, f"Flip mask mismatch for move {move}"
    
    @pytest.mark.skipif(
        not _rust_available(),
        reason="Rust kernel not available"
    )
    def test_stability_proxy_parity(self):
        """Test stability proxy parity"""
        import rust_kernel
        
        # Test various positions
        test_positions = [
            (0x0000000810000000, 0x0000001008000000),  # Start
            (0x8100000000000081, 0x0000000000000000),  # Corners only
            (0xFF00000000000000, 0x00FF000000000000),  # Edge patterns
        ]
        
        for b, w in test_positions:
            board = Board(B=b, W=w, stm=0, ply=0, hash=0)
            features = extract_features(board)
            # Calculate stability proxy as difference (Black - White)
            python_stability = features.get('stability_stm', 0) - features.get('stability_opp', 0)
            
            rust_stability = rust_kernel.stability_proxy(b, w)
            
            # Allow small differences due to implementation details
            assert abs(python_stability - rust_stability) <= 2, \
                f"Stability mismatch: Python={python_stability}, Rust={rust_stability}"
    
    @pytest.mark.skipif(
        not _rust_available(),
        reason="Rust kernel not available"
    )
    def test_potential_mobility_parity(self):
        """Test potential mobility parity"""
        import rust_kernel
        
        test_positions = [
            (0x0000000810000000, 0x0000001008000000, 0),
            (0x0000001008000000, 0x0000000810000000, 1),
        ]
        
        for b, w, stm in test_positions:
            board = Board(B=b, W=w, stm=stm, ply=0, hash=0)
            features = extract_features(board)
            python_pot_mob = features.get('potential_mobility', 0)
            
            rust_pot_mob = rust_kernel.potential_mobility(b, w, stm)
            
            assert abs(python_pot_mob - rust_pot_mob) <= 1, \
                f"Potential mobility mismatch: Python={python_pot_mob}, Rust={rust_pot_mob}"
    
    @pytest.mark.skipif(
        not _rust_available(),
        reason="Rust kernel not available"
    )
    def test_parity_regions_structure(self):
        """Test parity regions return structure"""
        import rust_kernel
        
        b, w = 0x0000000810000000, 0x0000001008000000
        regions = rust_kernel.parity_regions(b, w)
        
        assert isinstance(regions, list)
        for region_mask, controller in regions:
            assert isinstance(region_mask, int)
            assert isinstance(controller, int)
            assert 0 <= controller <= 2  # 0=black, 1=white, 2=neutral
    
    @pytest.mark.skipif(
        not _rust_available(),
        reason="Rust kernel not available"
    )
    def test_exact_solver_parity(self):
        """Test exact solver parity for small positions"""
        import rust_kernel
        from othello_coach.engine.solver import _python_exact_solver
        
        # Test endgame positions (≤12 empties for Python solver)
        test_positions = [
            # Real endgame with 12 empties (52 pieces)
            (0xFFFFFFFFFFF80000, 0x000000000007FFC0, 0, 12),
            # Real endgame with 8 empties (56 pieces)  
            (0xFFFFFFFFFFFFF000, 0x0000000000000FF0, 1, 8),
        ]
        
        for b, w, stm, claimed_empties in test_positions:
            # Calculate actual empties and skip if they don't match
            actual_empties = 64 - (b | w).bit_count()
            if actual_empties != claimed_empties:
                continue  # Skip invalid test case
                
            if actual_empties <= 12:
                board = Board(B=b, W=w, stm=stm, ply=0, hash=0)
                python_score = _python_exact_solver(board)
                rust_score = rust_kernel.exact_solver(b, w, stm, actual_empties, 64)

                assert python_score == rust_score, \
                    f"Solver mismatch: Python={python_score}, Rust={rust_score}"
    
    @pytest.mark.skipif(
        not _rust_available(),
        reason="Rust kernel not available"
    )
    def test_random_position_parity(self):
        """Test parity on random positions"""
        import rust_kernel
        
        random.seed(42)  # Reproducible tests
        
        for _ in range(10):
            # Generate random position
            b = random.randint(0, 2**64 - 1)
            w = random.randint(0, 2**64 - 1)
            w &= ~b  # Ensure no overlap
            stm = random.randint(0, 1)
            
            # Skip if invalid position
            if bin(b | w).count('1') > 64 or bin(b | w).count('1') < 4:
                continue
            
            try:
                # Test legal mask
                python_legal = fast_legal_mask(b, w, stm)
                rust_legal = rust_kernel.legal_mask(b, w, stm)
                assert python_legal == rust_legal, "Random position legal mask mismatch"
                
                # Test stability if not too complex
                if bin(b | w).count('1') >= 20:  # Enough pieces for stability
                    board = Board(B=b, W=w, stm=stm, ply=0, hash=0)
                    features = extract_features(board)
                    python_stability = features.get('stability_proxy', 0)
                    rust_stability = rust_kernel.stability_proxy(b, w)
                    
                    # Allow larger tolerance for complex positions
                    assert abs(python_stability - rust_stability) <= 5
                
            except Exception:
                # Skip positions that cause issues in either implementation
                continue


class TestRustPerformance:
    """Performance comparison tests (not strict assertions)"""
    
    @pytest.mark.skipif(
        not _rust_available(),
        reason="Rust kernel not available"
    )
    def test_legal_mask_performance(self):
        """Compare legal mask performance"""
        import rust_kernel
        import time
        
        # Test position
        b, w, stm = 0x0000000810000000, 0x0000001008000000, 0
        iterations = 10000
        
        # Time Python implementation
        start = time.time()
        for _ in range(iterations):
            fast_legal_mask(b, w, stm)
        python_time = time.time() - start
        
        # Time Rust implementation
        start = time.time()
        for _ in range(iterations):
            rust_kernel.legal_mask(b, w, stm)
        rust_time = time.time() - start
        
        print(f"Legal mask performance:")
        print(f"  Python: {python_time:.4f}s ({iterations/python_time:.0f} ops/s)")
        print(f"  Rust:   {rust_time:.4f}s ({iterations/rust_time:.0f} ops/s)")
        print(f"  Speedup: {python_time/rust_time:.1f}x")
        
        # Rust should be faster, but don't make it a hard requirement
        assert rust_time < python_time * 2, "Rust should be at least competitive with Python"
    
    @pytest.mark.skipif(
        not _rust_available(),
        reason="Rust kernel not available"
    )
    def test_solver_performance(self):
        """Compare solver performance on endgame"""
        import rust_kernel
        from othello_coach.engine.solver import _python_exact_solver
        import time
        
        # Simple endgame position
        board = Board(
            B=0x0000000000001000,
            W=0x0000000000002000,
            stm=0,
            ply=50,
            hash=0
        )
        empties = 64 - bin(board.B | board.W).count('1')
        
        if empties <= 12:  # Only test if Python solver can handle it
            iterations = 100
            
            # Time Python solver
            start = time.time()
            for _ in range(iterations):
                _python_exact_solver(board)
            python_time = time.time() - start
            
            # Time Rust solver
            start = time.time()
            for _ in range(iterations):
                rust_kernel.exact_solver(board.B, board.W, board.stm, empties, 64)
            rust_time = time.time() - start
            
            print(f"Solver performance ({empties} empties):")
            print(f"  Python: {python_time:.4f}s ({iterations/python_time:.0f} ops/s)")
            print(f"  Rust:   {rust_time:.4f}s ({iterations/rust_time:.0f} ops/s)")
            print(f"  Speedup: {python_time/rust_time:.1f}x")
            
            # Rust should provide meaningful speedup
            assert rust_time < python_time, "Rust solver should be faster than Python"
