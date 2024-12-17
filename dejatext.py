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

        # Print how many distinct duplicated entries are found
        distinct_count = len(data)
        f.write(f"**Total Distinct Duplicated Entries:** {distinct_count}\n\n")

        for content, locations in sorted(data.items(), key=lambda x: (-len(x[1]), x[0])):
            preview = content[:500] + "..." if len(content) > 500 else content
            files = sorted(set([loc[0] for loc in locations] + [loc[1] for loc in locations]))
            f.write(f"- Content preview:\n")
            f.write(f"  ```\n  {preview}\n  ```\n")

            if not no_file_links:
                f.write("  Files:\n")
                for file in files:
                    f.write(f"  - {file}\n")

            if is_similarity:
                similarities = sorted({loc[2] for loc in locations}, reverse=True)
                for sim in similarities:
                    f.write(f"  - **Similarity Score**: {sim}%\n")
            f.write("\n")

def maybe_write_markdown_report(filepath: str, title: str, data: dict, is_similarity: bool = False, no_file_links: bool = False):
    if data:
        write_markdown_report(filepath, title, data, is_similarity, no_file_links)

def write_summary_csv(filepath: str, data: list):
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Count', 'Similarity', 'Type', 'Content'])
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

    sentence_index = {}
    paragraph_index = {}
    phrase_index = {}
    word_index = {}

    def add_to_index(idx, item, file_path):
        norm = normalize_text_for_indexing(item)
        if not norm:
            return
        if norm not in idx:
            idx[norm] = {}
        if file_path not in idx[norm]:
            idx[norm][file_path] = 0
        idx[norm][file_path] += 1

    # Process files
    for file_path in all_files:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

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
            for w in set(normalized_words):
                if w not in word_index:
                    word_index[w] = {}
                if file_path not in word_index[w]:
                    word_index[w][file_path] = 0
                word_index[w][file_path] += words.count(w)

    duplicates = {'files': {}, 'sentences': {}, 'paragraphs': {}, 'phrases': {}, 'words': {}}
    similarities = {'files': {}, 'sentences': {}, 'paragraphs': {}, 'phrases': {}, 'words': {}}

    def add_to_report(report, content, file1, file2, similarity=100):
        if content not in report:
            report[content] = set()
        report[content].add((file1, file2, similarity))

    def check_fuzzy_and_add(content_a, content_b, file1, file2, duplicates_dict, similarities_dict):
        if not fuzzy:
            if content_a == content_b:
                add_to_report(duplicates_dict, content_a, file1, file2, 100)
        else:
            score = similarity_score(content_a, content_b)
            if score == 100:
                add_to_report(duplicates_dict, content_a, file1, file2, 100)
            elif score >= fuzz_threshold:
                add_to_report(similarities_dict, content_a, file1, file2, int(score))

    # Check files duplicates
    if check_files:
        file_list = list(all_contents.keys())
        for i in range(len(file_list)):
            for j in range(i, len(file_list)):
                f1, f2 = file_list[i], file_list[j]
                if f1 == f2:
                    continue
                content_a = all_contents[f1]
                content_b = all_contents[f2]
                check_fuzzy_and_add(content_a, content_b, f1, f2, duplicates['files'], similarities['files'])

    def index_to_list(index):
        return [(norm, files_counts) for norm, files_counts in index.items()]

    def check_index_duplicates(index, duplicates_dict, similarities_dict):
        items = index_to_list(index)
        for i in range(len(items)):
            for j in range(i, len(items)):
                norm_a, files_a = items[i]
                norm_b, files_b = items[j]
                if i == j:
                    # same normalized content in multiple files or counts
                    file_list = list(files_a.keys())
                    for fi in range(len(file_list)):
                        for fj in range(fi, len(file_list)):
                            f1, f2 = file_list[fi], file_list[fj]
                            if f1 != f2 or files_a[f1] > 1:
                                add_to_report(duplicates_dict, norm_a, f1, f2, 100)
                else:
                    score = similarity_score(norm_a, norm_b) if fuzzy else (100 if norm_a == norm_b else 0)
                    if score == 100:
                        file_list_a = list(files_a.keys())
                        file_list_b = list(files_b.keys())
                        for fa in file_list_a:
                            for fb in file_list_b:
                                if fa != fb or (fa == fb and (files_a[fa] > 1 or files_b[fb] > 1)):
                                    add_to_report(duplicates_dict, norm_a, fa, fb, 100)
                    elif fuzzy and score >= fuzz_threshold:
                        file_list_a = list(files_a.keys())
                        file_list_b = list(files_b.keys())
                        for fa in file_list_a:
                            for fb in file_list_b:
                                add_to_report(similarities_dict, norm_a, fa, fb, int(score))

    if check_sentences:
        check_index_duplicates(sentence_index, duplicates['sentences'], similarities['sentences'])

    if check_paragraphs:
        check_index_duplicates(paragraph_index, duplicates['paragraphs'], similarities['paragraphs'])

    if check_phrases:
        check_index_duplicates(phrase_index, duplicates['phrases'], similarities['phrases'])

    if check_words:
        items = [(w, file_counts) for w, file_counts in word_index.items()]
        for i in range(len(items)):
            for j in range(i, len(items)):
                w1, fc1 = items[i]
                w2, fc2 = items[j]
                if i == j:
                    # same word multiple files
                    file_list = list(fc1.keys())
                    total_occurrences = sum(fc1.values())
                    for fi in range(len(file_list)):
                        for fj in range(fi, len(file_list)):
                            f1, f2 = file_list[fi], file_list[fj]
                            if f1 != f2 or fc1[f1] > 1:
                                # Keep the occurrences info for words
                                add_to_report(duplicates['words'], f"{w1} ({total_occurrences} occurrences)", f1, f2, 100)
                else:
                    score = similarity_score(w1, w2) if fuzzy else (100 if w1 == w2 else 0)
                    if score == 100:
                        file_list_1 = list(fc1.keys())
                        file_list_2 = list(fc2.keys())
                        for fa in file_list_1:
                            for fb in file_list_2:
                                if fa != fb or fc1[fa] > 1 or fc2[fb] > 1:
                                    # Keep the "multiple" wording for words that appear in multiple files
                                    add_to_report(duplicates['words'], f"{w1} (multiple)", fa, fb, 100)
                    elif fuzzy and score >= fuzz_threshold:
                        file_list_1 = list(fc1.keys())
                        file_list_2 = list(fc2.keys())
                        for fa in file_list_1:
                            for fb in file_list_2:
                                add_to_report(similarities['words'], w1, fa, fb, int(score))

    # Generate reports
    if check_files:
        maybe_write_markdown_report(os.path.join(output_folder, 'duplicated_files.md'), "Duplicated Files", duplicates['files'], no_file_links=no_file_links)
        maybe_write_markdown_report(os.path.join(output_folder, 'similar_files.md'), "Similar Files", similarities['files'], is_similarity=True, no_file_links=no_file_links)

    if check_sentences:
        dup_sents = {k: v for k, v in duplicates['sentences'].items() if len(v) > 1}
        sim_sents = {k: v for k, v in similarities['sentences'].items() if len(v) > 1}
        maybe_write_markdown_report(os.path.join(output_folder, 'duplicated_sentences.md'), "Duplicated Sentences", dup_sents, no_file_links=no_file_links)
        maybe_write_markdown_report(os.path.join(output_folder, 'similar_sentences.md'), "Similar Sentences", sim_sents, is_similarity=True, no_file_links=no_file_links)

    if check_paragraphs:
        dup_paras = {k: v for k, v in duplicates['paragraphs'].items() if len(v) > 1}
        sim_paras = {k: v for k, v in similarities['paragraphs'].items() if len(v) > 1}
        maybe_write_markdown_report(os.path.join(output_folder, 'duplicated_paragraphs.md'), "Duplicated Paragraphs", dup_paras, no_file_links=no_file_links)
        maybe_write_markdown_report(os.path.join(output_folder, 'similar_paragraphs.md'), "Similar Paragraphs", sim_paras, is_similarity=True, no_file_links=no_file_links)

    if check_phrases:
        dup_phrases = {p: locs for p, locs in duplicates['phrases'].items() if len(locs) > 1}
        sim_phrases = {p: locs for p, locs in similarities['phrases'].items() if len(locs) > 1}
        os.makedirs(os.path.join(output_folder, 'duplicated_phrases'), exist_ok=True)
        # Separate reports by phrase length
        for length in range(min_phrase_length, max_phrase_length + 1):
            subset_dup = {p: v for p, v in dup_phrases.items() if len(p.split()) == length}
            maybe_write_markdown_report(
                os.path.join(output_folder, 'duplicated_phrases', f'duplicated_phrases_{length}_words.md'),
                f"Duplicated Phrases ({length} words)", subset_dup, no_file_links=no_file_links
            )
        maybe_write_markdown_report(
            os.path.join(output_folder, 'similar_phrases.md'),
            "Similar Phrases", sim_phrases, is_similarity=True, no_file_links=no_file_links
        )

    if check_words:
        dup_words_filtered = {k: v for k, v in duplicates['words'].items() if len(v) > 1}
        sim_words_filtered = {k: v for k, v in similarities['words'].items() if len(v) > 1}
        maybe_write_markdown_report(os.path.join(output_folder, 'duplicated_words.md'), "Duplicated Words", dup_words_filtered, no_file_links=no_file_links)
        maybe_write_markdown_report(os.path.join(output_folder, 'similar_words.md'), "Similar Words", sim_words_filtered, is_similarity=True, no_file_links=no_file_links)

    # Summary CSV
    summary_data = []

    def collect_summary(data, dtype):
        seen = set()
        rows = []
        for content, locs in data.items():
            if content not in seen:
                seen.add(content)
                unique_files = len(set([l[0] for l in locs] + [l[1] for l in locs]))
                sim = list(locs)[0][2]
                clean_content = content
                if len(clean_content) > 100:
                    clean_content = clean_content[:100] + "..."
                rows.append([unique_files, f"{sim}%", dtype, clean_content])
        return rows

    if check_files:
        summary_data.extend(collect_summary(duplicates['files'], 'File'))
        summary_data.extend(collect_summary(similarities['files'], 'File'))
    if check_sentences:
        dup_sents_filtered = {k: v for k, v in duplicates['sentences'].items() if len(v) > 1}
        sim_sents_filtered = {k: v for k, v in similarities['sentences'].items() if len(v) > 1}
        summary_data.extend(collect_summary(dup_sents_filtered, 'Sentence'))
        summary_data.extend(collect_summary(sim_sents_filtered, 'Sentence'))
    if check_paragraphs:
        dup_paras_filtered = {k: v for k, v in duplicates['paragraphs'].items() if len(v) > 1}
        sim_paras_filtered = {k: v for k, v in similarities['paragraphs'].items() if len(v) > 1}
        summary_data.extend(collect_summary(dup_paras_filtered, 'Paragraph'))
        summary_data.extend(collect_summary(sim_paras_filtered, 'Paragraph'))
    if check_phrases:
        dup_phrases_filtered = {k: v for k, v in duplicates['phrases'].items() if len(v) > 1}
        sim_phrases_filtered = {k: v for k, v in similarities['phrases'].items() if len(v) > 1}
        summary_data.extend(collect_summary(dup_phrases_filtered, 'Phrase'))
        summary_data.extend(collect_summary(sim_phrases_filtered, 'Phrase'))
    if check_words:
        dup_words_filtered = {k: v for k, v in duplicates['words'].items() if len(v) > 1}
        sim_words_filtered = {k: v for k, v in similarities['words'].items() if len(v) > 1}
        summary_data.extend(collect_summary(dup_words_filtered, 'Word'))
        summary_data.extend(collect_summary(sim_words_filtered, 'Word'))

    write_summary_csv(os.path.join(output_folder, 'summary_report.csv'), summary_data)

    typer.echo("Deduplication and similarity analysis completed, reports generated.")

if __name__ == "__main__":
    app()