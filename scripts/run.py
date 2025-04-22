# main.py
import os
import json
import hashlib
import csv
import gzip
import datetime
import asyncio
import re
from typing import Dict, List, Any, Optional, Set
from pathlib import Path
from email.parser import BytesParser
from email.policy import default
import subprocess
import readchar
import shutil
from bs4 import BeautifulSoup
from gscholarNoprint import GoogleScholarScraper, clean_text


# Utility functions
def generate_paper_id(title: str, year: str) -> str:
    """Generate a unique ID for a paper based on its title and year."""
    # Normalize the title by removing extra spaces and converting to lowercase
    normalized_title = ' '.join(title.lower().split())
    # Create a string combining title and year
    id_string = f"{normalized_title}_{year}"
    # Generate a hash
    return hashlib.md5(id_string.encode('utf-8')).hexdigest()

def clean_unicode_text(text: str) -> str:
    """Clean and normalize Unicode characters in text."""
    if not text:
        return ""
    
    # Replace common Unicode problems
    text = text.replace('\u2010', '-')  # Unicode hyphen
    text = text.replace('\u2011', '-')  # Non-breaking hyphen
    text = text.replace('\u2012', '-')  # Figure dash
    text = text.replace('\u2013', '-')  # En dash
    text = text.replace('\u2014', '-')  # Em dash
    text = text.replace('\u2015', '-')  # Horizontal bar
    text = text.replace('\u00a0', ' ')  # Non-breaking space
    text = text.replace('\u2026', '...')  # Ellipsis
    
    return text

def extract_html_from_eml(eml_file: str) -> Optional[str]:
    """Extract HTML content from an .eml file if it's a Google Scholar alert."""
    try:
        with open(eml_file, 'rb') as f:
            msg = BytesParser(policy=default).parse(f)
            
            # Check if this is a Google Scholar alert
            if 'scholaralerts-noreply@google.com' not in msg.get('From', ''):
                return None
            
            # Get HTML content
            for part in msg.walk():
                if part.get_content_type() == 'text/html':
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error processing {eml_file}: {e}")
    return None

def extract_paper_titles_from_html(html_content: str) -> List[str]:
    """Extract paper titles from Google Scholar alert HTML content."""
    titles = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    for title_link in soup.find_all('a', class_='gse_alrt_title'):
        title = title_link.text.strip()
        titles.append(title)
    
    return titles

def load_csv_to_set(file_path: str, column_name: str) -> Set[str]:
    """Load a CSV file's column into a set."""
    result = set()
    if os.path.exists(file_path):
        # Try different encodings if UTF-8 fails
        encodings = ['utf-8', 'latin-1', 'cp1252']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    reader = csv.DictReader(f)
                    if reader.fieldnames and column_name in reader.fieldnames:
                        for row in reader:
                            result.add(row[column_name].strip().lower())
                # If we get here, reading was successful
                break
            except UnicodeDecodeError:
                # Try the next encoding
                continue
            except Exception as e:
                print(f"Error reading {file_path} with {encoding} encoding: {e}")
                # Create an empty file if it can't be read at all
                if encoding == encodings[-1]:  # Last encoding attempt
                    print(f"Creating new empty file for {file_path}")
                    with open(file_path, 'w', encoding='utf-8', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=[column_name])
                        writer.writeheader()
    return result


def compress_json_file(input_file, output_file):
    """
    Compresses a JSON file using gzip with maximum compression.
    """
    try:
        with open(input_file, 'rb') as f:
            data = f.read()

        # Create directories if they don't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # Write compressed data with maximum compression level (9)
        with gzip.open(output_file, 'wb', compresslevel=9) as f:
            f.write(data)

        original_size = os.path.getsize(input_file)
        compressed_size = os.path.getsize(output_file)
        compression_ratio = (1 - compressed_size / original_size) * 100

        print(f"Compressed {input_file} to {output_file}")
        print(f"Original size: {original_size:,} bytes")
        print(f"Compressed size: {compressed_size:,} bytes")
        print(f"Compression ratio: {compression_ratio:.2f}%")

        return {
            "original_size": original_size,
            "compressed_size": compressed_size,
            "compression_ratio": compression_ratio
        }
    except Exception as e:
        print(f"Error compressing file: {e}")
        return None    

def load_journal_mapping(file_path: str) -> Dict[str, str]:
    """Load journal name mapping from CSV."""
    mapping = {}
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if "lowercase_name" in reader.fieldnames and "correct_name" in reader.fieldnames:
                for row in reader:
                    mapping[row["lowercase_name"].strip().lower()] = row["correct_name"].strip()
    return mapping

def save_set_to_csv(data: Set[str], file_path: str, column_name: str):
    """Save a set to a CSV file."""
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[column_name])
        writer.writeheader()
        for item in sorted(data):
            writer.writerow({column_name: item})

def save_journal_mapping(mapping: Dict[str, str], file_path: str):
    """Save journal mapping to CSV."""
    with open(file_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["lowercase_name", "correct_name"])
        writer.writeheader()
        for lowercase, correct in sorted(mapping.items()):
            writer.writerow({"lowercase_name": lowercase, "correct_name": correct})

def load_json_database(file_path: str) -> Dict:
    """Load a JSON database file or return an empty structure."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"papers": []}

def save_json_database(data: Dict, file_path: str):
    """Save data to a JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, indent=2, ensure_ascii=False, fp=f)

def format_authors_for_storage(authors_list: List[str]) -> List[Dict[str, str]]:
    """Format a list of author strings into structured author objects."""
    formatted_authors = []
    
    for author in authors_list:
        parts = author.strip().split()
        if len(parts) >= 2:
            # Assume the last part is the last name, everything before is first name
            last_name = parts[-1]
            first_name = ' '.join(parts[:-1])
            formatted_authors.append({
                "first_name": first_name,
                "last_name": last_name
            })
        elif len(parts) == 1:
            # Handle single name authors
            formatted_authors.append({
                "first_name": "",
                "last_name": parts[0]
            })
    
    return formatted_authors

def display_topics_for_selection(topics: Set[str]) -> str:
    """Display topics and let the user select one or create a new one."""
    topics_list = sorted(list(topics))

    def display_topics_in_columns(topics_to_display, search_term="", selection_buffer=""):
        """Display topics in multiple columns with numbers."""
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')

        # Get terminal width and calculate columns
        terminal_width = shutil.get_terminal_size().columns
        max_topic_length = max([len(str(i) + ". " + t) for i, t in enumerate(topics_to_display, 1)]) if topics_to_display else 0
        num_columns = max(1, terminal_width // (max_topic_length + 4))

        # Calculate rows needed for even distribution of topics across columns
        num_topics = len(topics_to_display)
        num_rows = (num_topics + num_columns - 1) // num_columns if topics_to_display else 0

        print("\nSelect a topic (or type to search, 0 to create new):")
        if search_term:
            print(f"Search: {search_term}")
        elif selection_buffer:
            print(f"Enter number: {selection_buffer}")

        # Display topics in columns - using column-first distribution
        for row in range(num_rows):
            line = ""
            for col in range(num_columns):
                idx = col * num_rows + row  # Column-first distribution
                if idx < len(topics_to_display):
                    topic_str = f"{idx + 1}. {topics_to_display[idx]}"
                    line += topic_str.ljust(max_topic_length + 4)
            print(line)

        print("\n0. Create new topic")

        if search_term:
            print("\nContinue typing to refine search or:")
            print("- Press Enter to select/create search term")
            print("- Press Backspace to delete")
            print("- Press Esc to cancel search")
        elif selection_buffer:
            print("\n- Press Enter to confirm selection")
            print("- Press Backspace to delete")
            print("- Press Esc to cancel selection")
        else:
            print("\nEnter number to select or type to search")

    search_term = ""
    selection_buffer = ""  # Buffer to collect full numeric input
    filtered_topics = topics_list

    # Initial display
    display_topics_in_columns(topics_list)

    while True:
        # Get keystroke
        key = readchar.readkey()

        # Handle numeric input for selection buffer
        if key.isdigit() and not search_term:
            selection_buffer += key
            display_topics_in_columns(filtered_topics, search_term, selection_buffer)
            continue

        # Handle Enter key for selection confirmation
        if key == readchar.key.ENTER and selection_buffer:
            try:
                choice_num = int(selection_buffer)
                if choice_num == 0:
                    # Create new topic
                    os.system('cls' if os.name == 'nt' else 'clear')
                    print("\nCreate new topic:")
                    new_topic = input("Enter topic name: ").strip()
                    if new_topic:
                        return new_topic
                    else:
                        # If empty, redisplay the topics
                        selection_buffer = ""
                        display_topics_in_columns(topics_list)
                        continue
                elif 1 <= choice_num <= len(filtered_topics):
                    return filtered_topics[choice_num - 1]
                else:
                    # Invalid number
                    print("Invalid selection. Please try again.")
                    selection_buffer = ""
                    display_topics_in_columns(filtered_topics, search_term)
            except ValueError:
                selection_buffer = ""
                display_topics_in_columns(filtered_topics, search_term)

        # Handle backspace for selection buffer
        elif key == readchar.key.BACKSPACE and selection_buffer:
            selection_buffer = selection_buffer[:-1]
            display_topics_in_columns(filtered_topics, search_term, selection_buffer)
            continue

        # Handle escape key to cancel selection
        elif key == readchar.key.ESC and selection_buffer:
            selection_buffer = ""
            display_topics_in_columns(filtered_topics, search_term)
            continue

        # Handle search mode (when not in selection mode)
        elif not selection_buffer and (key.isalpha() or (search_term and key.isalnum())):
            # Add to search term
            search_term += key
            # Filter topics that start with the search term
            filtered_topics = [t for t in topics_list if t.lower().startswith(search_term.lower())]
            display_topics_in_columns(filtered_topics, search_term)

        # Handle special keys for search mode
        elif key == readchar.key.ENTER and search_term:
            # If exact match exists, return it
            exact_matches = [t for t in topics_list if t.lower() == search_term.lower()]
            if exact_matches:
                return exact_matches[0]

            # Otherwise create new topic from search term
            os.system('cls' if os.name == 'nt' else 'clear')
            print(f"\nCreate new topic '{search_term}'? (y/n)")
            confirm = readchar.readkey().lower()
            if confirm == 'y':
                return search_term
            else:
                # Redisplay if user doesn't confirm
                search_term = ""
                filtered_topics = topics_list
                display_topics_in_columns(topics_list)

        elif key == readchar.key.BACKSPACE and search_term:
            # Remove last character from search
            search_term = search_term[:-1]
            if search_term:
                filtered_topics = [t for t in topics_list if t.lower().startswith(search_term.lower())]
            else:
                filtered_topics = topics_list
            display_topics_in_columns(filtered_topics, search_term)

        elif key == readchar.key.ESC:
            # Cancel search and redisplay all topics
            search_term = ""
            filtered_topics = topics_list
            display_topics_in_columns(topics_list)

        elif not key.isalnum() and key not in [readchar.key.ENTER, readchar.key.BACKSPACE, readchar.key.ESC]:
            # Invalid input
            display_topics_in_columns(filtered_topics, search_term, selection_buffer)
            print("Invalid input. Use numbers to select or letters to search.")


def manual_paper_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Allow users to manually provide or edit paper metadata."""
    is_ok = input("\nIs the metadata correct as is? (y/n): ").lower().strip()
    if is_ok in ['y', 'yes', '']:
        return metadata
    
    print("\nEnter paper metadata (press Enter to skip or keep existing):")
    
    # Title
    title_input = input(f"Title [{metadata.get('title', '')}]: ").strip()
    if title_input:
        metadata["title"] = title_input
    
    # Authors (comma separated)
    current_authors = ""
    if "authors" in metadata and metadata["authors"]:
        current_authors = ", ".join([f"{a.get('first_name', '')} {a.get('last_name', '')}" for a in metadata["authors"]])
        
    authors_input = input(f"Authors [{current_authors}] (format: 'First1 Last1, First2 Last2'): ").strip()
    if authors_input:
        author_list = [a.strip() for a in authors_input.split(',')]
        metadata["authors"] = []
        for author in author_list:
            parts = author.split()
            if len(parts) >= 2:
                last_name = parts[-1]
                first_name = ' '.join(parts[:-1])
                metadata["authors"].append({"first_name": first_name, "last_name": last_name})
            elif len(parts) == 1:
                metadata["authors"].append({"first_name": "", "last_name": parts[0]})
    
    # Year
    year_input = input(f"Year [{metadata.get('year', '')}]: ").strip()
    if year_input:
        metadata["year"] = int(year_input) if year_input.isdigit() else metadata.get("year", "")
    
    # Journal
    journal_input = input(f"Journal [{metadata.get('journal', '')}]: ").strip()
    if journal_input:
        metadata["journal"] = journal_input
    
    # Citations
    citations_input = input(f"Citations [{metadata.get('citations', 0)}]: ").strip()
    if citations_input and citations_input.isdigit():
        metadata["citations"] = int(citations_input)
    
    # URL
    url_input = input(f"URL [{metadata.get('url', '')}]: ").strip()
    if url_input:
        metadata["url"] = url_input
    
    # Abstract (with multi-line support)
    abstract_preview = metadata.get('abstract', '')[:100] + "..." if metadata.get('abstract', '') and len(metadata['abstract']) > 100 else metadata.get('abstract', '')
    print(f"Abstract [{abstract_preview}]:")
    print("Enter new abstract (or press Enter to keep existing):")
    print("(You can paste multi-line text, press Enter twice when finished)")
    
    abstract_lines = []
    while True:
        line = input()
        if not line and not abstract_lines:
            # User pressed Enter immediately, keep existing abstract
            break
        abstract_lines.append(line)
        if not line and abstract_lines:
            # User pressed Enter twice, finish input
            break
    
    if abstract_lines:
        # Join lines but remove the last empty line
        abstract_input = "\n".join(abstract_lines[:-1] if abstract_lines[-1] == "" else abstract_lines)
        if abstract_input:
            metadata["abstract"] = clean_unicode_text(abstract_input)
    
    return metadata

async def process_eml_files(
    eml_dir: str, 
    data_dir: str,
    scraper: GoogleScholarScraper
) -> None:
    """Process EML files, extract papers, and manage the database."""
    
    # Ensure directories exist
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(os.path.join(data_dir, "databases"), exist_ok=True)
    
    # Define file paths
    avoid_journals_path = os.path.join(data_dir, "databases", "csv", "avoid.csv")
    unique_paper_id_path = os.path.join(data_dir, "databases", "csv", "unique_paper_id.csv")
    unique_journal_path = os.path.join(data_dir, "databases", "csv", "unique_journal.csv")
    unique_topic_path = os.path.join(data_dir, "databases", "csv", "unique_topic.csv")
    
    # Load data from CSV files to memory
    avoid_journals = load_csv_to_set(avoid_journals_path, "name")
    unique_paper_ids = load_csv_to_set(unique_paper_id_path, "id")
    journal_mapping = load_journal_mapping(unique_journal_path)
    topics = load_csv_to_set(unique_topic_path, "name")
    
    # Extract paper titles from EML files
    print("Extracting paper titles from EML files...")
    all_titles = []
    for eml_file in Path(eml_dir).glob('*.eml'):
        html_content = extract_html_from_eml(str(eml_file))
        if html_content:
            titles = extract_paper_titles_from_html(html_content)
            all_titles.extend(titles)
    
    # Remove duplicates while preserving order
    unique_titles = []
    seen = set()
    for title in all_titles:
        if title not in seen:
            unique_titles.append(title)
            seen.add(title)
    
    print(f"Found {len(unique_titles)} unique paper titles.")
    
    # Process each paper
    selected_papers = []
    
    for i, title in enumerate(unique_titles, 1):
        print(f"\n[{i}/{len(unique_titles)}] Processing: {title}")
        
        # Scrape paper metadata
        paper_info = await scraper.search_paper(title)
        
        # Convert scraped format to our storage format
        paper_metadata = {
            "title": clean_unicode_text(paper_info.get("title", title)),
            "year": paper_info.get("year", ""),
            "authors": format_authors_for_storage(paper_info.get("authors", [])),
            "journal": paper_info.get("journal", ""),
            "citations": paper_info.get("citations", 0),
            "abstract": clean_unicode_text(paper_info.get("abstract", "")),
            "url": paper_info.get("url", ""),
            "date_added": datetime.datetime.now().strftime("%Y-%m-%d")
        }

        # Generate paper ID early to check if it already exists
        if paper_metadata.get("title") and paper_metadata.get("year"):
            paper_id = generate_paper_id(paper_metadata["title"], str(paper_metadata["year"]))
            
            # Check if paper already exists
            if paper_id in unique_paper_ids:
                print(f"Paper already exists with ID: {paper_id}")
                continue
        
        # Check journal against avoid list early
        if paper_metadata.get("journal"):
            journal_lower = paper_metadata["journal"].lower()
            if journal_lower in avoid_journals:
                print(f"Journal '{paper_metadata['journal']}' is in the avoid list. Skipping paper.")
                continue 

        # Display basic paper info before asking to add
        print("\n" + "="*60)
        print("="*60)
        print(f"  Title:     {paper_metadata.get('title', '')}")
        print(f"  Journal:   {paper_metadata.get('journal', '')}")
        print(f"  Year:      {paper_metadata.get('year', '')}")
        print(f"  Citations: {paper_metadata.get('citations', 0)}")
        
        if paper_metadata.get('authors'):
            author_str = ", ".join([f"{a.get('first_name', '')} {a.get('last_name', '')}" for a in paper_metadata['authors']])
            print(f"  Authors:   {author_str}")
        
        if paper_metadata.get('abstract'):
            # Truncate abstract if it's too long
            abstract = paper_metadata.get('abstract', '')
            print(f"\n  Abstract:  {abstract}")
        
        if paper_metadata.get('url'):
            print(f"\n  URL:       {paper_metadata.get('url', '')}")
        
        print("-"*60)

        
        # If this is a new journal, ask if we want to add it to avoid list
        if paper_metadata.get("journal"):
            journal_lower = paper_metadata["journal"].lower()
            if journal_lower not in avoid_journals and journal_lower not in journal_mapping:
                add_to_avoid = input(f"New journal '{paper_metadata['journal']}'. Add to avoid list? (y/n): ").lower().strip()
                if add_to_avoid == 'y':
                    avoid_journals.add(journal_lower)
                    print(f"Added '{journal_lower}' to avoid journals list.")
                    continue
        
        # Ask if we want to add this paper BEFORE doing detailed metadata editing
        add_paper = input("Add this paper to the database? (y/n): ").lower().strip()
        if add_paper != 'y':
            continue
        
        # Check if we need to modify paper metadata
        print("\nReview paper information:")
        paper_metadata = manual_paper_metadata(paper_metadata)
        
        # Validate required fields
        if not all([
            paper_metadata.get("title"), 
            paper_metadata.get("year"),
            paper_metadata.get("journal"),
            paper_metadata.get("abstract")
        ]):
            print("Paper missing required fields. Skipping.")
            continue
        
        # Generate paper ID
        paper_id = generate_paper_id(paper_metadata["title"], str(paper_metadata["year"]))
        paper_metadata["id"] = paper_id
        
        # Check if paper already exists
        if paper_id in unique_paper_ids:
            print(f"Paper already exists with ID: {paper_id}")
            continue
        
        # Check journal against avoid list
        journal_lower = paper_metadata["journal"].lower()
        if journal_lower in avoid_journals:
            print(f"Journal '{paper_metadata['journal']}' is in the avoid list. Skipping paper.")
            continue
        
        # Check if we need to normalize journal name
        if journal_lower in journal_mapping:
            print(f"Normalizing journal name from '{paper_metadata['journal']}' to '{journal_mapping[journal_lower]}'")
            paper_metadata["journal"] = journal_mapping[journal_lower]
        else:
            # Ask if we need to normalize this journal name
            normalize = input(f"New journal encountered. Should modify journal name '{paper_metadata['journal']}'? (y/n): ").lower().strip()
            if normalize == 'y':
                correct_name = input("Enter correct journal name: ").strip()
                if correct_name:
                    journal_mapping[journal_lower] = correct_name
                    paper_metadata["journal"] = correct_name
        
        
        # Select topic
        topic = display_topics_for_selection(topics)
        if topic:
            paper_metadata["topic"] = [topic]
            topics.add(topic)
        
        # Add paper to selected papers
        selected_papers.append(paper_metadata)
        unique_paper_ids.add(paper_id)
        
        print(f"Added paper: {paper_metadata['title']}")
    
    # Save all selected papers to current year file
    if selected_papers:
        # Get current year
        current_year = str(datetime.datetime.now().year)
        
        # Save all papers to current year file
        year_file = os.path.join(data_dir, "databases", "json", f"{current_year}.json")
        
        # Load existing file if it exists
        existing_data = load_json_database(year_file)
        
        # Add new papers
        existing_data["papers"].extend(selected_papers)
        
        # Save updated file
        save_json_database(existing_data, year_file)
        print(f"Saved {len(selected_papers)} papers to {year_file}")   

        # compress the json file
        compressed_output = os.path.join(data_dir, "databases", "upload", f"{current_year}.json.gz")
        compress_json_file(year_file, compressed_output)
    
    # Save updated CSV files
    save_set_to_csv(avoid_journals, avoid_journals_path, "name")
    save_set_to_csv(unique_paper_ids, unique_paper_id_path, "id")
    save_journal_mapping(journal_mapping, unique_journal_path)
    save_set_to_csv(topics, unique_topic_path, "name")
    
    print("\nProcessing complete!")

async def main():
    """Main entry point."""
    
    # Define directories
    eml_dir = "../data/eml"
    data_dir = "../data"
    
    # Create Google Scholar scraper
    scraper = GoogleScholarScraper()
    
    try:
        # Initialize scraper (browser opens only once)
        await scraper.initialize()
        
        # Process EML files
        await process_eml_files(eml_dir, data_dir, scraper)      

    finally:
        await scraper.close()
        await asyncio.sleep(0.5)      # keep this line

        # ── add the three lines below ───────────────────────────────────
        import gc
        await asyncio.sleep(0)        # let pending callbacks run
        gc.collect()                  # run all finalisers *now*      

if __name__ == "__main__":
    import nodriver as uc          # ← get Nodriver’s global loop
    loop = uc.loop()               # ← the loop Nodriver already uses
    loop.run_until_complete(main())
