import os
import re
import typer
from collections import Counter, defaultdict
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import Manager, Queue
import csv
import string
import time
import hashlib

app = typer.Typer()

def natural_sort_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', str(s))]

def process_file(file_path, min_phrase_length, max_phrase_length):
    with open(file_path, 'r') as file:
        content = file.read()
    if not content.strip():
        return [], [], [], [], content
        
    # More efficient paragraph splitting
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
    
    # Only process paragraphs that meet minimum length
    paragraphs = [p for p in paragraphs if len(p.split()) > 20]
    
    # More efficient sentence splitting
    sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', content)
    sentences = [s.strip() for s in sentences if s.strip()]

    phrases = []
    words = []
    
    # Modified phrase generation logic with less aggressive normalization
    for sentence in sentences:
        # Preserve case and punctuation in words, just split on whitespace
        sentence_words = sentence.split()
        words.extend(sentence_words)
        
        for length in range(min_phrase_length, min(max_phrase_length + 1, len(sentence_words) + 1)):
            for i in range(len(sentence_words) - length + 1):
                # Keep original form for exact matches, let fuzzy matching handle variations
                phrase = ' '.join(sentence_words[i:i + length])
                phrases.append(phrase)
    
    return sentences, paragraphs, phrases, words, content

def find_duplicates_and_similarities(file_chunk, all_sentences, all_paragraphs, all_phrases, all_words, all_contents, progress_queue, start_index, check_files, check_sentences, check_paragraphs, check_phrases, check_words, min_phrase_length, max_phrase_length, phrase_index, sentence_index, paragraph_index, word_index):
    duplicates = {'files': {}, 'sentences': {}, 'paragraphs': {}, 'phrases': {}, 'words': {}}
    similarities = {'files': {}, 'sentences': {}, 'paragraphs': {}, 'phrases': {}, 'words': {}}
    
    def add_to_report(report, content, file1, file2, similarity):
        if similarity == 100:
            if content not in report:
                report[content] = set()
            report[content].add((file1, file2, 100))
        else:
            if content not in report:
                report[content] = set()
            report[content].add((file1, file2, similarity))
    
    print(f"Starting processing for file chunk starting at index {start_index}")  # Debugging info

    for file_index, file_path in enumerate(file_chunk, start=start_index):
        print(f"Processing file {file_path}")  # Debugging info
        if check_files:
            progress_queue.put(('files', file_index + 1, len(file_chunk)))
        
        if check_files:
            seen_files = set()
            for other_file_path, other_content in all_contents.items():
                if file_path != other_file_path and all_contents[file_path] and other_content:
                    if hash_content(all_contents[file_path]) == hash_content(other_content):
                        similarity = 100
                    else:
                        similarity = 0
                    print(f"File similarity between {file_path} and {other_file_path}: {similarity}%")  # Debug
                    
                    if similarity == 100:
                        add_to_report(duplicates['files'], all_contents[file_path], file_path, other_file_path, 100)

        if check_paragraphs:
            seen_paragraphs = set()
            for file_path in all_paragraphs:
                # Filter paragraphs by length first
                valid_paragraphs = [(i, p) for i, p in enumerate(all_paragraphs[file_path]) if len(p.split()) > 20]
                
                for i, paragraph in valid_paragraphs:
                    if paragraph in seen_paragraphs:
                        continue
                        
                    seen_paragraphs.add(paragraph)
                    normalized_para = paragraph.lower().strip()
                    
                    # Compare with other files
                    for other_file_path, other_paragraphs in all_paragraphs.items():
                        if file_path >= other_file_path:  # Skip if we've already compared these files
                            continue
                            
                        # Filter other paragraphs by length
                        other_valid_paragraphs = [p for p in other_paragraphs if len(p.split()) > 20]
                        
                        for other_para in other_valid_paragraphs:
                            if normalized_para == other_para.lower().strip():
                                add_to_report(duplicates['paragraphs'], paragraph, file_path, other_file_path, 100)
                                
                    progress_queue.put(('paragraphs', i + 1, len(valid_paragraphs)))

        if check_phrases:
            seen_phrases = set()
            for i, phrase in enumerate(all_phrases[file_path]):
                phrase_length = len(phrase.split())
                if min_phrase_length <= phrase_length <= max_phrase_length:
                    # Compare with phrases in other files
                    for other_file_path in all_phrases:
                        if file_path != other_file_path:
                            for other_phrase in all_phrases[other_file_path]:
                                other_phrase_length = len(other_phrase.split())
                                if phrase_length == other_phrase_length:  # Only compare phrases of same length
                                    similarity = 100 if phrase == other_phrase else 0
                                    if similarity == 100:
                                        print(f"Phrase similarity: '{phrase}' and '{other_phrase}': {similarity}%")  # Debug
                                        add_to_report(duplicates['phrases'], phrase, file_path, other_file_path, 100)
                
                if i % 100 == 0 and i != 0:  # Update progress periodically
                    progress_queue.put(('phrases', i + 1, len(all_phrases[file_path])))

        print(f"Finished processing phrases for file {file_index + 1}/{len(file_chunk)}")  # Debugging info

        if check_words:
            print("Checking for duplicate words")  # Debugging info
            for word, total_count in word_index.items():
                if total_count > 1:
                    word_files = [file_path for file_path in all_words if word in (w.lower() for w in all_words[file_path])]
                    file_pairs = [(f1, f2) for i, f1 in enumerate(word_files) for f2 in word_files[i:] if f1 != f2 or (f1 == f2 and all_words[f1].count(word) > 1)]
                    for file1, file2 in file_pairs:
                        add_to_report(duplicates['words'], word, file1, file2, 100)
            progress_queue.put(('words', len(word_index), len(word_index)))

    if check_sentences:
        print("Checking for duplicate sentences")
        for file_path in all_sentences:
            for sentence in all_sentences[file_path]:
                for other_file_path in all_sentences:
                    if file_path != other_file_path:
                        for other_sentence in all_sentences[other_file_path]:
                            similarity = 100 if sentence == other_sentence else 0
                            print(f"Sentence similarity: {similarity}%\n'{sentence}'\n'{other_sentence}'")  # Debug
                            
                            if similarity == 100:
                                add_to_report(duplicates['sentences'], sentence, file_path, other_file_path, 100)

    if check_paragraphs:
        print("Checking for duplicate paragraphs")
        for i, paragraph in enumerate(all_paragraphs[file_path]):
            if len(paragraph.split()) > 20:
                for other_file_path in all_paragraphs:
                    if file_path != other_file_path:
                        for other_paragraph in all_paragraphs[other_file_path]:
                            if len(other_paragraph.split()) > 20:
                                similarity = 100 if paragraph == other_paragraph else 0
                                print(f"Paragraph similarity: {similarity}%")  # Debug
                                
                                if similarity == 100:
                                    add_to_report(duplicates['paragraphs'], paragraph, file_path, other_file_path, 100)

    if check_phrases:
        print("Checking for duplicate phrases")
        for i, phrase in enumerate(all_phrases[file_path]):
            phrase_length = len(phrase.split())
            if min_phrase_length <= phrase_length <= max_phrase_length:
                for other_file_path in all_phrases:
                    if file_path != other_file_path:
                        for other_phrase in all_phrases[other_file_path]:
                            if len(other_phrase.split()) == phrase_length:
                                similarity = 100 if phrase == other_phrase else 0
                                if similarity == 100:
                                    print(f"Phrase similarity: '{phrase}' and '{other_phrase}': {similarity}%")  # Debug
                                    add_to_report(duplicates['phrases'], phrase, file_path, other_file_path, 100)

    return duplicates, similarities

def generate_reports(duplicates, similarities, output_folder, check_files, check_sentences, check_paragraphs, check_phrases, check_words, min_phrase_length, max_phrase_length):
    os.makedirs(output_folder, exist_ok=True)
    
    print("Starting report generation...")  # Debugging info

    if check_files:
        file_report_path = os.path.join(output_folder, 'duplicated_files.md')
        print(f"Writing duplicated files report to {file_report_path}")  # Debugging info
        write_report(file_report_path, "Duplicated Files", duplicates['files'])
        similar_file_report_path = os.path.join(output_folder, 'similar_files.md')
        print(f"Writing similar files report to {similar_file_report_path}")  # Debugging info
        write_report(similar_file_report_path, "Similar Files", similarities['files'], is_similarity=True)
    
    if check_sentences:
        sentence_report_path = os.path.join(output_folder, 'duplicated_sentences.md')
        print(f"Writing duplicated sentences report to {sentence_report_path}")  # Debugging info
        write_report(sentence_report_path, "Duplicated Sentences", {k: v for k, v in duplicates['sentences'].items() if len(v) > 1})
        similar_sentence_report_path = os.path.join(output_folder, 'similar_sentences.md')
        print(f"Writing similar sentences report to {similar_sentence_report_path}")  # Debugging info
        write_report(similar_sentence_report_path, "Similar Sentences", {k: v for k, v in similarities['sentences'].items() if len(v) > 1}, is_similarity=True)
    
    if check_paragraphs:
        paragraph_report_path = os.path.join(output_folder, 'duplicated_paragraphs.md')
        print(f"Writing duplicated paragraphs report to {paragraph_report_path}")  # Debugging info
        write_report(paragraph_report_path, "Duplicated Paragraphs", {k: v for k, v in duplicates['paragraphs'].items() if len(v) > 1})
        similar_paragraph_report_path = os.path.join(output_folder, 'similar_paragraphs.md')
        print(f"Writing similar paragraphs report to {similar_paragraph_report_path}")  # Debugging info
        write_report(similar_paragraph_report_path, "Similar Paragraphs", {k: v for k, v in similarities['paragraphs'].items() if len(v) > 1}, is_similarity=True)
    
    if check_phrases:
        phrase_report_folder = os.path.join(output_folder, 'duplicated_phrases')
        os.makedirs(phrase_report_folder, exist_ok=True)
        for length in range(max_phrase_length, min_phrase_length - 1, -1):
            phrase_report_path = os.path.join(phrase_report_folder, f'duplicated_phrases_{length}_words.md')
            print(f"Writing duplicated phrases report ({length} words) to {phrase_report_path}")  # Debugging info
            write_report(phrase_report_path, f"Duplicated Phrases ({length} words)", {phrase: locations for phrase, locations in duplicates['phrases'].items() if len(locations) > 1 and len(phrase.split()) == length})
    
    if check_words:
        word_report_path = os.path.join(output_folder, 'duplicated_words.md')
        print(f"Writing duplicated words report to {word_report_path}")  # Debugging info
        # Fix: Change how we format the word duplicates for the report
        write_report(word_report_path, "Duplicated Words", {k: v for k, v in duplicates['words'].items()})

    summary_report_path = os.path.join(output_folder, 'summary_report.csv')
    print(f"Writing summary report to {summary_report_path}")  # Debugging info
    with open(summary_report_path, 'w', newline='') as summary_report:
        writer = csv.writer(summary_report)
        writer.writerow(['Count', 'Similarity', 'Type', 'Content'])
        
        def get_summary_data(data, data_type):
            summary_data = []
            seen_content = set()
            for content, locations in data.items():
                if content not in seen_content:
                    seen_content.add(content)
                    unique_files = len(set(loc[0] for loc in locations) | set(loc[1] for loc in locations))
                    similarity = str(list(locations)[0][2]) if list(locations)[0][2] != 100 else '100%'
                    
                    # Clean up content by removing occurrence counts
                    if data_type == 'Word':
                        # Extract just the word before the parentheses
                        clean_content = content.split(' (')[0]
                    else:
                        clean_content = content
                        
                    # Truncate long content
                    if len(clean_content) > 100:
                        clean_content = clean_content[:100] + "..."
                        
                    summary_data.append([unique_files, similarity, data_type, clean_content])
            return summary_data
        
        summary_data = (
            (get_summary_data(duplicates['files'], 'File') if check_files else []) +
            (get_summary_data(similarities['files'], 'File') if check_files else []) +
            (get_summary_data({k: v for k, v in duplicates['sentences'].items() if len(v) > 1}, 'Sentence') if check_sentences else []) +
            (get_summary_data({k: v for k, v in similarities['sentences'].items() if len(v) > 1}, 'Sentence') if check_sentences else []) +
            (get_summary_data({k: v for k, v in duplicates['paragraphs'].items() if len(v) > 1}, 'Paragraph') if check_paragraphs else []) +
            (get_summary_data({k: v for k, v in similarities['paragraphs'].items() if len(v) > 1}, 'Paragraph') if check_paragraphs else []) +
            (get_summary_data({phrase: locations for phrase, locations in duplicates['phrases'].items() if len(locations) > 1}, 'Phrase') if check_phrases else []) +
            (get_summary_data({phrase: locations for phrase, locations in similarities['phrases'].items() if len(locations) > 1}, 'Phrase') if check_phrases else []) +
            # Fix word summary data generation
            (get_summary_data({k: v for k, v in duplicates['words'].items() if len(v) > 1}, 'Word') if check_words else []) +
            (get_summary_data({k: v for k, v in similarities['words'].items() if len(v) > 1}, 'Word') if check_words else [])
        )
        
        summary_data.sort(key=lambda x: (-x[0], -float(str(x[1]).strip('%')), x[2]))
        
        for row in summary_data:
            writer.writerow(row)
    
    print("Reports generated successfully.")

def write_report(report_path, title, data, is_similarity=False):
    with open(report_path, 'w') as report:
        report.write(f"# {title}\n\n")
        for content, locations in sorted(data.items(), key=lambda x: (-len(x[1]), x[0])):
            if isinstance(locations, set):
                # Get unique files involved
                files = sorted(set(loc[0] for loc in locations) | set(loc[1] for loc in locations))
                if len(files) > 0:
                    # Changed content formatting to show preview for large content
                    content_preview = content[:500] + "..." if len(content) > 500 else content
                    report.write(f"- Found similarity between files with content preview:\n")
                    report.write(f"  ```\n  {content_preview}\n  ```\n")
                    report.write(f"  Files:\n")
                    for file in files:
                        report.write(f"  - {file}\n")
                    if is_similarity:
                        # Get all unique similarity scores for this content
                        similarities = {loc[2] for loc in locations}
                        for sim in sorted(similarities, reverse=True):
                            report.write(f"  - **Similarity Score**: {sim}%\n")
                    report.write("\n")

@app.command()
def dedup(
    input_directory: str,
    output_folder: str = "dedup_output",
    check_files: bool = typer.Option(True, "--check-files/--no-check-files", help="Check for duplicate files"),
    check_sentences: bool = typer.Option(True, "--check-sentences/--no-check-sentences", help="Check for duplicate sentences"),
    check_paragraphs: bool = typer.Option(True, "--check-paragraphs/--no-check-paragraphs", help="Check for duplicate paragraphs"),
    check_phrases: bool = typer.Option(True, "--check-phrases/--no-check-phrases", help="Check for duplicate phrases"),
    check_words: bool = typer.Option(True, "--check-words/--no-check-words", help="Check for duplicate words"),
    min_phrase_length: int = typer.Option(2, "--min-phrase-length", help="Set the minimum phrase length in words"),
    max_phrase_length: int = typer.Option(20, "--max-phrase-length", help="Set the maximum phrase length in words")
):
    if not (check_files or check_sentences or check_paragraphs or check_phrases or check_words):
        typer.echo("Error: At least one type of check must be enabled.")
        raise typer.Exit()

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    all_files = []
    all_sentences = {}
    all_paragraphs = {}
    all_phrases = {}
    all_words = {}
    all_contents = {}
    total_files = 0
    total_paragraphs = 0
    total_sentences = 0
    total_phrases = 0
    total_words = 0
    
    # Initialize global indexes
    phrase_index = defaultdict(set)
    sentence_index = defaultdict(set)
    paragraph_index = defaultdict(set)
    word_index = defaultdict(lambda: defaultdict(int))

    for root, _, files in os.walk(input_directory):
        for file in files:
            if file.endswith('.txt') or file.endswith('.md'):
                all_files.append(os.path.join(root, file))
    
    all_files.sort(key=natural_sort_key)
    
    for file_path in all_files:
        sentences, paragraphs, phrases, words, content = process_file(file_path, min_phrase_length, max_phrase_length)
        all_sentences[file_path] = sentences
        all_paragraphs[file_path] = paragraphs
        all_phrases[file_path] = phrases
        all_words[file_path] = words
        all_contents[file_path] = content
        total_files += 1

        # Build phrase index using sets for unique phrases per file
        if check_phrases:
            unique_phrases = set(
                phrase.lower().translate(str.maketrans('', '', string.punctuation))
                for phrase in phrases
            )
            for phrase in unique_phrases:
                normalized_phrase = phrase.lower().translate(str.maketrans('', '', string.punctuation))
                phrase_index[normalized_phrase].add(file_path)

        # Build sentence index with normalization
        if check_sentences:
            for sentence in sentences:
                normalized_sentence = sentence.lower().translate(str.maketrans('', '', string.punctuation)).strip()
                if normalized_sentence:
                    sentence_index[normalized_sentence].add(file_path)

        # Build paragraph index with normalization
        if check_paragraphs:
            for paragraph in paragraphs:
                normalized_paragraph = paragraph.lower().translate(str.maketrans('', '', string.punctuation)).strip()
                if normalized_paragraph:
                    paragraph_index[normalized_paragraph].add(file_path)

        # Build word index using Counter - in the file processing loop
        if check_words:
            # Only count words that appear more than once
            # Exclude words that are solely punctuation like '/'
            normalized_words = {
                word.lower().strip(string.punctuation)
                for word in words 
                if word.strip(string.punctuation) and len(word.strip(string.punctuation)) > 1 and word.strip(string.punctuation) != '/'
            }
            # Count unique occurrences per file
            word_counts = Counter(set(normalized_words))
            for word, count in word_counts.items():
                # Safely update word_index
                word_index[word][file_path] += words.count(word)

        if check_paragraphs:
            total_paragraphs += len(paragraphs)
        if check_sentences:
            total_sentences += len(sentences)
        if check_phrases:
            total_phrases += len(phrases)
        if check_words:
            total_words += len(words)
    
    total_steps = total_files + total_paragraphs + total_sentences + total_phrases + total_words
    
    print("Starting deduplication process...")  # Debugging info

    # After building indexes, perform duplicate sentence detection
    duplicates = {'files': {}, 'sentences': {}, 'paragraphs': {}, 'phrases': {}, 'words': {}}
    similarities = {'files': {}, 'sentences': {}, 'paragraphs': {}, 'phrases': {}, 'words': {}}

    if check_sentences:
        print("Checking for duplicate sentences")  # Debugging info
        for sentence, file_data in sentence_index.items():
            file_counts = Counter()
            for file_path in file_data:
                if file_path:
                    file_counts[file_path] += 1
            files_with_sentence = list(file_counts.keys())
            if len(files_with_sentence) > 1 or any(count > 1 for count in file_counts.values()):
                file_list = sorted(files_with_sentence)
                seen_pairs = set()
                for i in range(len(file_list)):
                    for j in range(i, len(file_list)):
                        file1 = file_list[i]
                        file2 = file_list[j]
                        if file1 != file2 or (file1 == file2 and file_counts[file1] > 1):
                            similarity = 100  # Since sentence comparison is always equal here
                            if similarity == 100:
                                pair = (file1, file2)
                                if pair not in seen_pairs:
                                    try:
                                        add_to_report(duplicates['sentences'], sentence, file1, file2, 100)
                                    except KeyError:
                                        # Handle cases where sentence might be '/'
                                        pass
                                    seen_pairs.add(pair)

    if check_paragraphs:
        print("Checking for duplicate paragraphs")  # Debugging info
        for file_path in all_paragraphs:
            for i, paragraph in enumerate(all_paragraphs[file_path]):
                if len(paragraph.split()) > 20:
                    for other_file_path in all_paragraphs:
                        if file_path != other_file_path:
                            for other_paragraph in all_paragraphs[other_file_path]:
                                if len(other_paragraph.split()) > 20:
                                    similarity = 100 if paragraph == other_paragraph else 0
                                    if similarity == 100:
                                        add_to_report(duplicates['paragraphs'], paragraph, file_path, other_file_path, 100)

    if check_phrases:
        print("Checking for duplicate phrases")  # Debugging info
        for file_path, phrases in all_phrases.items():
            for i, phrase in enumerate(phrases):
                phrase_length = len(phrase.split())
                if min_phrase_length <= phrase_length <= max_phrase_length:
                    for other_file_path in all_phrases:
                        if file_path != other_file_path:
                            for other_phrase in all_phrases[other_file_path]:
                                if len(other_phrase.split()) == phrase_length:
                                    similarity = 100 if phrase == other_phrase else 0
                                    if similarity == 100:
                                        add_to_report(duplicates['phrases'], phrase, file_path, other_file_path, 100)
                                    
                if i % 100 == 0 and i != 0:  # Update progress periodically
                    progress_queue.put(('phrases', i + 1, len(all_phrases[file_path])))

    # Perform duplicate paragraph detection
    if check_paragraphs:
        print("Checking for duplicate paragraphs")  # Debugging info
        for paragraph, file_data in paragraph_index.items():
            if len(paragraph.split()) > 20 and len(file_data) > 1:
                file_list = [file_info[0] for file_info in file_data]
                for i in range(len(file_list)):
                    for j in range(i, len(file_list)):
                        file1 = file_list[i]
                        file2 = file_list[j]
                        if file1 != file2 or (file1 == file2 and all_paragraphs[file1].count(paragraph) > 1):
                            similarity = 100 if paragraph == paragraph else 0
                            if similarity == 100:
                                add_to_report(duplicates['paragraphs'], paragraph, file1, file2, similarity)

    # Perform duplicate phrase detection
    if check_phrases:
        print("Checking for duplicate phrases")  # Debugging info
        for phrase, files in phrase_index.items():
            if len(phrase.split()) >= min_phrase_length and len(files) > 1:
                file_list = sorted(files)
                seen_pairs = set()  # Add this line to track seen file pairs
                for i in range(len(file_list)):
                    for j in range(i, len(file_list)):
                        file1, file2 = file_list[i], file_list[j]
                        pair = tuple(sorted((file1, file2)))
                        if pair not in seen_pairs:
                            similarity = 100 if phrase == other_phrase else 0
                            if similarity == 100:
                                if file1 != file2 or (file1 == file2 and all_phrases[file1].count(phrase) > 1):
                                    add_to_report(duplicates['phrases'], phrase, file1, file2, 100)
                                    seen_pairs.add(pair)  # Add this line to mark the pair as seen

    # Perform duplicate word detection - in the main deduplication section
    if check_words:
        print("Checking for duplicate words")  # Debugging info
        for word, file_counts in word_index.items():
            total_occurrences = sum(file_counts.values())
            # Only process words that appear more than once
            if len(file_counts) > 1 or any(count > 1 for count in file_counts.values()):
                file_list = sorted(file_counts.keys())
                seen_pairs = set()
                
                # Compare all file pairs
                for i in range(len(file_list)):
                    for j in range(i, len(file_list)):
                        file1, file2 = file_list[i], file_list[j]
                        pair = tuple(sorted((file1, file2)))
                        
                        # Add to duplicates if:
                        # 1. Different files OR
                        # 2. Same file with multiple occurrences
                        if pair not in seen_pairs and (
                            file1 != file2 or 
                            (file1 == file2 and file_counts[file1] > 1)
                        ):
                            add_to_report(duplicates['words'], f"{word} ({total_occurrences} occurrences)", file1, file2, 100)
                            seen_pairs.add(pair)

    # Generate reports
    generate_reports(
        duplicates, similarities, output_folder,
        check_files, check_sentences, check_paragraphs, check_phrases, check_words,
        min_phrase_length, max_phrase_length
    )

    print("Deduplication process completed.")  # Debugging info

def add_to_report(report, content, file1, file2, similarity):
    if content not in report:
        report[content] = set()
    report[content].add((file1, file2, similarity))

def hash_content(content):
    return hashlib.md5(content.encode('utf-8')).hexdigest()

if __name__ == "__main__":
    app()
