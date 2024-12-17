# **DejaText** 📄✨  
**Identify Duplicate and Similar Text in Files**

**DejaText** is a Python-based command-line tool to scan directories of `.txt` or `.md` files, identify duplicated and optionally similar text segments (sentences, paragraphs, phrases, words) across or within files, and produce organized reports for easy review.

---

## **How It Works**

1. **Input**: Provide a directory containing `.txt` or `.md` files.  
   
2. **Processing**:  
   - **DejaText** scans each file based on your selected checks:
     - **Files**: Identify duplicate or similar file contents.
     - **Sentences**: Detect repeated or similar sentences across documents.
     - **Paragraphs**: Flag paragraphs found verbatim or with similarity in multiple files.
     - **Phrases**: Find recurring or similar multi-word phrases within and across files.
     - **Words**: Highlight words that appear frequently across files.
   - **Fuzzy Matching** (optional):  
     If enabled, DejaText uses a specified similarity threshold to consider non-identical but similar text as well. If disabled, only exact matches are reported.
       
3. **Output**:  
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
    
Dependencies
- typer (for CLI)
- difflib (standard library, used for similarity)
- csv, hashlib, re, string, os (standard library)

(The requirements.txt file should list any external dependencies.)

Usage

Run DejaText from the command line as follows:
```bash
python dejatext.py input_directory
```

- Replace `input_directory` with the path to a folder containing `.txt` or `.md` files.

For example:
```bash
python dejatext.py ./notes
```

Options

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

Example

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

Features
- Detects exact duplicates of files, sentences, paragraphs, phrases, and words.
- Optional fuzzy matching to find similar text above a specified similarity threshold.
- Automatically organizes results into a dedicated output directory.
- Produces both markdown reports and a summary CSV for quick reference.
- Flexibly enable/disable checks for different text segments.
- Easily adjust phrase length boundaries for more fine-grained control.
    
License

MIT License
    
Future Enhancements
- Additional filtering or grouping options.
- More sophisticated similarity scoring methods.
- Improved scalability and performance optimizations for very large document sets.

