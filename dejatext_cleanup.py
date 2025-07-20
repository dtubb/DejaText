import os
import re
import shutil
import string
import typer
import signal
from contextlib import contextmanager

__version__ = "0.0.1.dev2"

app = typer.Typer()

@app.command()
def version():
    """Show the version of DejaText Cleanup."""
    typer.echo(f"DejaText Cleanup version {__version__}")

@contextmanager
def timeout(seconds):
    """Context manager for timeout handling."""
    def signal_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    
    # Set the signal handler and a 5-second alarm
    old_handler = signal.signal(signal.SIGALRM, signal_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split(r'([0-9]+)', str(s))]

def remove_yaml_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from the beginning of text content."""
    # More comprehensive YAML detection that handles various formats
    
    # Pattern 1: Standard YAML with --- delimiters
    yaml_content_pattern = r'^---\s*\n((?:[a-zA-Z_][a-zA-Z0-9_]*\s*:.*\n)|(?:#.*\n)|(?:\s*-\s+.*\n)|(?:\s*\n))*---\s*\n?'
    
    # Pattern 2: YAML with first line before ---
    first_line_yaml_pattern = r'^[^\n]*\n---\s*\n((?:[a-zA-Z_][a-zA-Z0-9_]*\s*:.*\n)|(?:#.*\n)|(?:\s*-\s+.*\n)|(?:\s*\n))*---\s*\n?'
    
    # Pattern 3: YAML that starts with a field (like Path:) followed by --- blocks
    field_start_yaml_pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*\s*:.*\n(?:\s*\n)*((?:---\s*\n((?:[a-zA-Z_][a-zA-Z0-9_]*\s*:.*\n)|(?:#.*\n)|(?:\s*-\s+.*\n)|(?:\s*\n))*---\s*\n?)+)'
    
    # Keep removing YAML frontmatter blocks until none are left
    while True:
        # Try the standard YAML pattern first
        match = re.match(yaml_content_pattern, content, re.DOTALL)
        if match:
            # Remove the frontmatter and continue
            content = content[match.end():]
            continue
            
        # Try the pattern with first line before YAML
        match = re.match(first_line_yaml_pattern, content, re.DOTALL)
        if match:
            # Remove the frontmatter and continue
            content = content[match.end():]
            continue
            
        # Try the field-start pattern (for cases like "Path: ..." followed by YAML blocks)
        match = re.match(field_start_yaml_pattern, content, re.DOTALL)
        if match:
            # Remove the frontmatter and continue
            content = content[match.end():]
            continue
            
        # No more matches
        break
    
    return content

def normalize_text_for_indexing(text: str) -> str:
    """Normalize text while preserving underscores in Markdown emphasis."""
    return text.lower().translate(str.maketrans('', '', string.punctuation.replace("_", ""))).strip()

def split_paragraphs(content: str) -> list:
    """Split text into paragraphs."""
    # Split on multiple newlines or other whitespace patterns
    paragraphs = re.split(r'\n\s*\n+', content)
    return [p.strip() for p in paragraphs if p.strip()]

def split_sentences(content: str) -> list:
    """Split text into sentences, fixing hyphenated words."""
    content = re.sub(r"(\w)-\n(\w)", r"\1\2", content)  # Fix hyphenated words split over lines
    
    # Simple sentence splitting that avoids common abbreviations
    # Split on sentence endings followed by whitespace, but be more careful
    # This is a simpler approach that works better for most cases
    sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', content)
    
    # Clean up the results - remove empty strings and strip whitespace
    result = []
    for sentence in sentences:
        sentence = sentence.strip()
        if sentence:
            result.append(sentence)
    
    return result

@app.command()
def cleanup(
    input_directory: str,
    output_folder: str = "cleanup_output",
    check_files: bool = typer.Option(True, "--check-files/--no-check-files"),
    check_sentences: bool = typer.Option(True, "--check-sentences/--no-check-sentences"),
    check_paragraphs: bool = typer.Option(True, "--check-paragraphs/--no-check-paragraphs"),
    verbose: bool = typer.Option(False, "--verbose", help="Show detailed progress information")
):
    if not (check_files or check_sentences or check_paragraphs):
        typer.echo("Error: At least one type of check must be enabled.")
        raise typer.Exit(1)

    # Copy folder structure
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    
    # Copy files with error handling for unreadable files
    try:
        shutil.copytree(input_directory, output_folder)
        typer.echo(f"Copied folder structure from {input_directory} to {output_folder}")
    except (OSError, PermissionError) as e:
        if "No such file or directory" in str(e):
            typer.echo(f"Error: Input directory '{input_directory}' does not exist.")
            raise typer.Exit(1)
        typer.echo(f"Error copying folder structure: {e}")
        # Try to create output directory and copy readable files manually
        os.makedirs(output_folder, exist_ok=True)
        for root, dirs, files in os.walk(input_directory):
            # Create corresponding directories in output
            rel_path = os.path.relpath(root, input_directory)
            output_root = os.path.join(output_folder, rel_path)
            os.makedirs(output_root, exist_ok=True)
            
            # Copy readable files
            for file in files:
                src_file = os.path.join(root, file)
                dst_file = os.path.join(output_root, file)
                try:
                    shutil.copy2(src_file, dst_file)
                except (OSError, PermissionError) as copy_error:
                    typer.echo(f"Error copying file {src_file}: {copy_error}")
        typer.echo(f"Copied readable files from {input_directory} to {output_folder}")

    all_files = []
    for root, _, files in os.walk(output_folder):
        for file in files:
            if file.endswith('.txt') or file.endswith('.md'):
                all_files.append(os.path.join(root, file))
    all_files.sort(key=natural_sort_key)
    typer.echo(f"Found {len(all_files)} files to process")

    file_index = {}
    paragraph_index = {}
    sentence_index = {}

    if verbose:
        typer.echo("Starting to process files...")

    def add_to_index(idx, item, file_path):
        """Add text segments to indexing while avoiding very short words."""
        norm = normalize_text_for_indexing(item)
        if not norm or len(norm) < 3:  # Ignore single-letter or two-letter words
            return
        if norm not in idx:
            idx[norm] = {'files': [], 'original': item, 'occurrences': []}
        idx[norm]['files'].append(file_path)
        idx[norm]['occurrences'].append((file_path, item))

    for i, file_path in enumerate(all_files):
        if verbose and i % 100 == 0:
            typer.echo(f"Processing file {i+1}/{len(all_files)}: {os.path.basename(file_path)}")
        
        # Skip problematic files that we know cause issues
        if "210 2024-09-16_12-54_Recording_11_2.md" in file_path:
            typer.echo(f"Skipping problematic file: {os.path.basename(file_path)}")
            continue
        
        try:
            with timeout(30):  # 30 second timeout per file
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Remove YAML frontmatter before processing (but keep in file)
                content = remove_yaml_frontmatter(content)
        except (TimeoutError, OSError, UnicodeDecodeError) as e:
            typer.echo(f"Error processing file {file_path}: {e}")
            continue

        if check_files:
            add_to_index(file_index, content, file_path)

        if check_paragraphs:
            paragraphs = split_paragraphs(content)
            for p in paragraphs:
                add_to_index(paragraph_index, p, file_path)

        if check_sentences:
            sentences = split_sentences(content)
            for s in sentences:
                add_to_index(sentence_index, s, file_path)

    def delete_duplicates(index, content_type):
        """Delete duplicates while avoiding partial deletions of Markdown-styled text."""
        if verbose:
            typer.echo(f"Processing {content_type} duplicates...")
        
        total_items = len([k for k in index.keys() if len(k) >= 3])
        processed = 0
        
        for norm, data in index.items():
            if len(norm) < 3:  # Skip very short words
                continue
                
            # Process if it appears multiple times (either across files or within files)
            if len(data['occurrences']) < 2:
                continue  # Skip unique content that appears only once
                
            processed += 1
            if verbose and processed % 100 == 0:
                typer.echo(f"Processing {content_type} item {processed}/{total_items}")

            # Group occurrences by file and sort files
            file_occurrences = {}
            for file_path, item in data['occurrences']:
                if file_path not in file_occurrences:
                    file_occurrences[file_path] = []
                file_occurrences[file_path].append(item)
            
            sorted_files = sorted(file_occurrences.keys(), key=natural_sort_key)
            first_file = sorted_files[0]  # Keep first occurrence
            
            # Process each file that has duplicates
            for file_path in sorted_files:
                occurrences_in_file = file_occurrences[file_path]
                
                # For file-level duplicates, delete all but the first file
                if content_type == 'file':
                    if file_path != first_file:
                        try:
                            os.remove(file_path)
                            typer.echo(f"Deleted duplicate file: {file_path}")
                        except (OSError) as e:
                            typer.echo(f"Error deleting file {file_path}: {e}")
                    continue
                
                # For paragraph/sentence duplicates, keep first occurrence in first file
                # For subsequent files or additional occurrences in first file, mark with {del}
                should_mark_duplicates = (file_path != first_file) or len(occurrences_in_file) > 1
                
                if not should_mark_duplicates:
                    continue  # Keep first occurrence in first file
                
                try:
                    with timeout(30):  # 30 second timeout per file
                        if os.path.exists(file_path):
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                        else:
                            continue  # Skip if file doesn't exist

                        # Remove YAML frontmatter before processing for deletion
                        content = remove_yaml_frontmatter(content)
                        
                        # Process all files regardless of size - timeout protection is sufficient
                        
                        # For internal duplicates, we need to mark all but the first occurrence
                        # For cross-file duplicates, we mark all occurrences in subsequent files
                        if file_path == first_file and len(occurrences_in_file) > 1:
                            # Internal duplicates in first file - mark all but first occurrence
                            pattern_compiled = re.compile(re.escape(data['original']), re.DOTALL | re.MULTILINE)
                            
                            def replace_matches(match):
                                # Count how many times we've seen this match
                                if not hasattr(replace_matches, 'count'):
                                    replace_matches.count = 0
                                replace_matches.count += 1
                                # Keep first occurrence, mark others with {del}
                                return match.group(0) if replace_matches.count == 1 else "{del}"
                            
                            new_content = pattern_compiled.sub(replace_matches, content)
                        else:
                            # Cross-file duplicates or subsequent files - mark all occurrences
                            pattern_compiled = re.compile(re.escape(data['original']), re.DOTALL | re.MULTILINE)
                            
                            def replace_matches(m):
                                return "{del}" if m.group(0).strip() == data['original'].strip() else m.group(0)
                            
                            new_content = pattern_compiled.sub(replace_matches, content)
                        
                        # Write the updated content if it changed
                        if new_content != content:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                f.write(new_content)
                            if verbose:
                                typer.echo(f"Updated file with deleted {content_type}: {os.path.basename(file_path)}")
                            else:
                                typer.echo(f"Updated file with deleted {content_type}: {file_path}")
                                
                except (TimeoutError, OSError, UnicodeDecodeError) as e:
                    typer.echo(f"Error processing file {file_path} for deletion: {e}")
                    continue

    if check_files:
        delete_duplicates(file_index, 'file')

    if check_paragraphs:
        delete_duplicates(paragraph_index, 'paragraph')

    if check_sentences:
        delete_duplicates(sentence_index, 'sentence')

    typer.echo("Cleanup completed, duplicates removed.")

if __name__ == "__main__":
    app()