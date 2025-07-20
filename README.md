# **DejaText** 📄✨  
**Identify Duplicate and Similar Text in Files**

**Version**: 0.0.1.dev2

**DejaText** is a Python-based command-line tool to scan directories of `.txt` or `.md` files, identify duplicated and optionally similar text segments (sentences, paragraphs, phrases, words) across or within files, and produce organized reports for easy review.

---

## **How It Works**

1. **Input**: Provide a directory containing files. DejaText supports:
   - **Single files**: Point to the directory containing the file
   - **Single folders**: Primary use case
   - **Nested directories**: Recursively processes all subdirectories
   - **Complex directory structures**: Preserves the entire folder hierarchy
   
2. **File Processing**:  
   - **Supported file types**: Only `.txt` and `.md` files are processed for duplicate detection
   - **Case insensitive**: Handles `.txt`, `.TXT`, `.md`, `.MD`, `.Txt`, etc.
   - **Other file types**: All files are copied to preserve directory structure, but only text files are analyzed
   - **Natural sorting**: Files are processed in alphanumeric order (e.g., `file1.txt` before `file10.txt`)
   
3. **Processing**:  
   - **DejaText** scans each supported file based on your selected checks:
     - **Files**: Identify duplicate or similar file contents.
     - **Sentences**: Detect repeated or similar sentences across documents.
     - **Paragraphs**: Flag paragraphs found verbatim or with similarity in multiple files.
     - **Phrases**: Find recurring or similar multi-word phrases within and across files.
     - **Words**: Highlight words that appear frequently across files.
   - **YAML Frontmatter Handling**: Automatically detects and preserves YAML frontmatter in markdown files while removing it for duplicate detection. Supports complex YAML formats including field-prefixed YAML blocks.
   - **Fuzzy Matching** (optional):  
     If enabled, DejaText uses a specified similarity threshold to consider non-identical but similar text as well. If disabled, only exact matches are reported.
       
4. **Output**:  
   - A new folder, `dedup_output` by default, will be created to store reports.
   - Markdown reports detailing duplicated and similar text (if any) are generated:
     - `duplicated_*.md` for exact duplicates.
     - `similar_*.md` for items above your similarity threshold.
   - A `summary_report.csv` summarizing the counts and types of duplicates/similarities.
   - If no duplicates or similarities are found for a given category, no empty report is generated.
   - Optionally disable file references in reports with `--no-file-links`.
       
---

## **Installation**

### Requirements
- **Python 3.8 or later** (Check with `python --version`)
    
### Steps
1. Clone the repository:  
   ```bash
   git clone https://github.com/dtubb/dedup.git
   cd dedup
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Dependencies

- typer (for CLI)
- difflib (standard library, used for similarity)
- csv, hashlib, re, string, os (standard library)

### Virtual Environment Setup

```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On macOS/Linux
# or
.venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
```

## **Usage**

### **Main Application (dejatext.py)**

Run DejaText from the command line as follows:
```bash
python dejatext.py input_directory
```

- Replace `input_directory` with the path to a folder containing `.txt` or `.md` files.

### **Cleanup Application (dejatext_cleanup.py)**

For removing duplicates from files (rather than just reporting them):

```bash
python dejatext_cleanup.py input_directory
```

The cleanup script will:
- ✅ Copy all files to a new directory with `_cleanup` suffix
- ✅ Remove duplicate files entirely
- ✅ Mark duplicate sentences/paragraphs with `{del}` tags
- ✅ Preserve YAML frontmatter
- ✅ Show detailed progress with `--verbose` flag

For example:
```bash
python dejatext.py ./notes
```

### **Shell Script Usage**

For convenience, you can use the included shell script:

```bash
# Make the script executable (first time only)
chmod +x dejatext_cleanup.sh

# Run the script with a directory
./dejatext_cleanup.sh /path/to/your/directory

# Run with multiple directories
./dejatext_cleanup.sh /path/to/dir1 /path/to/dir2
```

The script will:
- ✅ Automatically activate the virtual environment
- ✅ Process each input directory
- ✅ Create output folders with `_cleanup` suffix
- ✅ Show verbose progress information
- ✅ Handle multiple input directories

### **Automator Workflow Integration**

You can integrate DejaText with macOS Automator for easy file processing:

1. **Create a new Automator workflow**
2. **Add "Run Shell Script" action**
3. **Set shell to `/bin/zsh`**
4. **Paste the following script:**

```bash
# Path to your dejatext_cleanup.sh script
/Users/yourusername/code/dejatext/dejatext_cleanup.sh "$@"
```

5. **Save as "Quick Action" or "Service"**
6. **Configure to receive files/folders in Finder**

Now you can right-click any folder in Finder and select your service to process it with DejaText!

### **Supported Input Types**

| Input Type | Description | Example |
|------------|-------------|---------|
| **Single file** | Point to directory containing the file | `python dejatext.py ./folder_with_one_file` |
| **Single folder** | Process all files in one directory | `python dejatext.py ./notes` |
| **Nested folders** | Recursively process all subdirectories | `python dejatext.py ./project_docs` |
| **Complex structure** | Handles any depth of nested folders | `python dejatext.py ./research_papers` |

### **File Type Support**

| File Type | Processing | Example |
|-----------|------------|---------|
| **`.txt`** | ✅ Full processing | `document.txt`, `notes.TXT` |
| **`.md`** | ✅ Full processing | `readme.md`, `article.MD` |
| **`.py`** | ❌ Copied but not processed | `script.py` |
| **`.json`** | ❌ Copied but not processed | `data.json` |
| **`.jpg`** | ❌ Copied but not processed | `image.jpg` |
| **No extension** | ❌ Copied but not processed | `notes` |

**Note**: All files are copied to preserve directory structure, but only `.txt` and `.md` files are analyzed for duplicates.

### **File Processing Details**

- **Natural Sorting**: Files are processed in alphanumeric order:
  - `file1.txt` → `file2.txt` → `file10.txt` (not `file1.txt` → `file10.txt` → `file2.txt`)
  - `a1.txt` → `a2.txt` → `a10.txt` → `b1.txt`
  - Handles leading zeros: `file001.txt` → `file01.txt` → `file1.txt`

- **Directory Structure**: 
  - ✅ Preserves all subdirectories and folder hierarchy
  - ✅ Handles empty directories gracefully
  - ✅ Maintains relative paths in output
  - ✅ Supports special characters in filenames

- **Case Insensitive**: 
  - `.txt`, `.TXT`, `.Txt` are all treated as text files
  - `.md`, `.MD`, `.Md` are all treated as markdown files

### Options

| Option                   | Description                                      | Default         |
|--------------------------|--------------------------------------------------|-----------------|
| --output-folder          | Path to folder for output reports.              | dedup_output    |
| --check-files/--no-check-files            | Check for duplicate/similar entire files.        | True            |
| --check-sentences/--no-check-sentences    | Check for duplicate/similar sentences.            | True            |
| --check-paragraphs/--no-check-paragraphs  | Check for duplicate/similar paragraphs.          | True            |
| --check-phrases/--no-check-phrases        | Check for duplicate/similar phrases.             | True            |
| --check-words/--no-check-words            | Check for duplicate/similar words.               | True            |
| --min-phrase-length                        | Minimum words in a phrase.                       | 2               |
| --max-phrase-length                        | Maximum words in a phrase.                       | 20              |
| --fuzzy/--no-fuzzy                          | Enable fuzzy matching (similarity scoring)       | False           |
| --fuzz-threshold                           | Minimum similarity percentage for fuzzy matches  | 90              |
| --no-file-links                            | Disable listing file names in the reports        | False           |

### Example

Assume you have the following files in the notes directory:

file1.txt:
```
This is an example sentence.
This is an example sentence.
Something new here.
```

file2.txt:
```
This is an example sentence.
Another line here.
```

Running:
```bash
python dejatext.py ./notes
```

Possible output (if duplicates are found):
- `dedup_output/duplicated_sentences.md` might show the repeated sentence inside `file1.txt` and across `file1.txt` and `file2.txt`.
- `summary_report.csv` summarizes the number of duplicates found.

If no duplicates are found in any category, no empty reports are created, and the summary remains minimal.

---

## **Version Information**

### **Current Version**
- **DejaText**: 0.0.1.dev2
- **DejaText Cleanup**: 0.0.1.dev2

### **Check Version**
To check the current version of either application:

```bash
# Check DejaText version
python dejatext.py version

# Check DejaText Cleanup version  
python dejatext_cleanup.py version
```

### **Changelog**
See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes and improvements.

---

## **Development**

### **Testing**
Run the comprehensive test suite:

```bash
# Run all tests
python tests/run_tests.py

# Run specific test categories
python tests/run_tests.py --unit
python tests/run_tests.py --integration
python tests/run_tests.py --yaml
```

### **Previous Versions**
- **0.0.1.dev1**: Initial implementation with basic duplicate detection
- **0.0.1.dev2**: Enhanced testing, automation, and documentation