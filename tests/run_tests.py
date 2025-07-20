#!/usr/bin/env python3
"""
Comprehensive test runner for dejatext.
Supports running different test categories and provides detailed output.
"""

import sys
import subprocess
import argparse
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✅ SUCCESS")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ FAILED")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="Run dejatext test suite")
    parser.add_argument("--quick", action="store_true", help="Run quick smoke tests")
    parser.add_argument("--yaml", action="store_true", help="Run YAML handling tests")
    parser.add_argument("--safety", action="store_true", help="Run text deletion safety tests")
    parser.add_argument("--edge-cases", action="store_true", help="Run edge cases and error handling")
    parser.add_argument("--verbose", action="store_true", help="Run all tests with verbose output")
    parser.add_argument("--coverage", action="store_true", help="Run tests with coverage report")
    parser.add_argument("--failed", action="store_true", help="Run previously failed tests")
    parser.add_argument("--install-deps", action="store_true", help="Install test dependencies")
    parser.add_argument("--list", action="store_true", help="List available test categories")
    
    args = parser.parse_args()
    
    if args.install_deps:
        print("Installing test dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"], check=True)
        print("✅ Dependencies installed")
        return
    
    if args.list:
        print("📋 Available Test Categories:")
        print()
        print("🔧 Core Functionality:")
        print("  --yaml          YAML frontmatter handling")
        print("  --safety        Text deletion safety")
        print("  --edge-cases    Edge cases and error handling")
        print()
        print("⚡ Quick Tests:")
        print("  --quick         Smoke tests")
        print("  --failed        Previously failed tests")
        print()
        print("📊 Full Testing:")
        print("  --verbose       All tests with verbose output")
        print("  --coverage      Tests with coverage report")
        print()
        print("🛠️  Setup:")
        print("  --install-deps  Install test dependencies")
        return
    
    # Define test categories
    test_categories = {
        'quick': [
            'tests/test_dejatext_cleanup.py::TestFileOperations::test_basic_cleanup',
            'tests/test_dejatext_cleanup.py::TestYAMLFrontmatterRemoval::test_basic_yaml_frontmatter',
            'tests/test_dejatext_cleanup.py::TestTextDeletionSafety::test_unique_content_not_deleted'
        ],
        'yaml': [
            'tests/test_dejatext_cleanup.py::TestYAMLFrontmatterRemoval',
            'tests/test_dejatext_cleanup.py::TestYAMLPreservation'
        ],
        'safety': [
            'tests/test_dejatext_cleanup.py::TestTextDeletionSafety'
        ],
        'edge-cases': [
            'tests/test_dejatext_cleanup.py::TestErrorHandling',
            'tests/test_dejatext_cleanup.py::TestSpecialCases'
        ]
    }
    
    total_count = 0
    success_count = 0
    
    if args.quick:
        print("🚀 Running Quick Smoke Tests...")
        for test in test_categories['quick']:
            total_count += 1
            if run_command([sys.executable, "-m", "pytest", test, "-v"], f"Quick test: {test}"):
                success_count += 1
    
    elif args.yaml:
        print("📄 Running YAML Handling Tests...")
        total_count += 1
        if run_command([sys.executable, "-m", "pytest", "tests/test_dejatext_cleanup.py::TestYAMLFrontmatterRemoval", "-v"], "YAML frontmatter removal"):
            success_count += 1
        total_count += 1
        if run_command([sys.executable, "-m", "pytest", "tests/test_dejatext_cleanup.py::TestYAMLPreservation", "-v"], "YAML preservation"):
            success_count += 1
    
    elif args.safety:
        print("🛡️ Running Text Deletion Safety Tests...")
        total_count += 1
        if run_command([sys.executable, "-m", "pytest", "tests/test_dejatext_cleanup.py::TestTextDeletionSafety", "-v"], "Text deletion safety"):
            success_count += 1
    
    elif args.edge_cases:
        print("🔍 Running Edge Cases and Error Handling Tests...")
        total_count += 1
        if run_command([sys.executable, "-m", "pytest", "tests/test_dejatext_cleanup.py::TestErrorHandling", "-v"], "Error handling"):
            success_count += 1
        total_count += 1
        if run_command([sys.executable, "-m", "pytest", "tests/test_dejatext_cleanup.py::TestSpecialCases", "-v"], "Special cases"):
            success_count += 1
    
    elif args.verbose:
        print("📊 Running Full Test Suite with Verbose Output...")
        total_count += 1
        if run_command([sys.executable, "-m", "pytest", "tests/test_dejatext_cleanup.py", "-v", "-s"], "Full test suite"):
            success_count += 1
    
    elif args.coverage:
        print("📈 Running Tests with Coverage Report...")
        # Install coverage if not available
        try:
            import coverage
        except ImportError:
            print("Installing coverage...")
            subprocess.run([sys.executable, "-m", "pip", "install", "coverage"], check=True)
        
        total_count += 1
        if run_command([
            sys.executable, "-m", "coverage", "run", "-m", "pytest", "tests/test_dejatext_cleanup.py", "-v"
        ], "Tests with coverage"):
            success_count += 1
        
        # Generate coverage report
        print("\n📊 Coverage Report:")
        subprocess.run([sys.executable, "-m", "coverage", "report"])
        subprocess.run([sys.executable, "-m", "coverage", "html"])
        print("📁 HTML coverage report generated in htmlcov/")
    
    elif args.failed:
        print("🔄 Running Previously Failed Tests...")
        total_count += 1
        if run_command([sys.executable, "-m", "pytest", "tests/test_dejatext_cleanup.py", "--lf", "-v"], "Failed tests"):
            success_count += 1
    
    else:
        # Default: run all tests
        print("🧪 Running Complete Test Suite...")
        total_count += 1
        if run_command([sys.executable, "-m", "pytest", "tests/test_dejatext_cleanup.py", "-v"], "Complete test suite"):
            success_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Test Summary: {success_count}/{total_count} test runs successful")
    if success_count == total_count:
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed!")
    print(f"{'='*60}")

if __name__ == "__main__":
    main() 