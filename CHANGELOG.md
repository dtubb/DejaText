# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.1.dev2] - 2025-07-20

### Added
- Comprehensive test suite with pytest
- Dedicated `tests/` folder with organized test structure
- Test runner script (`tests/run_tests.py`) supporting categorized test execution
- Shell script (`dejatext_cleanup.sh`) for automation with virtual environment activation
- Updated `dejatext.sh` to work with `dejatext_cleanup.py` instead of structur
- Enhanced YAML frontmatter detection for complex multi-block YAML
- Natural sorting of filenames using custom `natural_sort_key` function
- Comprehensive README documentation with usage examples
- Virtual environment setup instructions
- Automator workflow integration documentation

### Changed
- Improved file extension filtering to be case-insensitive
- Enhanced directory structure preservation in cleanup operations
- Updated `.gitignore` to include Python, testing, IDE, and system files
- Refactored test organization into dedicated `tests/` folder
- Updated requirements.txt to only include external dependencies

### Fixed
- YAML frontmatter regex pattern to handle complex multi-block YAML with field lines
- File extension filtering case sensitivity issues in tests
- Test runner paths after moving tests to `tests/` folder
- Requirements file to exclude standard library modules
- Shell script command syntax for `dejatext_cleanup.py`

### Technical
- Added pytest configuration (`tests/pytest.ini`)
- Created test fixtures and conftest.py for shared test resources
- Implemented comprehensive test coverage for file handling, YAML processing, and duplicate detection
- Added test requirements file (`tests/requirements-test.txt`)

## [0.0.1.dev1] - 2024-12-07

### Added
- Initial implementation of DejaText text processing tool
- YAML frontmatter detection and removal
- Duplicate detection at file, paragraph, and sentence levels
- CLI interface using typer
- Basic file and directory processing capabilities
- Support for .txt and .md file types
- Directory structure preservation during processing
- Basic README documentation

### Technical
- Python CLI application using typer
- Text processing with sentence and paragraph splitting
- Regex-based YAML frontmatter detection
- File system operations with directory copying and filtering 