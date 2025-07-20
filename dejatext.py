import os
import re
import csv
import hashlib
import string
import typer
from difflib import SequenceMatcher

app = typer.Typer()

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower()
            for text in re.split('([0-9]+)', str(s))]

def remove_yaml_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from the beginning of text content."""
    # Pattern to match YAML frontmatter: --- at start, followed by content, ending with ---
    # Only match if there's actual YAML content between the --- markers (not just a single line)
    # Handle multiple consecutive YAML blocks
    frontmatter_pattern = r'^---\s*\n(.+?\n)+---\s*\n'
    
    # Keep removing YAML frontmatter blocks until none are left
    while True:
        match = re.match(frontmatter_pattern, content, re.DOTALL)
        if match:
            # Remove the frontmatter and continue
            content = content[match.end():]
        else:
            break
    
    return content

def hash_content(content: str) -> str:
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def split_paragraphs(content: str) -> list:
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    return paragraphs

def split_sentences(content: str) -> list:
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', content)
    sentences = [s.strip() for s in sentences if s.strip()]
    return sentences

def generate_phrases(sentence_words: list, min_len: int, max_len: int) -> list:
    phrases = []
    n = len(sentence_words)
    for length in range(min_len, min(max_len, n) + 1):
        for i in range(n - length + 1):
            phrase = ' '.join(sentence_words[i:i+length])
            phrases.append(phrase)
    return phrases

def normalize_text_for_indexing(text: str) -> str:
    return text.lower().translate(str.maketrans('', '', string.punctuation)).strip()

def write_markdown_report(filepath: str, title: str, data: dict, is_similarity: bool = False, no_file_links: bool = False):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# {title}\n\n")
        distinct_count = len(data)
        f.write(f"**Total Distinct Entries:** {distinct_count}\n\n")

        for content, info in sorted(data.items(), key=lambda x: (-len(x[1]['files']), x[0])):
            preview = info['original'][:500] + "..." if len(info['original']) > 500 else info['original']
            total_occurrences = info.get('total_occurrences', 0)
            file_count = len(info['files'])
            similarity = info['similarity']
            f.write(f"- Content preview:\n")
            f.write(f"  ```\n  {preview}\n  ```\n")
            f.write(f"  **Total Occurrences:** {total_occurrences}\n\n")
            f.write(f"  **Number of Files:** {file_count}\n\n")

            if not no_file_links and file_count > 0:
                f.write("  Files:\n")
                for file in sorted(info['files']):
                    f.write(f"  - {file}\n")

            if is_similarity:
                f.write(f"  - **Max Similarity Score**: {similarity}%\n\n")

def maybe_write_markdown_report(filepath: str, title: str, data: dict, is_similarity: bool = False, no_file_links: bool = False):
    if data:
        write_markdown_report(filepath, title, data, is_similarity, no_file_links)

def write_summary_csv(filepath: str, data: list):
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Count', 'Similarity', 'Type', 'Content', 'Total Occurrences', 'Number of Files'])
        data.sort(key=lambda x: (-x[0], -float(str(x[1]).strip('%')), x[2]))
        for row in data:
            writer.writerow(row)

def similarity_score(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio() * 100

@app.command()
def dejatext(
    input_directory: str,
    output_folder: str = "dedup_output",
    check_files: bool = typer.Option(True, "--check-files/--no-check-files"),
    check_sentences: bool = typer.Option(True, "--check-sentences/--no-check-sentences"),
    check_paragraphs: bool = typer.Option(True, "--check-paragraphs/--no-check-paragraphs"),
    check_phrases: bool = typer.Option(True, "--check-phrases/--no-check-phrases"),
    check_words: bool = typer.Option(True, "--check-words/--no-check-words"),
    min_phrase_length: int = typer.Option(2, "--min-phrase-length"),
    max_phrase_length: int = typer.Option(20, "--max-phrase-length"),
    fuzzy: bool = typer.Option(False, "--fuzzy/--no-fuzzy", help="Enable or disable fuzzy comparison (default off)"),
    fuzz_threshold: int = typer.Option(90, "--fuzz-threshold", help="Minimum similarity percentage for fuzzy matches"),
    no_file_links: bool = typer.Option(False, "--no-file-links", help="Disable links to files in generated reports")
):
    if not (check_files or check_sentences or check_paragraphs or check_phrases or check_words):
        typer.echo("Error: At least one type of check must be enabled.")
        raise typer.Exit(1)

    os.makedirs(output_folder, exist_ok=True)

    all_files = []
    for root, _, files in os.walk(input_directory):
        for file in files:
            if file.endswith('.txt') or file.endswith('.md'):
                all_files.append(os.path.join(root, file))
    all_files.sort(key=natural_sort_key)

    all_contents = {}
    all_sentences = {}
    all_paragraphs = {}
    all_phrases = {}
    all_words = {}

    # Index structures:
    # Each index key = norm, value = {'files':{file:count}, 'original': original_content}
    sentence_index = {}
    paragraph_index = {}
    phrase_index = {}
    word_index = {}

    def add_to_index(idx, item, file_path):
        norm = normalize_text_for_indexing(item)
        if not norm:
            return
        if norm not in idx:
            idx[norm] = {'files':{}, 'original': item}
        if file_path not in idx[norm]['files']:
            idx[norm]['files'][file_path] = 0
        idx[norm]['files'][file_path] += 1

    # Process files
    for file_path in all_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Remove YAML frontmatter before processing
        content = remove_yaml_frontmatter(content)

        all_contents[file_path] = content
        if not content.strip():
            all_sentences[file_path] = []
            all_paragraphs[file_path] = []
            all_phrases[file_path] = []
            all_words[file_path] = []
            continue

        paragraphs = split_paragraphs(content)
        valid_paragraphs = [p for p in paragraphs if len(p.split()) > 20] if check_paragraphs else paragraphs
        sentences = split_sentences(content)

        words = []
        phrases = []
        if check_phrases or check_words:
            for s in sentences:
                sentence_words = s.split()
                words.extend(sentence_words)
                if check_phrases:
                    phrases.extend(generate_phrases(sentence_words, min_phrase_length, max_phrase_length))
        else:
            words = [w for s in sentences for w in s.split()]

        all_sentences[file_path] = sentences
        all_paragraphs[file_path] = valid_paragraphs
        all_phrases[file_path] = phrases
        all_words[file_path] = words

        # Index building
        if check_sentences:
            for s in sentences:
                add_to_index(sentence_index, s, file_path)

        if check_paragraphs:
            for p in valid_paragraphs:
                add_to_index(paragraph_index, p, file_path)

        if check_phrases:
            for ph in phrases:
                add_to_index(phrase_index, ph, file_path)

        if check_words:
            normalized_words = [w.lower().strip(string.punctuation) for w in words if w.strip(string.punctuation) and len(w.strip(string.punctuation)) > 1]
            for w_ in normalized_words:
                if w_ not in word_index:
                    word_index[w_] = {'files':{}, 'original': w_}
                if file_path not in word_index[w_]['files']:
                    word_index[w_]['files'][file_path] = 0
                word_index[w_]['files'][file_path] += 1

    # Now we store duplicates and similarities in a new structure:
    # report[content] = {
    #    'original': original_content,
    #    'files': set_of_files,
    #    'similarity': max similarity found,
    #    'total_occurrences': sum of occurrences in all files
    # }

    duplicates = {'files': {}, 'sentences': {}, 'paragraphs': {}, 'phrases': {}, 'words': {}}
    similarities = {'files': {}, 'sentences': {}, 'paragraphs': {}, 'phrases': {}, 'words': {}}

    def add_to_report(report, content, files, similarity=100, total_occurrences=0):
        if content not in report:
            report[content] = {
                'original': content,
                'files': set(),
                'similarity': similarity,
                'total_occurrences': total_occurrences
            }
        else:
            report[content]['similarity'] = max(report[content]['similarity'], similarity)
        report[content]['files'].update(files)

    def add_index_based_report(report, original, file_counts, similarity=100):
        # Calculate total occurrences and file list
        files = file_counts.keys()
        total_occurrences = sum(file_counts.values())
        add_to_report(report, original, files, similarity, total_occurrences)

    def similarity_check_and_add(content_a, content_b, f1, f2, duplicates_dict, similarities_dict):
        if not fuzzy:
            # Exact match only
            if content_a == content_b:
                add_to_report(duplicates_dict, content_a, [f1, f2], 100)
        else:
            score = similarity_score(content_a, content_b)
            if score == 100:
                add_to_report(duplicates_dict, content_a, [f1, f2], 100)
            elif score >= fuzz_threshold:
                add_to_report(similarities_dict, content_a, [f1, f2], int(score))

    # Check files duplicates (direct content comparison)
    if check_files:
        file_list = list(all_contents.keys())
        for i in range(len(file_list)):
            for j in range(i+1, len(file_list)):
                f1, f2 = file_list[i], file_list[j]
                content_a = all_contents[f1]
                content_b = all_contents[f2]
                similarity_check_and_add(content_a, content_b, f1, f2, duplicates['files'], similarities['files'])

    def check_index_duplicates(index, duplicates_dict, similarities_dict):
        # First handle exact duplicates
        items = list(index.items())  # (norm, {files:{}, original:})
        # Exact duplicates: if appears in multiple files or multiple times in one file
        for norm, data in items:
            file_counts = data['files']
            original = data['original']
            if len(file_counts) > 1 or any(count > 1 for count in file_counts.values()):
                # It's a duplicate by definition
                add_index_based_report(duplicates_dict, original, file_counts, 100)

        # Fuzzy checks if enabled
        if fuzzy:
            # Skip if too large
            if len(items) > 1000:
                print("Skipping fuzzy checks due to large number of items (>1000).")
                return

            for i in range(len(items)):
                for j in range(i+1, len(items)):
                    norm_a, data_a = items[i]
                    norm_b, data_b = items[j]
                    if norm_a == norm_b:
                        continue
                    score = similarity_score(data_a['original'], data_b['original'])
                    if score >= fuzz_threshold:
                        # Merge files from both
                        merged_files = list(data_a['files'].keys()) + list(data_b['files'].keys())
                        total_occurrences = sum(data_a['files'].values()) + sum(data_b['files'].values())
                        add_to_report(similarities_dict, data_a['original'], merged_files, int(score), total_occurrences)

    if check_sentences:
        check_index_duplicates(sentence_index, duplicates['sentences'], similarities['sentences'])

    if check_paragraphs:
        check_index_duplicates(paragraph_index, duplicates['paragraphs'], similarities['paragraphs'])

    if check_phrases:
        check_index_duplicates(phrase_index, duplicates['phrases'], similarities['phrases'])

    # Check words
    if check_words:
        word_items = list(word_index.items()) # (norm, {files:{}, 'original':w_})
        # Exact duplicates
        for norm, data in word_items:
            file_counts = data['files']
            original = data['original']
            if len(file_counts) > 1 or any(count > 1 for count in file_counts.values()):
                add_index_based_report(duplicates['words'], original, file_counts, 100)

        # Fuzzy
        if fuzzy and len(word_items) <= 1000:
            for i in range(len(word_items)):
                for j in range(i+1, len(word_items)):
                    w1, data1 = word_items[i]
                    w2, data2 = word_items[j]
                    if w1 == w2:
                        continue
                    score = similarity_score(data1['original'], data2['original'])
                    if score >= fuzz_threshold:
                        merged_files = list(data1['files'].keys()) + list(data2['files'].keys())
                        total_occurrences = sum(data1['files'].values()) + sum(data2['files'].values())
                        add_to_report(similarities['words'], data1['original'], merged_files, int(score), total_occurrences)
        elif fuzzy and len(word_items) > 1000:
            print("Skipping fuzzy checks for words due to large number of items (>1000).")

    # Now we must also fix the files duplicates since they currently show pairs
    # We currently store file content in duplicates['files'] and similarities['files'] directly.
    # We must compute total occurrences (which for files is just "1 occurrence" per file)
    # The number of occurrences is just the number of files. Similarity is stored.
    # Content can be large, but we will trust the code as is.

    def finalize_file_entries(data_dict):
        for content, info in data_dict.items():
            # total_occurrences = number of files (as each file is one occurrence)
            info['total_occurrences'] = len(info['files'])
    finalize_file_entries(duplicates['files'])
    finalize_file_entries(similarities['files'])

    # Generate reports
    if check_files:
        maybe_write_markdown_report(os.path.join(output_folder, 'duplicated_files.md'), "Duplicated Files", duplicates['files'], no_file_links=no_file_links)
        maybe_write_markdown_report(os.path.join(output_folder, 'similar_files.md'), "Similar Files", similarities['files'], is_similarity=True, no_file_links=no_file_links)

    if check_sentences:
        dup_sents = duplicates['sentences']
        sim_sents = similarities['sentences']
        maybe_write_markdown_report(os.path.join(output_folder, 'duplicated_sentences.md'), "Duplicated Sentences", dup_sents, no_file_links=no_file_links)
        maybe_write_markdown_report(os.path.join(output_folder, 'similar_sentences.md'), "Similar Sentences", sim_sents, is_similarity=True, no_file_links=no_file_links)

    if check_paragraphs:
        dup_paras = duplicates['paragraphs']
        sim_paras = similarities['paragraphs']
        maybe_write_markdown_report(os.path.join(output_folder, 'duplicated_paragraphs.md'), "Duplicated Paragraphs", dup_paras, no_file_links=no_file_links)
        maybe_write_markdown_report(os.path.join(output_folder, 'similar_paragraphs.md'), "Similar Paragraphs", sim_paras, is_similarity=True, no_file_links=no_file_links)

    if check_phrases:
        dup_phrases = duplicates['phrases']
        sim_phrases = similarities['phrases']
        os.makedirs(os.path.join(output_folder, 'duplicated_phrases'), exist_ok=True)
        # Separate reports by phrase length
        for length in range(min_phrase_length, max_phrase_length + 1):
            subset_dup = {p: v for p, v in dup_phrases.items() if len(v['original'].split()) == length}
            maybe_write_markdown_report(
                os.path.join(output_folder, 'duplicated_phrases', f'duplicated_phrases_{length}_words.md'),
                f"Duplicated Phrases ({length} words)", subset_dup, no_file_links=no_file_links
            )
        maybe_write_markdown_report(
            os.path.join(output_folder, 'similar_phrases.md'),
            "Similar Phrases", sim_phrases, is_similarity=True, no_file_links=no_file_links
        )

    if check_words:
        dup_words_filtered = duplicates['words']
        sim_words_filtered = similarities['words']
        maybe_write_markdown_report(os.path.join(output_folder, 'duplicated_words.md'), "Duplicated Words", dup_words_filtered, no_file_links=no_file_links)
        maybe_write_markdown_report(os.path.join(output_folder, 'similar_words.md'), "Similar Words", sim_words_filtered, is_similarity=True, no_file_links=no_file_links)

    # Summary CSV
    summary_data = []

    def collect_summary(data, dtype):
        # data is {content: {'original':..., 'files':set(), 'similarity':..., 'total_occurrences':...}}
        rows = []
        for content, info in data.items():
            unique_files = len(info['files'])
            sim = info['similarity']
            clean_content = info['original']
            if len(clean_content) > 100:
                clean_content = clean_content[:100] + "..."
            total_occ = info['total_occurrences']
            rows.append([unique_files, f"{sim}%", dtype, clean_content, total_occ, unique_files])
        return rows

    if check_files:
        summary_data.extend(collect_summary(duplicates['files'], 'File'))
        summary_data.extend(collect_summary(similarities['files'], 'File'))
    if check_sentences:
        summary_data.extend(collect_summary(duplicates['sentences'], 'Sentence'))
        summary_data.extend(collect_summary(similarities['sentences'], 'Sentence'))
    if check_paragraphs:
        summary_data.extend(collect_summary(duplicates['paragraphs'], 'Paragraph'))
        summary_data.extend(collect_summary(similarities['paragraphs'], 'Paragraph'))
    if check_phrases:
        summary_data.extend(collect_summary(duplicates['phrases'], 'Phrase'))
        summary_data.extend(collect_summary(similarities['phrases'], 'Phrase'))
    if check_words:
        summary_data.extend(collect_summary(duplicates['words'], 'Word'))
        summary_data.extend(collect_summary(similarities['words'], 'Word'))

    write_summary_csv(os.path.join(output_folder, 'summary_report.csv'), summary_data)

    typer.echo("Deduplication and similarity analysis completed, reports generated.")

if __name__ == "__main__":
    app()