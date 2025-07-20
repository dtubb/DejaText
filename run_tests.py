#!/usr/bin/env python3
"""
Comprehensive Test Runner for DejaText Cleanup

This script provides various options for running the test suite with different
levels of detail and focus areas.
"""

import sys
import subprocess
import argparse
import os

def run_command(cmd, description):
    """Run a command and display results"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ SUCCESS")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print("❌ FAILED")
        print(f"Exit code: {e.returncode}")
        print("STDOUT:")
        print(e.stdout)
        print("STDERR:")
        print(e.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive Test Runner for DejaText Cleanup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py --quick                    # Quick smoke test
  python run_tests.py --yaml                     # Test YAML handling
  python run_tests.py --safety                   # Test text deletion safety
  python run_tests.py --verbose                  # Full verbose test run
  python run_tests.py --coverage                 # Run with coverage report
  python run_tests.py --failed                   # Run only failed tests
  python run_tests.py --list                     # List all test categories
        """
    )
    
    parser.add_argument('--quick', action='store_true',
                       help='Run quick smoke tests only')
    parser.add_argument('--yaml', action='store_true',
                       help='Test YAML frontmatter handling')
    parser.add_argument('--safety', action='store_true',
                       help='Test text deletion safety')
    parser.add_argument('--edge-cases', action='store_true',
                       help='Test edge cases and error handling')
    parser.add_argument('--verbose', action='store_true',
                       help='Run all tests with verbose output')
    parser.add_argument('--coverage', action='store_true',
                       help='Run tests with coverage report')
    parser.add_argument('--failed', action='store_true',
                       help='Run only previously failed tests')
    parser.add_argument('--list', action='store_true',
                       help='List all available test categories')
    parser.add_argument('--install-deps', action='store_true',
                       help='Install test dependencies')
    
    args = parser.parse_args()
    
    # Check if pytest is available
    try:
        import pytest
    except ImportError:
        print("❌ pytest not found. Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"], check=True)
    
    if args.install_deps:
        print("Installing test dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements-test.txt"], check=True)
        print("✅ Dependencies installed")
        return
    
    if args.list:
        print("📋 Available Test Categories:")
        print("\n🔧 Core Functionality:")
        print("  --yaml          YAML frontmatter handling")
        print("  --safety        Text deletion safety")
        print("  --edge-cases    Edge cases and error handling")
        print("\n⚡ Quick Tests:")
        print("  --quick         Smoke tests")
        print("  --failed        Previously failed tests")
        print("\n📊 Full Testing:")
        print("  --verbose       All tests with verbose output")
        print("  --coverage      Tests with coverage report")
        print("\n🛠️  Setup:")
        print("  --install-deps  Install test dependencies")
        return
    
    # Define test categories
    test_categories = {
        'quick': [
            'test_dejatext_cleanup.py::TestFileOperations::test_basic_cleanup',
            'test_dejatext_cleanup.py::TestYAMLFrontmatterRemoval::test_basic_yaml_frontmatter',
            'test_dejatext_cleanup.py::TestTextDeletionSafety::test_unique_content_not_deleted'
        ],
        'yaml': [
            'test_dejatext_cleanup.py::TestYAMLFrontmatterRemoval',
            'test_dejatext_cleanup.py::TestYAMLPreservation'
        ],
        'safety': [
            'test_dejatext_cleanup.py::TestTextDeletionSafety'
        ],
        'edge-cases': [
            'test_dejatext_cleanup.py::TestErrorHandling',
            'test_dejatext_cleanup.py::TestSpecialCases'
        ]
    }
    
    success_count = 0
    total_count = 0
    
    if args.quick:
        print("🚀 Running Quick Smoke Tests...")
        for test in test_categories['quick']:
            total_count += 1
            if run_command([sys.executable, "-m", "pytest", test, "-v"], f"Quick test: {test}"):
                success_count += 1
    
    elif args.yaml:
        print("📄 Testing YAML Frontmatter Handling...")
        for category in test_categories['yaml']:
            total_count += 1
            if run_command([sys.executable, "-m", "pytest", category, "-v"], f"YAML tests: {category}"):
                success_count += 1
    
    elif args.safety:
        print("🛡️ Testing Text Deletion Safety...")
        for category in test_categories['safety']:
            total_count += 1
            if run_command([sys.executable, "-m", "pytest", category, "-v"], f"Safety tests: {category}"):
                success_count += 1
    
    elif args.edge_cases:
        print("🔍 Testing Edge Cases and Error Handling...")
        for category in test_categories['edge-cases']:
            total_count += 1
            if run_command([sys.executable, "-m", "pytest", category, "-v"], f"Edge case tests: {category}"):
                success_count += 1
    
    elif args.verbose:
        print("📊 Running Full Test Suite with Verbose Output...")
        total_count += 1
        if run_command([sys.executable, "-m", "pytest", "test_dejatext_cleanup.py", "-v", "-s"], "Full test suite"):
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
            sys.executable, "-m", "coverage", "run", "-m", "pytest", "test_dejatext_cleanup.py", "-v"
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
        if run_command([sys.executable, "-m", "pytest", "test_dejatext_cleanup.py", "--lf", "-v"], "Failed tests"):
            success_count += 1
    
    else:
        # Default: run all tests
        print("🧪 Running Complete Test Suite...")
        total_count += 1
        if run_command([sys.executable, "-m", "pytest", "test_dejatext_cleanup.py", "-v"], "Complete test suite"):
            success_count += 1
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 Test Summary: {success_count}/{total_count} test runs successful")
    if success_count == total_count:
        print("🎉 All tests passed!")
    else:
        print("⚠️ Some tests failed. Check output above for details.")
    print('='*60)

if __name__ == "__main__":
    main() 