"""
Pytest configuration and shared fixtures for dejatext tests.
"""
import os
import sys
import tempfile
import shutil
import pytest

# Add the parent directory to the path so we can import dejatext_cleanup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def test_files(temp_dir):
    """Create test files in a temporary directory."""
    input_dir = os.path.join(temp_dir, "input")
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(input_dir)
    
    # Create some basic test files
    with open(os.path.join(input_dir, "file1.txt"), "w") as f:
        f.write("This is unique content in file 1.")
    
    with open(os.path.join(input_dir, "file2.txt"), "w") as f:
        f.write("This is unique content in file 1.")  # Duplicate of file1
    
    with open(os.path.join(input_dir, "file3.md"), "w") as f:
        f.write("""---
title: Test File
---
This is content after YAML frontmatter.

This is a second paragraph.""")
    
    return {
        'temp_dir': temp_dir,
        'input_dir': input_dir,
        'output_dir': output_dir
    } 