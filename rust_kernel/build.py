#!/usr/bin/env python3
"""Robust build script for Rust kernel with comprehensive error handling"""

import subprocess
import sys
import os
import shutil
import time
from pathlib import Path
import json


class RustKernelBuilder:
    """Robust Rust kernel builder with comprehensive error handling"""
    
    def __init__(self):
        self.rust_dir = Path(__file__).parent
        self.project_root = self.rust_dir.parent
        self.target_dir = self.rust_dir / "target"
        self.build_log = self.project_root / "rust_build.log"
        
    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {level}: {message}"
        print(log_msg)
        
        # Also write to build log file
        with open(self.build_log, 'a', encoding='utf-8') as f:
            f.write(log_msg + '\n')
    
    def check_rust_toolchain(self) -> bool:
        """Check if Rust toolchain is available and working"""
        self.log("Checking Rust toolchain...")
        
        tools = ["rustc", "cargo", "rustup"]
        missing_tools = []
        
        for tool in tools:
            if not shutil.which(tool):
                missing_tools.append(tool)
        
        if missing_tools:
            self.log(f"Missing Rust tools: {', '.join(missing_tools)}", "ERROR")
            self.log("Please run 'python install_rust.py' to install Rust", "ERROR")
            return False
        
        # Verify tool versions
        try:
            rustc_version = subprocess.run(
                ["rustc", "--version"], 
                capture_output=True, text=True, check=True
            ).stdout.strip()
            cargo_version = subprocess.run(
                ["cargo", "--version"], 
                capture_output=True, text=True, check=True
            ).stdout.strip()
            
            self.log(f"Found {rustc_version}")
            self.log(f"Found {cargo_version}")
            
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to verify Rust tools: {e}", "ERROR")
            return False
    
    def check_maturin(self) -> bool:
        """Check if maturin is available and install if needed"""
        self.log("Checking maturin...")
        
        if shutil.which("maturin"):
            try:
                version = subprocess.run(
                    ["maturin", "--version"], 
                    capture_output=True, text=True, check=True
                ).stdout.strip()
                self.log(f"Found maturin: {version}")
                return True
            except subprocess.CalledProcessError:
                pass
        
        # Install maturin if not found
        self.log("Installing maturin...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "--upgrade", "maturin"
            ], check=True, capture_output=True)
            
            # Verify installation
            version = subprocess.run(
                ["maturin", "--version"], 
                capture_output=True, text=True, check=True
            ).stdout.strip()
            self.log(f"Installed maturin: {version}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to install maturin: {e}", "ERROR")
            return False
    
    def clean_build_artifacts(self):
        """Clean previous build artifacts"""
        self.log("Cleaning build artifacts...")
        
        # Clean target directory
        if self.target_dir.exists():
            try:
                shutil.rmtree(self.target_dir)
                self.log("Cleaned target directory")
            except Exception as e:
                self.log(f"Warning: Could not clean target directory: {e}", "WARNING")
        
        # Clean Python cache
        python_cache = self.rust_dir / "__pycache__"
        if python_cache.exists():
            try:
                shutil.rmtree(python_cache)
                self.log("Cleaned Python cache")
            except Exception as e:
                self.log(f"Warning: Could not clean Python cache: {e}", "WARNING")
    
    def build_kernel(self) -> bool:
        """Build the Rust kernel"""
        self.log("Building Rust kernel...")
        
        try:
            # Change to rust directory
            original_dir = os.getcwd()
            os.chdir(self.rust_dir)
            
            # Build with maturin
            self.log("Running maturin build...")
            result = subprocess.run([
                "maturin", "develop", "--release", "--quiet"
            ], capture_output=True, text=True, check=True)
            
            # Return to original directory
            os.chdir(original_dir)
            
            self.log("✓ Rust kernel built successfully!")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Build failed: {e}", "ERROR")
            if e.stdout:
                self.log(f"stdout: {e.stdout}", "DEBUG")
            if e.stderr:
                self.log(f"stderr: {e.stderr}", "DEBUG")
            
            # Return to original directory on error
            try:
                os.chdir(original_dir)
            except:
                pass
            return False
        
        except Exception as e:
            self.log(f"Unexpected error during build: {e}", "ERROR")
            # Return to original directory on error
            try:
                os.chdir(original_dir)
            except:
                pass
            return False
    
    def test_kernel(self) -> bool:
        """Test the built kernel"""
        self.log("Testing Rust kernel...")
        
        try:
            # Import the kernel
            import rust_kernel
            
            # Test basic functionality
            b, w, stm = 0x0000000810000000, 0x0000001008000000, 0
            legal = rust_kernel.legal_mask(b, w, stm)
            
            if legal > 0:
                self.log("✓ Rust kernel test passed!")
                return True
            else:
                self.log("✗ Rust kernel test failed: no legal moves found", "ERROR")
                return False
                
        except ImportError as e:
            self.log(f"✗ Rust kernel import failed: {e}", "ERROR")
            return False
        except Exception as e:
            self.log(f"✗ Rust kernel test failed: {e}", "ERROR")
            return False
    
    def create_build_info(self):
        """Create build information file"""
        build_info = {
            "build_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "rust_version": None,
            "cargo_version": None,
            "maturin_version": None,
            "build_success": True
        }
        
        try:
            # Get Rust version
            rustc_result = subprocess.run(
                ["rustc", "--version"], 
                capture_output=True, text=True, check=True
            )
            build_info["rust_version"] = rustc_result.stdout.strip()
            
            # Get Cargo version
            cargo_result = subprocess.run(
                ["cargo", "--version"], 
                capture_output=True, text=True, check=True
            )
            build_info["cargo_version"] = cargo_result.stdout.strip()
            
            # Get maturin version
            maturin_result = subprocess.run(
                ["maturin", "--version"], 
                capture_output=True, text=True, check=True
            )
            build_info["maturin_version"] = maturin_result.stdout.strip()
            
        except Exception as e:
            self.log(f"Warning: Could not get version info: {e}", "WARNING")
        
        # Write build info
        build_info_path = self.project_root / "rust_build_info.json"
        with open(build_info_path, 'w', encoding='utf-8') as f:
            json.dump(build_info, f, indent=2)
        
        self.log(f"Created build info: {build_info_path}")
    
    def build(self) -> bool:
        """Main build process"""
        self.log("Starting Rust kernel build...")
        
        # Initialize build log
        with open(self.build_log, 'w', encoding='utf-8') as f:
            f.write(f"Rust Kernel Build Log - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 50 + "\n")
        
        try:
            # Step 1: Check Rust toolchain
            if not self.check_rust_toolchain():
                return False
            
            # Step 2: Check maturin
            if not self.check_maturin():
                return False
            
            # Step 3: Clean build artifacts
            self.clean_build_artifacts()
            
            # Step 4: Build kernel
            if not self.build_kernel():
                return False
            
            # Step 5: Test kernel
            if not self.test_kernel():
                return False
            
            # Step 6: Create build info
            self.create_build_info()
            
            self.log("✓ Rust kernel build completed successfully!")
            return True
            
        except Exception as e:
            self.log(f"Build process failed: {e}", "ERROR")
            return False


def main():
    """Main entry point"""
    builder = RustKernelBuilder()
    
    try:
        success = builder.build()
        if success:
            print("\n🎉 Rust kernel built successfully!")
            print("The Othello Coach is now ready with Rust acceleration.")
        else:
            print("\n❌ Rust kernel build failed!")
            print("Check the build log for details: rust_build.log")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nBuild interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error during build: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
