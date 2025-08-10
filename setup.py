#!/usr/bin/env python3
"""
Comprehensive setup script for Othello Coach.
Handles Python dependencies, Rust installation, and kernel building.
"""

import subprocess
import sys
import os
from pathlib import Path
import argparse


def run_command(cmd: list, description: str = ""):
    """Run a command with proper error handling"""
    if description:
        print(f"\n🔄 {description}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        if e.stdout:
            print(f"stdout: {e.stdout}")
        if e.stderr:
            print(f"stderr: {e.stderr}")
        return False


def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    
    if sys.version_info < (3, 8):
        print(f"❌ Python 3.8+ required, found {sys.version}")
        return False
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    return True


def install_python_dependencies():
    """Install Python dependencies"""
    print("\n📦 Installing Python dependencies...")
    
    # Upgrade pip first
    if not run_command([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], "Upgrading pip"):
        return False
    
    # Install requirements
    requirements_file = Path("requirements.txt")
    if requirements_file.exists():
        if not run_command([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], "Installing Python dependencies"):
            return False
    else:
        print("⚠️  requirements.txt not found, installing core dependencies manually")
        core_deps = ["PyQt6", "numpy", "pytest", "maturin"]
        for dep in core_deps:
            if not run_command([sys.executable, "-m", "pip", "install", dep], f"Installing {dep}"):
                return False
    
    return True


def check_rust_installation():
    """Check if Rust is already installed"""
    print("\n🔧 Checking Rust installation...")
    
    try:
        # Check rustc
        result = subprocess.run(["rustc", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ Rust found: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ Rust not found")
    return False


def install_rust():
    """Install Rust using the installer script"""
    print("\n🦀 Installing Rust...")
    
    installer_script = Path("install_rust.py")
    if not installer_script.exists():
        print("❌ install_rust.py not found")
        return False
    
    if not run_command([sys.executable, "install_rust.py"], "Installing Rust"):
        return False
    
    return True


def build_rust_kernel():
    """Build the Rust kernel"""
    print("\n⚙️  Building Rust kernel...")
    
    build_script = Path("rust_kernel") / "build.py"
    if not build_script.exists():
        print("❌ rust_kernel/build.py not found")
        return False
    
    if not run_command([sys.executable, str(build_script)], "Building Rust kernel"):
        return False
    
    return True


def run_tests():
    """Run the test suite to verify everything works"""
    print("\n🧪 Running tests...")
    
    if not run_command([sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"], "Running test suite"):
        return False
    
    return True


def create_environment_scripts():
    """Create environment setup scripts for future sessions"""
    print("\n📝 Creating environment setup scripts...")
    
    # Windows batch file
    bat_content = """@echo off
REM Othello Coach Environment Setup
echo Setting up Othello Coach environment...

REM Set Rust environment
set RUST_HOME=%USERPROFILE%\\.cargo
set PATH=%RUST_HOME%\\bin;%PATH%

REM Activate Python virtual environment if it exists
if exist "venv\\Scripts\\activate.bat" (
    call venv\\Scripts\\activate.bat
    echo Python virtual environment activated.
)

echo Environment setup complete!
echo You can now run: python -m othello_coach.gui.main
"""
    
    with open("setup_env.bat", "w") as f:
        f.write(bat_content)
    
    # Unix shell script
    sh_content = """#!/bin/bash
# Othello Coach Environment Setup
echo "Setting up Othello Coach environment..."

# Set Rust environment
export RUST_HOME="$HOME/.cargo"
export PATH="$RUST_HOME/bin:$PATH"

# Activate Python virtual environment if it exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "Python virtual environment activated."
fi

echo "Environment setup complete!"
echo "You can now run: python -m othello_coach.gui.main"
"""
    
    with open("setup_env.sh", "w") as f:
        f.write(sh_content)
    
    # Make shell script executable
    try:
        os.chmod("setup_env.sh", 0o755)
    except:
        pass
    
    print("✅ Environment setup scripts created:")
    print("  - setup_env.bat (Windows)")
    print("  - setup_env.sh (Unix/Linux/macOS)")


def main():
    """Main setup process"""
    parser = argparse.ArgumentParser(description="Setup Othello Coach project")
    parser.add_argument("--skip-rust", action="store_true", help="Skip Rust installation")
    parser.add_argument("--skip-tests", action="store_true", help="Skip running tests")
    parser.add_argument("--python-only", action="store_true", help="Only install Python dependencies")
    
    args = parser.parse_args()
    
    print("🚀 Othello Coach Setup")
    print("=" * 50)
    
    try:
        # Check Python version
        if not check_python_version():
            sys.exit(1)
        
        # Install Python dependencies
        if not install_python_dependencies():
            print("❌ Failed to install Python dependencies")
            sys.exit(1)
        
        if args.python_only:
            print("\n✅ Python-only setup completed!")
            return
        
        # Check/install Rust
        if not args.skip_rust:
            if not check_rust_installation():
                if not install_rust():
                    print("❌ Failed to install Rust")
                    sys.exit(1)
            else:
                print("✅ Rust already installed")
        
        # Build Rust kernel
        if not args.skip_rust:
            if not build_rust_kernel():
                print("❌ Failed to build Rust kernel")
                sys.exit(1)
        
        # Run tests
        if not args.skip_tests:
            if not run_tests():
                print("❌ Tests failed")
                sys.exit(1)
        
        # Create environment scripts
        create_environment_scripts()
        
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. For future sessions, run the environment setup script:")
        if os.name == 'nt':  # Windows
            print("   setup_env.bat")
        else:
            print("   source setup_env.sh")
        print("2. Start the application:")
        print("   python -m othello_coach.gui.main")
        
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error during setup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
