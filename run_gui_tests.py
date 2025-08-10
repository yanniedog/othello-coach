#!/usr/bin/env python3
"""Comprehensive GUI test runner for Othello Coach"""

import sys
import os
import subprocess
import time
from pathlib import Path

def run_tests():
    """Run all GUI tests with comprehensive reporting"""
    
    # Ensure we're in the right directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Activate virtual environment if it exists
    venv_python = project_root / "venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = project_root / "venv" / "bin" / "python"
    
    if venv_python.exists():
        python_cmd = str(venv_python)
    else:
        python_cmd = "python"
    
    print("🚀 Starting comprehensive GUI tests...")
    print("=" * 60)
    
    # Install test dependencies if needed
    print("📦 Installing test dependencies...")
    try:
        subprocess.run([python_cmd, "-m", "pip", "install", "pytest", "pytest-qt", "pytest-cov"], 
                      check=True, capture_output=True)
        print("✅ Dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Warning: Could not install dependencies: {e}")
    
    # Run the comprehensive test suite
    print("\n🧪 Running comprehensive GUI tests...")
    start_time = time.time()
    
    try:
        result = subprocess.run([
            python_cmd, "-m", "pytest", 
            "tests/test_gui_comprehensive.py",
            "-v",
            "--tb=short",
            "--durations=10",
            "--cov=othello_coach",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml"
        ], check=False, capture_output=False)
        
        test_time = time.time() - start_time
        
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        if result.returncode == 0:
            print("✅ All tests passed!")
        else:
            print(f"❌ Some tests failed (exit code: {result.returncode})")
        
        print(f"⏱️  Total test time: {test_time:.2f} seconds")
        print(f"📁 Coverage reports saved to:")
        print(f"   - HTML: htmlcov/index.html")
        print(f"   - XML: coverage.xml")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"💥 Test execution failed: {e}")
        return False

def run_specific_test_suite(suite_name):
    """Run a specific test suite"""
    
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    venv_python = project_root / "venv" / "Scripts" / "python.exe"
    if not venv_python.exists():
        venv_python = project_root / "venv" / "bin" / "python"
    
    if venv_python.exists():
        python_cmd = str(venv_python)
    else:
        python_cmd = "python"
    
    print(f"🧪 Running {suite_name} tests...")
    
    try:
        result = subprocess.run([
            python_cmd, "-m", "pytest", 
            f"tests/test_gui_comprehensive.py::{suite_name}",
            "-v",
            "--tb=short"
        ], check=False, capture_output=False)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"💥 Test execution failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        suite_name = sys.argv[1]
        success = run_specific_test_suite(suite_name)
    else:
        success = run_tests()
    
    sys.exit(0 if success else 1)
