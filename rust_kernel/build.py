#!/usr/bin/env python3
"""Build script for Rust kernel"""

import subprocess
import sys
import os
from pathlib import Path


def build_rust_kernel():
    """Build the Rust kernel with maturin"""
    rust_dir = Path(__file__).parent
    
    print("Building Rust acceleration kernel...")
    
    # Check if cargo is available
    try:
        subprocess.run(["cargo", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: Cargo not found. Please install Rust toolchain.", file=sys.stderr)
        return False
    
    # Check if maturin is available
    try:
        subprocess.run(["maturin", "--version"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Installing maturin...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "maturin"], check=True)
        except subprocess.CalledProcessError:
            print("Error: Failed to install maturin.", file=sys.stderr)
            return False
    
    # Build the wheel
    try:
        os.chdir(rust_dir)
        subprocess.run(["maturin", "develop", "--release"], check=True)
        print("✓ Rust kernel built successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: Failed to build Rust kernel: {e}", file=sys.stderr)
        return False


def test_rust_kernel():
    """Test that the Rust kernel works"""
    try:
        import rust_kernel
        
        # Basic functionality test
        b, w, stm = 0x0000000810000000, 0x0000001008000000, 0
        legal = rust_kernel.legal_mask(b, w, stm)
        
        if legal > 0:
            print("✓ Rust kernel test passed!")
            return True
        else:
            print("✗ Rust kernel test failed: no legal moves found")
            return False
            
    except ImportError as e:
        print(f"✗ Rust kernel import failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Rust kernel test failed: {e}")
        return False


if __name__ == "__main__":
    if build_rust_kernel():
        test_rust_kernel()
    else:
        sys.exit(1)
