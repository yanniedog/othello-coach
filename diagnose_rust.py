#!/usr/bin/env python3
"""
Comprehensive diagnostic script for Othello Coach Rust integration.
This script helps identify and resolve issues with Rust installation and kernel building.
"""

import subprocess
import sys
import os
import platform
import json
import time
from pathlib import Path
import shutil


class RustDiagnostics:
    """Comprehensive Rust diagnostics for Othello Coach"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.rust_kernel_dir = self.project_root / "rust_kernel"
        self.diagnostic_results = {}
        
    def print_header(self, title: str):
        """Print a formatted header"""
        print(f"\n{'='*60}")
        print(f" {title}")
        print(f"{'='*60}")
    
    def print_section(self, title: str):
        """Print a section header"""
        print(f"\n{'-'*40}")
        print(f" {title}")
        print(f"{'-'*40}")
    
    def run_command(self, cmd: list, capture_output: bool = True) -> dict:
        """Run a command and return results"""
        result = {
            "command": " ".join(cmd),
            "success": False,
            "stdout": "",
            "stderr": "",
            "return_code": None,
            "error": None
        }
        
        try:
            process = subprocess.run(cmd, capture_output=capture_output, text=True, timeout=30)
            result["return_code"] = process.returncode
            result["success"] = process.returncode == 0
            
            if capture_output:
                result["stdout"] = process.stdout
                result["stderr"] = process.stderr
                
        except subprocess.TimeoutExpired:
            result["error"] = "Command timed out after 30 seconds"
        except FileNotFoundError:
            result["error"] = "Command not found"
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def check_system_info(self):
        """Check system information"""
        self.print_section("System Information")
        
        info = {
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": sys.version,
            "python_executable": sys.executable,
            "working_directory": os.getcwd()
        }
        
        for key, value in info.items():
            print(f"{key:20}: {value}")
        
        self.diagnostic_results["system_info"] = info
    
    def check_python_environment(self):
        """Check Python environment"""
        self.print_section("Python Environment")
        
        # Check pip
        pip_result = self.run_command([sys.executable, "-m", "pip", "--version"])
        print(f"pip: {'✅ Available' if pip_result['success'] else '❌ Not available'}")
        if pip_result['success']:
            print(f"  Version: {pip_result['stdout'].strip()}")
        
        # Check virtual environment
        venv_active = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        print(f"Virtual Environment: {'✅ Active' if venv_active else '❌ Not active'}")
        
        # Check key packages
        key_packages = ["PyQt6", "numpy", "pytest", "maturin"]
        for package in key_packages:
            try:
                __import__(package.lower())
                print(f"{package:20}: ✅ Installed")
            except ImportError:
                print(f"{package:20}: ❌ Not installed")
        
        self.diagnostic_results["python_environment"] = {
            "pip_available": pip_result['success'],
            "venv_active": venv_active,
            "pip_version": pip_result['stdout'].strip() if pip_result['success'] else None
        }
    
    def check_rust_toolchain(self):
        """Check Rust toolchain installation"""
        self.print_section("Rust Toolchain")
        
        rust_tools = ["rustc", "cargo", "rustup"]
        rust_status = {}
        
        for tool in rust_tools:
            result = self.run_command([tool, "--version"])
            if result['success']:
                print(f"{tool:20}: ✅ {result['stdout'].strip()}")
                rust_status[tool] = {
                    "available": True,
                    "version": result['stdout'].strip()
                }
            else:
                print(f"{tool:20}: ❌ Not found")
                rust_status[tool] = {
                    "available": False,
                    "error": result['error']
                }
        
        # Check Rust home directory
        rust_home = os.path.expanduser("~/.cargo")
        if os.path.exists(rust_home):
            print(f"Rust Home: ✅ {rust_home}")
            rust_status["rust_home"] = rust_home
        else:
            print(f"Rust Home: ❌ Not found")
            rust_status["rust_home"] = None
        
        # Check PATH for Rust
        path_entries = os.environ.get("PATH", "").split(os.pathsep)
        rust_in_path = any("cargo" in path for path in path_entries)
        print(f"Rust in PATH: {'✅ Yes' if rust_in_path else '❌ No'}")
        rust_status["rust_in_path"] = rust_in_path
        
        self.diagnostic_results["rust_toolchain"] = rust_status
    
    def check_maturin(self):
        """Check maturin installation"""
        self.print_section("Maturin (Rust-Python Bridge)")
        
        maturin_result = self.run_command(["maturin", "--version"])
        if maturin_result['success']:
            print(f"maturin: ✅ {maturin_result['stdout'].strip()}")
            self.diagnostic_results["maturin"] = {
                "available": True,
                "version": maturin_result['stdout'].strip()
            }
        else:
            print(f"maturin: ❌ Not found")
            print(f"  Error: {maturin_result['error']}")
            
            # Try to install maturin
            print("\nAttempting to install maturin...")
            install_result = self.run_command([sys.executable, "-m", "pip", "install", "maturin"])
            if install_result['success']:
                print("✅ maturin installed successfully")
                self.diagnostic_results["maturin"] = {"available": True, "installed": True}
            else:
                print("❌ Failed to install maturin")
                self.diagnostic_results["maturin"] = {"available": False, "install_error": install_result['error']}
    
    def check_rust_kernel_files(self):
        """Check Rust kernel source files"""
        self.print_section("Rust Kernel Source Files")
        
        required_files = [
            "rust_kernel/Cargo.toml",
            "rust_kernel/src/lib.rs",
            "rust_kernel/src/movegen.rs",
            "rust_kernel/src/solver.rs",
            "rust_kernel/build.py"
        ]
        
        files_status = {}
        for file_path in required_files:
            path = Path(file_path)
            if path.exists():
                size = path.stat().st_size
                print(f"{file_path:30}: ✅ {size:,} bytes")
                files_status[file_path] = {"exists": True, "size": size}
            else:
                print(f"{file_path:30}: ❌ Missing")
                files_status[file_path] = {"exists": False}
        
        self.diagnostic_results["rust_kernel_files"] = files_status
    
    def check_rust_kernel_build(self):
        """Check Rust kernel build status"""
        self.print_section("Rust Kernel Build Status")
        
        # Check if built extension exists
        try:
            import rust_kernel
            print("✅ Rust kernel module imported successfully")
            
            # Check availability
            if hasattr(rust_kernel, 'AVAILABLE'):
                print(f"Rust Available: {'✅ Yes' if rust_kernel.AVAILABLE else '❌ No'}")
                
                if rust_kernel.AVAILABLE:
                    # Test basic functionality
                    try:
                        b, w, stm = 0x0000000810000000, 0x0000001008000000, 0
                        legal = rust_kernel.legal_mask(b, w, stm)
                        print(f"Function Test: ✅ legal_mask returned {legal}")
                    except Exception as e:
                        print(f"Function Test: ❌ legal_mask failed: {e}")
                else:
                    print("⚠️  Rust kernel unavailable, using Python fallbacks")
                    
            else:
                print("⚠️  Rust kernel imported but AVAILABLE flag not found")
                
        except ImportError as e:
            print(f"❌ Rust kernel module import failed: {e}")
            print("This indicates the kernel was not built successfully")
        
        # Check build artifacts
        target_dir = self.rust_kernel_dir / "target"
        if target_dir.exists():
            print(f"Build Directory: ✅ {target_dir}")
            # List some build artifacts
            for item in target_dir.iterdir():
                if item.is_dir():
                    print(f"  - {item.name}/")
                else:
                    print(f"  - {item.name}")
        else:
            print("Build Directory: ❌ Not found")
        
        self.diagnostic_results["rust_kernel_build"] = {
            "import_success": "rust_kernel" in sys.modules,
            "available": getattr(rust_kernel, 'AVAILABLE', False) if "rust_kernel" in sys.modules else False,
            "target_dir_exists": target_dir.exists()
        }
    
    def check_python_fallbacks(self):
        """Check Python fallback implementations"""
        self.print_section("Python Fallback Implementations")
        
        fallback_modules = [
            "othello_coach.engine.movegen_fast",
            "othello_coach.insights.features",
            "othello_coach.engine.solver",
            "othello_coach.engine.board"
        ]
        
        fallback_status = {}
        for module in fallback_modules:
            try:
                __import__(module)
                print(f"{module:40}: ✅ Available")
                fallback_status[module] = True
            except ImportError as e:
                print(f"{module:40}: ❌ Not available: {e}")
                fallback_status[module] = False
        
        self.diagnostic_results["python_fallbacks"] = fallback_status
    
    def run_rust_tests(self):
        """Run Rust kernel tests"""
        self.print_section("Rust Kernel Tests")
        
        if "rust_kernel" in sys.modules:
            try:
                import rust_kernel
                if hasattr(rust_kernel, 'test_rust_functions'):
                    print("Running Rust kernel function tests...")
                    test_results = rust_kernel.test_rust_functions()
                    
                    for func_name, success in test_results.items():
                        status = "✅ PASS" if success else "❌ FAIL"
                        print(f"{func_name:20}: {status}")
                    
                    self.diagnostic_results["rust_tests"] = test_results
                else:
                    print("⚠️  test_rust_functions not available")
            except Exception as e:
                print(f"❌ Rust tests failed: {e}")
                self.diagnostic_results["rust_tests"] = {"error": str(e)}
        else:
            print("⚠️  Rust kernel not available for testing")
    
    def generate_recommendations(self):
        """Generate recommendations based on diagnostic results"""
        self.print_section("Recommendations")
        
        recommendations = []
        
        # Check Rust toolchain
        rust_status = self.diagnostic_results.get("rust_toolchain", {})
        if not rust_status.get("rustc", {}).get("available", False):
            recommendations.append("Install Rust toolchain: python install_rust.py")
        
        if not rust_status.get("rust_in_path", False):
            recommendations.append("Add Rust to PATH: run setup_env.bat or source setup_env.sh")
        
        # Check maturin
        maturin_status = self.diagnostic_results.get("maturin", {})
        if not maturin_status.get("available", False):
            recommendations.append("Install maturin: pip install maturin")
        
        # Check kernel build
        build_status = self.diagnostic_results.get("rust_kernel_build", {})
        if not build_status.get("import_success", False):
            recommendations.append("Build Rust kernel: python rust_kernel/build.py")
        
        # Check Python fallbacks
        fallback_status = self.diagnostic_results.get("python_fallbacks", {})
        missing_fallbacks = [mod for mod, available in fallback_status.items() if not available]
        if missing_fallbacks:
            recommendations.append(f"Install missing Python modules: {', '.join(missing_fallbacks)}")
        
        if recommendations:
            print("Issues found. Recommended actions:")
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
        else:
            print("✅ No issues detected. Rust integration is working correctly!")
        
        self.diagnostic_results["recommendations"] = recommendations
    
    def save_diagnostic_report(self):
        """Save diagnostic results to file"""
        report_file = self.project_root / "rust_diagnostic_report.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.diagnostic_results, f, indent=2)
        
        print(f"\n📄 Diagnostic report saved to: {report_file}")
    
    def run_diagnostics(self):
        """Run all diagnostic checks"""
        print("🔍 Othello Coach Rust Diagnostics")
        print("=" * 60)
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Project: {self.project_root}")
        
        try:
            self.check_system_info()
            self.check_python_environment()
            self.check_rust_toolchain()
            self.check_maturin()
            self.check_rust_kernel_files()
            self.check_rust_kernel_build()
            self.check_python_fallbacks()
            self.run_rust_tests()
            self.generate_recommendations()
            self.save_diagnostic_report()
            
        except Exception as e:
            print(f"\n❌ Diagnostics failed: {e}")
            import traceback
            traceback.print_exc()


def main():
    """Main entry point"""
    diagnostics = RustDiagnostics()
    diagnostics.run_diagnostics()


if __name__ == "__main__":
    main()
