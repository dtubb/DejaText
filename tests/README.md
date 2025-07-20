# Testing

This directory contains the comprehensive test suite for DejaText.

## Quick Start

```bash
# From project root
python run_tests.py --quick

# From tests directory
python run_tests.py --quick
```

## Test Structure

- `__init__.py` - Package initialization
- `conftest.py` - Pytest configuration and shared fixtures
- `run_tests.py` - Comprehensive test runner with categories
- `test_dejatext_cleanup.py` - Main test suite (90 tests)
- `pytest.ini` - Pytest configuration
- `requirements-test.txt` - Test dependencies

## Running Tests

### From Project Root
```bash
python run_tests.py                    # Full test suite
python run_tests.py --quick            # Quick smoke tests
python run_tests.py --yaml             # YAML handling tests
python run_tests.py --safety           # Text deletion safety tests
python run_tests.py --edge-cases       # Edge cases and error handling
python run_tests.py --verbose          # Full verbose output
python run_tests.py --coverage         # Run with coverage report
```

### From Tests Directory
```bash
cd tests
python run_tests.py                    # Full test suite
python -m pytest                      # Direct pytest
python -m pytest -k "yaml"            # Run specific tests
```

### Direct Pytest
```bash
python -m pytest tests/               # Run all tests
python -m pytest tests/ -v            # Verbose output
python -m pytest tests/ -k "yaml"     # Run tests matching "yaml"
```

## Test Categories

- **YAML Frontmatter Removal** - Tests YAML detection and removal
- **Critical Edge Cases** - Tests edge cases that could cause issues
- **Performance Edge Cases** - Tests large files and many files
- **CLI Edge Cases** - Tests command-line interface
- **Text Normalization** - Tests text processing for indexing
- **Text Splitting** - Tests sentence and paragraph splitting
- **Real-World Data** - Tests with realistic content scenarios
- **Duplicate Detection Options** - Tests different detection levels
- **Natural Sorting** - Tests filename sorting
- **Timeout Decorator** - Tests timeout functionality
- **File Operations** - Tests main cleanup functionality
- **Error Handling** - Tests error scenarios
- **Special Cases** - Tests special file and content types
- **YAML Preservation** - Tests YAML preservation during processing
- **Text Deletion Safety** - Tests that legitimate text isn't deleted

## Coverage

The test suite covers:
- ✅ Core functionality (YAML handling, text processing, duplicate detection)
- ✅ Edge cases (Unicode, special characters, large files, timeouts)
- ✅ Error handling (Invalid inputs, corrupted files, permission errors)
- ✅ CLI interface (Arguments, help text, validation)
- ✅ Real-world scenarios (Academic content, technical terms, complex YAML)
- ✅ Performance (Large files, many files, timeout protection)

## Dependencies

Install test dependencies:
```bash
pip install -r tests/requirements-test.txt
```

Or use the test runner:
```bash
python run_tests.py --install-deps
``` 