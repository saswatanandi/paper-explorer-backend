"""
Not needed anymore. Used to process legacy CSV files and update the corresponding JSON files.

This script processes CSV files in the legacy data directory, extracts paper metadata,
and updates the corresponding JSON files in the topics directory.
Usage:
    python csv_to_json.py
Requirements:
    - Python 3.x
    - pandas
    - gscholar
    - tqdm
    - asyncio
    - aiohttp
    - beautifulsoup4
    - lxml  

"""

import os
import json
import argparse
import pandas as pd
from pathlib import Path
import hashlib
import time
import random
from typing import Dict, List, Optional, Any
import asyncio
from gscholar import GoogleScholarScraper

# Constants
DATA_DIR = Path("../data")
LEGACY_DATA_DIR = DATA_DIR / "legacy_data"
TOPICS_DIR = DATA_DIR / "topics"
DATABASES_DIR = DATA_DIR / "databases"

UNIQUE_PAPERS_FILE = DATABASES_DIR / "unique_papers.json"
KNOWN_JOURNALS_FILE = DATABASES_DIR / "known_journals.json"
SKIP_JOURNALS_FILE = DATABASES_DIR / "skip_journals.json"

# Ensure directories exist
TOPICS_DIR.mkdir(exist_ok=True, parents=True)
DATABASES_DIR.mkdir(exist_ok=True, parents=True)

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

def manual_paper_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Allow users to manually provide or edit paper metadata.
    """
    # Print current metadata if any
    if metadata:
        print(f"\n{'='*50}")
        print("\nCurrent metadata:")
        print(f"{'-'*50}")  
        for key, value in metadata.items():
            if key == "title" and value:
                # Show title
                print(f"title: {value}")
                print(f"{'-'*50}")  
            elif key == "authors" and value:
                # Format authors nicely
                author_str = ", ".join([f"{a.get('first_name', '')} {a.get('last_name', '')}" for a in value])
                print(f"authors: {author_str}") 
                print(f"{'-'*50}")                       
            elif key == "abstract" and value:
                # Show truncated abstract for readability
                print(f"abstract: {value}")
                print(f"{'-'*50}")
            else:
                print(f"{key}: {value}")
                print(f"{'-'*50}")
                
        # First ask if everything is correct as is
        is_ok = input("\nIs the metadata correct as is? (y/n): ").lower().strip()
        if is_ok == 'y' or is_ok == 'Y' or is_ok == 'yes' or is_ok == '':
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
    
    # Abstract
    abstract_preview = metadata.get('abstract', '')[:100] + "..." if metadata.get('abstract', '') and len(metadata['abstract']) > 100 else metadata.get('abstract', '')
    print(f"Abstract [{abstract_preview}]:")
    print("Enter new abstract (or press Enter to keep existing):")
    print("(You can paste multi-line text, press Enter twice when finished)")
    
    # Handle multi-line input for abstract
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

def load_json_file(file_path: Path, default: Any = None) -> Any:
    """Load a JSON file or return a default value if the file doesn't exist."""
    if not file_path.exists():
        return default if default is not None else {}

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Warning: Error parsing JSON file {file_path}: {e}")
        print("Using default empty value instead.")
        return default if default is not None else {}

def save_json_file(file_path: Path, data: Any) -> None:
    """Save data to a JSON file with pretty formatting."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def generate_paper_id(title: str, year: str) -> str:
    """Generate a unique ID for a paper based on its title and year."""
    # Normalize the title by removing extra spaces and converting to lowercase
    normalized_title = ' '.join(title.lower().split())
    # Create a string combining title and year
    id_string = f"{normalized_title}_{year}"
    # Generate a hash
    return hashlib.md5(id_string.encode('utf-8')).hexdigest()

def is_duplicate(paper_id: str, unique_papers: Dict) -> bool:
    """Check if a paper is already in the unique papers database."""
    return paper_id in unique_papers

def add_to_unique_papers(paper_id: str, paper_data: Dict, unique_papers: Dict) -> Dict:
    """Add a paper to the unique papers database."""
    unique_papers[paper_id] = {
        "title": paper_data["title"],
        "year": paper_data["year"],
        "authors": paper_data["authors"],
        "topic": paper_data["topic"],
        "abstract": paper_data["abstract"],
        "citations": paper_data["citations"],
    }
    return unique_papers

def update_known_journals(journal: str, topic: str, known_journals: Dict) -> Dict:
    """Update the known journals database with a new journal if it doesn't exist."""
    if journal not in known_journals:
        known_journals[journal] = {
            "categories": [topic],
            "date_added": time.strftime("%Y-%m-%d")
        }
    elif topic not in known_journals[journal]["categories"]:
        known_journals[journal]["categories"].append(topic)

    return known_journals

def is_journal_skipped(journal: str, skip_journals: Dict) -> bool:
    """Check if a journal is in the skip journals list."""
    if not journal:
        return False

    # Check if the journal name exists in the skip_journals dictionary
    return journal in skip_journals

async def process_papers_batch(titles: List[str]) -> Dict[str, Dict]:
    """Process a batch of papers with a single browser instance."""
    scraper = GoogleScholarScraper()
    await scraper.initialize()

    try:
        results = {}
        for title in titles:
            # Make print prettier
            print(f"\n{'-'*50}")
            print(f"Fetching metadata for: {title}")
            metadata = await scraper.search_paper(title)
            results[title] = metadata
            # Add a small delay to avoid being blocked
            await asyncio.sleep(random.uniform(1, 2))
        print(f"\n{'-'*50}")

        return results
    finally:
        # Ensure the browser is closed properly
        await scraper.close()

# Replace the asyncio.run with a custom event loop manager
def run_async(coro):
    """Custom function to run coroutines with proper cleanup."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(coro)
    except Exception as e:
        print(f"Error in async execution: {e}")
        raise
    finally:
        # Cancel pending tasks but don't close the loop
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        # Run the event loop until tasks are canceled
        if pending:
            loop.run_until_complete(
                asyncio.gather(*pending, return_exceptions=True)
            )       

def process_csv_file(csv_path: Path, topic: str) -> None:
    """Process a single CSV file and update the corresponding JSON files."""
    print(f"Processing {csv_path}...")

    # Load existing databases
    unique_papers = load_json_file(UNIQUE_PAPERS_FILE, {})
    known_journals = load_json_file(KNOWN_JOURNALS_FILE, {})
    skip_journals = load_json_file(SKIP_JOURNALS_FILE, {})
    topic_papers = load_json_file(TOPICS_DIR / f"{topic}.json", {"papers": []})

    # Read the CSV file
    try:
        # First try with default encoding (utf-8)
        df = pd.read_csv(csv_path)
        print(f"Found {len(df)} papers in {csv_path}")
    except UnicodeDecodeError as e:
        # If we get a specific unicode decode error, try with latin1 encoding
        print(f"Unicode error with default encoding. Trying latin1 encoding...")
        try:
            df = pd.read_csv(csv_path, encoding='latin1')
            print(f"Successfully read with latin1 encoding. Found {len(df)} papers in {csv_path}")
        except Exception as e2:
            print(f"Error reading {csv_path} with latin1 encoding: {e2}")
            return
    except Exception as e:
        # Handle other types of errors
        print(f"Error reading {csv_path}: {e}")
        return



    # Collect all valid titles first
    titles = []
    paper_rows = []

    for _, row in df.iterrows():
        title = str(row.get('title', '')).strip()
        year = str(row.get('year', '')).strip()

        if title and year:
            # Check if this paper is already in the database
            paper_id = generate_paper_id(title, year)
            if not is_duplicate(paper_id, unique_papers):
                titles.append(title)
                paper_rows.append(row)

    print(f"Fetching metadata for {len(titles)} papers...")

    # Fetch metadata for all papers in a batch
    # metadata_dict = asyncio.run(process_papers_batch(titles))
    metadata_dict = run_async(process_papers_batch(titles))

    # Process each valid row with the fetched metadata
    papers_added = 0
    papers_skipped = 0

    for i, row in enumerate(paper_rows):
        try:
            year = str(row.get('year', '')).strip()
            title = str(row.get('title', '')).strip()

            # Generate a unique ID for the paper
            paper_id = generate_paper_id(title, year)

            # Get the metadata we've fetched
            metadata = metadata_dict.get(title, {})

            # Convert author format from list of strings to list of dicts
            formatted_authors = []
            if metadata.get("authors"):
                for author in metadata.get("authors", []):
                    # Split the author name into first and last names
                    name_parts = author.split()
                    if len(name_parts) > 1:
                        formatted_authors.append({
                            "first_name": " ".join(name_parts[:-1]),
                            "last_name": name_parts[-1]
                        })
                    else:
                        formatted_authors.append({
                            "first_name": "",
                            "last_name": author
                        })

            # Prepare metadata for manual checking/editing
            metadata_to_check = {
                "title": title,
                "year": int(year) if year.isdigit() else year,
                "authors": formatted_authors,
                "journal": metadata.get("journal", ""),
                "citations": metadata.get("citations", 0),
                "abstract": metadata.get("abstract", ""),
                "url": metadata.get("url", "")
            }

            # Allow manual checking and editing of metadata
            updated_metadata = manual_paper_metadata(metadata_to_check)

            # Prepare the paper data with reordered attributes
            paper_data = {
                "id": generate_paper_id(updated_metadata.get("title", title), year),
                "year": updated_metadata.get("year", int(year) if year.isdigit() else year),
                "authors": updated_metadata.get("authors", formatted_authors),
                "title": updated_metadata.get("title", title),
                "journal": updated_metadata.get("journal", ""),
                "citations": updated_metadata.get("citations", 0),
                "abstract": updated_metadata.get("abstract", ""),
                "url": updated_metadata.get("url", ""),
                "date_added": time.strftime("%Y-%m-%d"),
                "topic": topic
            }

            # Update known journals if we have journal information
            journal = paper_data.get("journal", "")
            if journal:
                known_journals = update_known_journals(journal, topic, known_journals)

            # Add the paper to the topic's JSON file
            topic_papers["papers"].append(paper_data)

            # Add the paper to the unique papers database (keep the existing format for this)
            unique_papers = add_to_unique_papers(paper_id, paper_data, unique_papers)

            papers_added += 1
            print(f"Added paper: {title}")

        except Exception as e:
            print(f"Error processing paper: {e}")
            papers_skipped += 1

    # Save the updated databases
    save_json_file(UNIQUE_PAPERS_FILE, unique_papers)
    save_json_file(KNOWN_JOURNALS_FILE, known_journals)
    save_json_file(TOPICS_DIR / f"{topic}.json", topic_papers)

    print(f"Finished processing {csv_path}")
    print(f"Papers added: {papers_added}, Papers skipped: {papers_skipped}")

def process_all_csv_files() -> None:
    """Process all CSV files in the legacy data directory."""
    for csv_file in LEGACY_DATA_DIR.glob("*.csv"):
        topic = csv_file.stem  # Get the filename without extension as the topic
        process_csv_file(csv_file, topic)

def main() -> None:
    """Main function to process legacy CSV files."""
    parser = argparse.ArgumentParser(description="Process legacy CSV files and enrich with metadata")
    parser.add_argument("--topic", help="Specific topic to process (CSV filename without extension)")
    args = parser.parse_args()

    if args.topic:
        csv_path = LEGACY_DATA_DIR / f"{args.topic}.csv"
        if csv_path.exists():
            process_csv_file(csv_path, args.topic)
        else:
            print(f"Error: CSV file for topic '{args.topic}' not found")
    else:
        process_all_csv_files()

if __name__ == "__main__":
    main()