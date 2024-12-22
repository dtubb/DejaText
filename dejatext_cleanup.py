import os
import re
import shutil
import hashlib
import string
import typer
from difflib import SequenceMatcher

app = typer.Typer()

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', str(s))]

def normalize_text_for_indexing(text: str) -> str:
    return text.lower().translate(str.maketrans('', '', string.punctuation)).strip()

def split_paragraphs(content: str) -> list:
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    return paragraphs

def split_sentences(content: str) -> list:
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', content)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences

@app.command()
def cleanup(
    input_directory: str,
    output_folder: str = "cleanup_output",
    check_files: bool = typer.Option(True, "--check-files/--no-check-files"),
    check_sentences: bool = typer.Option(True, "--check-sentences/--no-check-sentences"),
    check_paragraphs: bool = typer.Option(True, "--check-paragraphs/--no-check-paragraphs")
):
    if not (check_files or check_sentences or check_paragraphs):
        typer.echo("Error: At least one type of check must be enabled.")
        raise typer.Exit(1)

    # Copy the original folder structure to the output directory
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    shutil.copytree(input_directory, output_folder)
    typer.echo(f"Copied folder structure from {input_directory} to {output_folder}")

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

    def add_to_index(idx, item, file_path):
        norm = normalize_text_for_indexing(item)
        if not norm:
            return
        if norm not in idx:
            idx[norm] = {'files':[], 'original': item}
        idx[norm]['files'].append(file_path)

    for file_path in all_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

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
        for norm, data in index.items():
            files = data['files']
            if len(files) > 1:
                for file_path in files[1:]:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    if content_type == 'file':
                        os.remove(file_path)
                        typer.echo(f"Deleted duplicate file: {file_path}")
                    else:
                        if content_type == 'paragraph':
                            content = content.replace(data['original'], "[[deleted]]")
                        elif content_type == 'sentence':
                            content = content.replace(data['original'], "[[deleted]]")
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        typer.echo(f"Updated file with deleted {content_type}: {file_path}")

    if check_files:
        delete_duplicates(file_index, 'file')

    if check_paragraphs:
        delete_duplicates(paragraph_index, 'paragraph')

    if check_sentences:
        delete_duplicates(sentence_index, 'sentence')

    typer.echo("Cleanup completed, duplicates removed.")

if __name__ == "__main__":
    app()
