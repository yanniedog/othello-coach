#!/usr/bin/env python3
"""
Comprehensive Rust installation and setup script for Othello Coach.
This script ensures robust Rust toolchain installation and kernel building.
"""

import subprocess
import sys
import os
import platform
import shutil
from pathlib import Path
import urllib.request
import json
import zipfile
import tarfile
import tempfile
import time


class RustInstaller:
    """Handles Rust toolchain installation and kernel building"""
    
    def __init__(self):
        self.rustup_path = None
        self.cargo_path = None
        self.maturin_path = None
        self.project_root = Path(__file__).parent
        self.rust_kernel_dir = self.project_root / "rust_kernel"
        
    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def run_command(self, cmd: list, capture_output: bool = True, check: bool = True) -> subprocess.CompletedProcess:
        """Run a command with proper error handling"""
        self.log(f"Running: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=capture_output, check=check, text=True)
            return result
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {' '.join(cmd)}", "ERROR")
            self.log(f"Error: {e}", "ERROR")
            if capture_output and e.stdout:
                self.log(f"stdout: {e.stdout}", "DEBUG")
            if capture_output and e.stderr:
                self.log(f"stderr: {e.stderr}", "DEBUG")
            raise
    
    def check_command_exists(self, command: str) -> bool:
        """Check if a command exists in PATH"""
        return shutil.which(command) is not None
    
    def get_system_info(self) -> dict:
        """Get system information for Rust installation"""
        system = platform.system().lower()
        machine = platform.machine().lower()
        
        # Map common architectures
        arch_map = {
            'x86_64': 'x86_64',
            'amd64': 'x86_64',
            'i386': 'i686',
            'i686': 'i686',
            'aarch64': 'aarch64',
            'arm64': 'aarch64',
        }
        
        return {
            'system': system,
            'arch': arch_map.get(machine, machine),
            'machine': machine
        }
    
    def install_rustup_windows(self) -> bool:
        """Install Rust on Windows using rustup-init.exe"""
        self.log("Installing Rust on Windows...")
        
        # Download rustup-init.exe
        rustup_url = "https://win.rustup.rs/x86_64"
        installer_path = self.project_root / "rustup-init.exe"
        
        try:
            self.log("Downloading rustup-init.exe...")
            urllib.request.urlretrieve(rustup_url, installer_path)
            
            # Run installer with default settings
            self.log("Running rustup-init.exe...")
            result = subprocess.run([str(installer_path)], check=True)
            
            # Clean up installer
            installer_path.unlink()
            
            # Refresh environment variables
            self.refresh_environment()
            
            return True
            
        except Exception as e:
            self.log(f"Failed to install Rust on Windows: {e}", "ERROR")
            return False
    
    def install_rustup_unix(self) -> bool:
        """Install Rust on Unix-like systems using rustup"""
        self.log("Installing Rust on Unix-like system...")
        
        try:
            # Download and run rustup install script
            rustup_url = "https://sh.rustup.rs"
            result = subprocess.run([
                "curl", "--proto", "=https", "--tlsv1.2", "-sSf", rustup_url
            ], capture_output=True, text=True, check=True)
            
            # Run the install script
            install_script = result.stdout
            subprocess.run([
                "bash", "-c", install_script
            ], input="1\n", text=True, check=True)  # Default installation
            
            # Refresh environment
            self.refresh_environment()
            
            return True
            
        except Exception as e:
            self.log(f"Failed to install Rust on Unix: {e}", "ERROR")
            return False
    
    def install_rustup(self) -> bool:
        """Install Rust toolchain using appropriate method for the system"""
        system_info = self.get_system_info()
        
        if system_info['system'] == 'windows':
            return self.install_rustup_windows()
        else:
            return self.install_rustup_unix()
    
    def refresh_environment(self):
        """Refresh environment variables to include Rust paths"""
        self.log("Refreshing environment variables...")
        
        # Get Rust home directory
        rust_home = os.path.expanduser("~/.cargo")
        if platform.system().lower() == "windows":
            rust_home = os.path.expanduser("~/.cargo")
        
        # Add Rust binaries to PATH
        rust_bin = os.path.join(rust_home, "bin")
        if rust_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = rust_bin + os.pathsep + os.environ.get("PATH", "")
        
        # Update shell environment for current session
        if platform.system().lower() == "windows":
            # On Windows, we need to restart the shell or use setx
            pass
        else:
            # On Unix, source the environment
            try:
                env_file = os.path.join(rust_home, "env")
                if os.path.exists(env_file):
                    with open(env_file, 'r') as f:
                        for line in f:
                            if line.startswith('export PATH='):
                                path_value = line.split('=', 1)[1].strip().strip('"')
                                os.environ["PATH"] = path_value + os.pathsep + os.environ.get("PATH", "")
                                break
            except Exception as e:
                self.log(f"Warning: Could not refresh environment: {e}", "WARNING")
    
    def verify_rust_installation(self) -> bool:
        """Verify that Rust is properly installed"""
        self.log("Verifying Rust installation...")
        
        try:
            # Check rustc
            rustc_result = self.run_command(["rustc", "--version"])
            self.log(f"Found rustc: {rustc_result.stdout.strip()}")
            
            # Check cargo
            cargo_result = self.run_command(["cargo", "--version"])
            self.log(f"Found cargo: {cargo_result.stdout.strip()}")
            
            # Check rustup
            rustup_result = self.run_command(["rustup", "--version"])
            self.log(f"Found rustup: {rustup_result.stdout.strip()}")
            
            return True
            
        except Exception as e:
            self.log(f"Rust verification failed: {e}", "ERROR")
            return False
    
    def install_maturin(self) -> bool:
        """Install maturin for building Rust extensions"""
        self.log("Installing maturin...")
        
        try:
            # Try to install maturin using pip
            self.run_command([
                sys.executable, "-m", "pip", "install", "--upgrade", "maturin"
            ])
            
            # Verify installation
            maturin_result = self.run_command(["maturin", "--version"])
            self.log(f"Installed maturin: {maturin_result.stdout.strip()}")
            
            return True
            
        except Exception as e:
            self.log(f"Failed to install maturin: {e}", "ERROR")
            return False
    
    def build_rust_kernel(self) -> bool:
        """Build the Rust kernel using maturin"""
        self.log("Building Rust kernel...")
        
        if not self.rust_kernel_dir.exists():
            self.log("Rust kernel directory not found!", "ERROR")
            return False
        
        try:
            # Change to rust_kernel directory
            original_dir = os.getcwd()
            os.chdir(self.rust_kernel_dir)
            
            # Clean previous builds
            self.log("Cleaning previous builds...")
            if (self.rust_kernel_dir / "target").exists():
                shutil.rmtree(self.rust_kernel_dir / "target")
            
            # Build in release mode
            self.log("Building with maturin...")
            self.run_command([
                "maturin", "develop", "--release", "--quiet"
            ])
            
            # Return to original directory
            os.chdir(original_dir)
            
            self.log("✓ Rust kernel built successfully!")
            return True
            
        except Exception as e:
            self.log(f"Failed to build Rust kernel: {e}", "ERROR")
            # Return to original directory on error
            try:
                os.chdir(original_dir)
            except:
                pass
            return False
    
    def test_rust_kernel(self) -> bool:
        """Test that the Rust kernel works correctly"""
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
    
    def create_environment_script(self):
        """Create environment setup script for future sessions"""
        system_info = self.get_system_info()
        
        if system_info['system'] == 'windows':
            script_content = """@echo off
REM Rust environment setup for Othello Coach
set RUST_HOME=%USERPROFILE%\\.cargo
set PATH=%RUST_HOME%\\bin;%PATH%
echo Rust environment loaded.
"""
            script_path = self.project_root / "setup_rust_env.bat"
        else:
            script_content = """#!/bin/bash
# Rust environment setup for Othello Coach
export RUST_HOME="$HOME/.cargo"
export PATH="$RUST_HOME/bin:$PATH"
echo "Rust environment loaded."
"""
            script_path = self.project_root / "setup_rust_env.sh"
            # Make executable
            script_path.chmod(0o755)
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        self.log(f"Created environment setup script: {script_path}")
    
    def install(self) -> bool:
        """Main installation process"""
        self.log("Starting Rust installation for Othello Coach...")
        
        # Step 1: Check if Rust is already installed
        if self.check_command_exists("rustc") and self.check_command_exists("cargo"):
            self.log("Rust is already installed, verifying...")
            if self.verify_rust_installation():
                self.log("Rust installation verified successfully!")
            else:
                self.log("Rust installation appears corrupted, reinstalling...")
                if not self.install_rustup():
                    return False
        else:
            self.log("Rust not found, installing...")
            if not self.install_rustup():
                return False
        
        # Step 2: Verify installation
        if not self.verify_rust_installation():
            self.log("Rust installation verification failed!", "ERROR")
            return False
        
        # Step 3: Install maturin
        if not self.install_maturin():
            self.log("Maturin installation failed!", "ERROR")
            return False
        
        # Step 4: Build Rust kernel
        if not self.build_rust_kernel():
            self.log("Rust kernel build failed!", "ERROR")
            return False
        
        # Step 5: Test Rust kernel
        if not self.test_rust_kernel():
            self.log("Rust kernel test failed!", "ERROR")
            return False
        
        # Step 6: Create environment setup script
        self.create_environment_script()
        
        self.log("✓ Rust installation completed successfully!")
        return True


def main():
    """Main entry point"""
    installer = RustInstaller()
    
    try:
        success = installer.install()
        if success:
            print("\n🎉 Rust installation completed successfully!")
            print("The Othello Coach Rust kernel is now ready to use.")
            print("\nFor future sessions, run the environment setup script:")
            if platform.system().lower() == "windows":
                print("  setup_rust_env.bat")
            else:
                print("  source setup_rust_env.sh")
        else:
            print("\n❌ Rust installation failed!")
            print("Please check the error messages above and try again.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nInstallation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error during installation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
