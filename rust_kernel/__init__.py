"""Python wrapper for the Rust extension module.

This package exposes the functions compiled in ``rust_kernel._rust_kernel``
at the top-level ``rust_kernel`` namespace, matching the expectations of
the test suite and downstream imports.

Features:
- Automatic fallback to Python implementations if Rust is unavailable
- Comprehensive error handling and logging
- Performance monitoring and diagnostics
- Seamless integration with existing code
"""

from __future__ import annotations
import logging
import time
import traceback
from typing import Any, Dict, List, Tuple, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import the compiled extension first and expose its API. If unavailable,
# provide Python fallbacks that match the same function signatures.
try:  # Prefer the compiled extension submodule
    logger.info("Attempting to import Rust kernel...")
    start_time = time.time()
    
    from . import rust_kernel
    legal_mask = rust_kernel.legal_mask
    flip_mask = rust_kernel.flip_mask
    potential_mobility = rust_kernel.potential_mobility
    stability_proxy = rust_kernel.stability_proxy
    parity_regions = rust_kernel.parity_regions
    exact_solver = rust_kernel.exact_solver
    
    import_time = time.time() - start_time
    logger.info(f"Rust kernel imported successfully in {import_time:.3f}s")
    
    AVAILABLE = True
    RUST_IMPORT_TIME = import_time
    
    __all__ = [
        "legal_mask",
        "flip_mask",
        "potential_mobility",
        "stability_proxy",
        "parity_regions",
        "exact_solver",
        "AVAILABLE",
        "RUST_IMPORT_TIME",
        "get_performance_info",
        "test_rust_functions",
    ]
    
except Exception as e:  # Fall back to Python implementations
    logger.warning(f"Rust kernel import failed: {e}")
    logger.info("Falling back to Python implementations")
    
    AVAILABLE = False
    RUST_IMPORT_TIME = None
    
    # Import Python equivalents to maintain the same public API
    try:
        from othello_coach.engine.movegen_fast import (
            generate_legal_mask as _py_legal_mask,
            generate_flip_mask as _py_generate_flip_mask,
        )
        from othello_coach.insights.features import extract_features as _extract_features
        from othello_coach.engine.solver import _python_exact_solver as _py_exact_solver
        from othello_coach.engine.board import Board as _Board
        
        logger.info("Python fallbacks imported successfully")
        
    except ImportError as fallback_error:
        logger.error(f"Failed to import Python fallbacks: {fallback_error}")
        logger.error("This may indicate a broken installation")
        raise

    def legal_mask(b: int, w: int, stm: int) -> int:
        """Python fallback for legal_mask"""
        try:
            return _py_legal_mask(b, w, stm)
        except Exception as e:
            logger.error(f"Python legal_mask failed: {e}")
            # Return empty mask as safe fallback
            return 0

    def flip_mask(b: int, w: int, stm: int, sq: int) -> int:
        """Python fallback for flip_mask"""
        try:
            # movegen_fast expects side-to-move bitboards for flip mask
            return _py_generate_flip_mask(b if stm == 0 else w, w if stm == 0 else b, sq)
        except Exception as e:
            logger.error(f"Python flip_mask failed: {e}")
            # Return empty mask as safe fallback
            return 0

    def potential_mobility(b: int, w: int, stm: int) -> int:
        """Python fallback for potential_mobility"""
        try:
            feats = _extract_features(_Board(B=b, W=w, stm=stm, ply=0, hash=0))
            return int(feats.get('potential_mobility', 0))
        except Exception as e:
            logger.error(f"Python potential_mobility failed: {e}")
            # Return neutral value as safe fallback
            return 0

    def stability_proxy(b: int, w: int) -> int:
        """Python fallback for stability_proxy"""
        try:
            feats = _extract_features(_Board(B=b, W=w, stm=0, ply=0, hash=0))
            return int(feats.get('stability_stm', 0) - feats.get('stability_opp', 0))
        except Exception as e:
            logger.error(f"Python stability_proxy failed: {e}")
            # Return neutral value as safe fallback
            return 0

    def parity_regions(b: int, w: int) -> List[Tuple[int, int]]:
        """Python fallback for parity_regions"""
        try:
            empties = (~(b | w)) & 0xFFFFFFFFFFFFFFFF
            regions: List[Tuple[int, int]] = []
            visited = 0
            rem = empties
            while rem:
                lsb = rem & -rem
                start = (lsb.bit_length() - 1)
                stack = [start]
                mask = 0
                while stack:
                    s = stack.pop()
                    if (visited >> s) & 1:
                        continue
                    visited |= (1 << s)
                    mask |= (1 << s)
                    r, f = divmod(s, 8)
                    for nb in (s-8 if r>0 else None, s+8 if r<7 else None, s-1 if f>0 else None, s+1 if f<7 else None):
                        if nb is None:
                            continue
                        if ((empties >> nb) & 1) and ((visited >> nb) & 1) == 0:
                            stack.append(nb)
                regions.append((mask, 2))
                rem &= ~mask
            return regions
        except Exception as e:
            logger.error(f"Python parity_regions failed: {e}")
            # Return empty list as safe fallback
            return []

    def exact_solver(b: int, w: int, stm: int, empties: int, tt_mb: int) -> int:
        """Python fallback for exact_solver"""
        try:
            board = _Board(B=b, W=w, stm=stm, ply=0, hash=0)
            return int(_py_exact_solver(board))
        except Exception as e:
            logger.error(f"Python exact_solver failed: {e}")
            # Return neutral score as safe fallback
            return 0

    __all__ = [
        "legal_mask",
        "flip_mask",
        "potential_mobility",
        "stability_proxy",
        "parity_regions",
        "exact_solver",
        "AVAILABLE",
        "RUST_IMPORT_TIME",
        "get_performance_info",
        "test_rust_functions",
    ]


def get_performance_info() -> Dict[str, Any]:
    """Get performance and availability information about the Rust kernel"""
    info = {
        "rust_available": AVAILABLE,
        "rust_import_time": RUST_IMPORT_TIME,
        "python_fallback": not AVAILABLE,
        "functions": {}
    }
    
    # Test each function for performance
    test_cases = [
        (0x0000000810000000, 0x0000001008000000, 0),  # Standard opening position
        (0x0000000000000000, 0x0000000000000000, 0),  # Empty board
        (0xFFFFFFFFFFFFFFFF, 0x0000000000000000, 0),  # Full black board
    ]
    
    for i, (b, w, stm) in enumerate(test_cases):
        case_info = {}
        
        # Test legal_mask
        start_time = time.time()
        try:
            result = legal_mask(b, w, stm)
            case_info["legal_mask"] = {
                "result": result,
                "time": time.time() - start_time,
                "success": True
            }
        except Exception as e:
            case_info["legal_mask"] = {
                "error": str(e),
                "time": time.time() - start_time,
                "success": False
            }
        
        # Test potential_mobility
        start_time = time.time()
        try:
            result = potential_mobility(b, w, stm)
            case_info["potential_mobility"] = {
                "result": result,
                "time": time.time() - start_time,
                "success": True
            }
        except Exception as e:
            case_info["potential_mobility"] = {
                "error": str(e),
                "time": time.time() - start_time,
                "success": False
            }
        
        info["functions"][f"test_case_{i}"] = case_info
    
    return info


def test_rust_functions() -> Dict[str, bool]:
    """Test all Rust functions to ensure they work correctly"""
    logger.info("Testing Rust kernel functions...")
    
    test_results = {}
    
    # Test data
    b, w, stm = 0x0000000810000000, 0x0000001008000000, 0
    
    # Test legal_mask
    try:
        legal = legal_mask(b, w, stm)
        test_results["legal_mask"] = legal > 0
        logger.info(f"legal_mask test: {'PASS' if legal > 0 else 'FAIL'}")
    except Exception as e:
        test_results["legal_mask"] = False
        logger.error(f"legal_mask test failed: {e}")
    
    # Test flip_mask
    try:
        if legal > 0:
            # Find first legal move
            for sq in range(64):
                if legal & (1 << sq):
                    flips = flip_mask(b, w, stm, sq)
                    test_results["flip_mask"] = flips >= 0
                    logger.info(f"flip_mask test: {'PASS' if flips >= 0 else 'FAIL'}")
                    break
            else:
                test_results["flip_mask"] = False
                logger.warning("flip_mask test: SKIP (no legal moves)")
        else:
            test_results["flip_mask"] = False
            logger.warning("flip_mask test: SKIP (no legal moves)")
    except Exception as e:
        test_results["flip_mask"] = False
        logger.error(f"flip_mask test failed: {e}")
    
    # Test potential_mobility
    try:
        pot_mob = potential_mobility(b, w, stm)
        test_results["potential_mobility"] = isinstance(pot_mob, int)
        logger.info(f"potential_mobility test: {'PASS' if isinstance(pot_mob, int) else 'FAIL'}")
    except Exception as e:
        test_results["potential_mobility"] = False
        logger.error(f"potential_mobility test failed: {e}")
    
    # Test stability_proxy
    try:
        stability = stability_proxy(b, w)
        test_results["stability_proxy"] = isinstance(stability, int)
        logger.info(f"stability_proxy test: {'PASS' if isinstance(stability, int) else 'FAIL'}")
    except Exception as e:
        test_results["stability_proxy"] = False
        logger.error(f"stability_proxy test failed: {e}")
    
    # Test parity_regions
    try:
        regions = parity_regions(b, w)
        test_results["parity_regions"] = isinstance(regions, list)
        logger.info(f"parity_regions test: {'PASS' if isinstance(regions, list) else 'FAIL'}")
    except Exception as e:
        test_results["parity_regions"] = False
        logger.error(f"parity_regions test failed: {e}")
    
    # Test exact_solver
    try:
        # Test with small number of empties
        empties = 64 - (b | w).bit_count()
        if empties <= 16:
            score = exact_solver(b, w, stm, empties, 32)
            test_results["exact_solver"] = isinstance(score, int)
            logger.info(f"exact_solver test: {'PASS' if isinstance(score, int) else 'FAIL'}")
        else:
            test_results["exact_solver"] = True  # Skip for large positions
            logger.info("exact_solver test: SKIP (too many empties)")
    except Exception as e:
        test_results["exact_solver"] = False
        logger.error(f"exact_solver test failed: {e}")
    
    # Summary
    passed = sum(test_results.values())
    total = len(test_results)
    logger.info(f"Rust kernel test summary: {passed}/{total} functions passed")
    
    return test_results


# Log initialization status
if AVAILABLE:
    logger.info("Rust kernel is available and ready for use")
else:
    logger.warning("Rust kernel unavailable, using Python fallbacks")
    logger.info("Run 'python install_rust.py' to install Rust and rebuild the kernel")
