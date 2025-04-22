# =============================
# CREATE FIRST VERSION OF PAPER
# =============================
# import json
# import pandas as pd
# import os

# # Load the JSON data
# try:
#     with open('../data/databases/_combined.json', 'r', encoding='utf-8') as f:
#         data = json.load(f)
# except FileNotFoundError:
#     print("File not found. Using sample data instead.")

# # Extract journal names
# journals = []
# for paper in data.get('papers', []):
#     journal_name = paper.get('journal')
#     if journal_name:
#         journals.append(journal_name)

# # Create a dictionary mapping lowercase journal names to their original form
# journal_dict = {}
# for journal in journals:
#     lower_journal = journal.lower()
#     if lower_journal not in journal_dict:
#         journal_dict[lower_journal] = journal

# # Create a DataFrame for unique journals
# journal_df = pd.DataFrame({
#     'lowercase_name': list(journal_dict.keys()),
#     'correct_name': list(journal_dict.values())
# })

# # Sort by lowercase name for better readability
# journal_df = journal_df.sort_values('lowercase_name').reset_index(drop=True)

# # Save to CSV
# journal_df.to_csv('unique_journal.csv', index=False)


# ================================
# CREATE FIRST VERSION OF PAPER_ID
# ================================

# import json
# import pandas as pd
# import os

# # Define the path to the JSON file
# json_path = '../data/databases/_combined.json'

# # Check if the file exists
# if not os.path.exists(json_path):
#     print(f"File not found: {json_path}")
# else:
#     # Load the JSON data
#     with open(json_path, 'r') as f:
#         data = json.load(f)
    
#     # Extract paper IDs
#     paper_ids = [paper['id'] for paper in data['papers']]
    
#     # Count unique IDs
#     unique_ids = set(paper_ids)
#     print(f"Total papers: {len(paper_ids)}")
#     print(f"Unique paper IDs: {len(unique_ids)}")
#     print(f"Duplicate IDs: {len(paper_ids) - len(unique_ids)}")
    
#     # Create a DataFrame with unique IDs
#     df = pd.DataFrame({'id': list(unique_ids)})
    
#     # Save to CSV
#     df.to_csv('unique_paper_id.csv', index=False)


# ==================================================================
# CREATE FIRST VERSION OF COMBINED.json and compressed-COMBINED.json
# ==================================================================
import json
import os
import gzip
from pathlib import Path

# def combine_json_files(input_folder, output_file):
#     """
#     Combines multiple JSON files from the input folder into a single JSON file.
#     Converts 'topic' field to an array if it's a string.
#     """
#     all_papers = []

#     # Create directories if they don't exist
#     os.makedirs(os.path.dirname(output_file), exist_ok=True)

#     # Process each JSON file in the input folder
#     for filename in os.listdir(input_folder):
#         if filename.endswith('.json'):
#             file_path = os.path.join(input_folder, filename)
#             try:
#                 with open(file_path, 'r', encoding='utf-8') as f:
#                     data = json.load(f)

#                 # Process papers in the current file
#                 if 'papers' in data:
#                     for paper in data['papers']:
#                         # Convert topic to array if it's a string
#                         if 'topic' in paper and isinstance(paper['topic'], str):
#                             paper['topic'] = [paper['topic']]
#                         all_papers.append(paper)
#             except Exception as e:
#                 print(f"Error processing {filename}: {e}")

#     # Write the combined data to the output file
#     with open(output_file, 'w', encoding='utf-8') as f:
#         json.dump({"papers": all_papers}, f, indent=2)

#     print(f"Combined {len(all_papers)} papers into {output_file}")
#     return len(all_papers)

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


# Step 1: Combine JSON files
input_folder = "../data/topics"
combined_output = "../data/databases/corrected_combined.json"
# combine_json_files(input_folder, combined_output)

# Step 2: Compress the combined file
compressed_output = "../data/databases/2024.json.gz"  # Changed extension to .gz
compress_json_file(combined_output, compressed_output)




# ====================================================
# Make corrected version of  first _combined.json file
# ====================================================
# import json
# import os
# import csv
# import pandas as pd
# from pathlib import Path

# # Define file paths
# input_file = Path("../data/databases/_combined.json")
# output_file = Path("../data/databases/corrected_combined.json")
# unique_paper_id_file = Path("../data/databases/unique_paper_id.csv")
# unique_journal_file = Path("../data/databases/unique_journal.csv")

# # Create directories if they don't exist
# os.makedirs(os.path.dirname(output_file), exist_ok=True)

# # Initialize unique paper IDs and journals
# unique_paper_ids = set()
# journal_mapping = {}

# # Load existing unique paper IDs if file exists
# if unique_paper_id_file.exists():
#     with open(unique_paper_id_file, 'r', newline='', encoding='utf-8') as f:
#         reader = csv.DictReader(f)
#         for row in reader:
#             unique_paper_ids.add(row['id'])

# # Load existing journal mappings if file exists
# if unique_journal_file.exists():
#     with open(unique_journal_file, 'r', newline='', encoding='utf-8') as f:
#         reader = csv.DictReader(f)
#         for row in reader:
#             journal_mapping[row['lowercase_name']] = row['correct_name']

# # Load the JSON data
# try:
#     with open(input_file, 'r', encoding='utf-8') as f:
#         data = json.load(f)
# except FileNotFoundError:
#     print(f"Input file {input_file} not found.")
#     data = {"papers": []}
# except json.JSONDecodeError:
#     print(f"Error decoding JSON from {input_file}.")
#     data = {"papers": []}

# # Function to simulate user input for journal names
# # In a real application, you would replace this with actual user input
# def get_user_input_for_journal(journal_name):
#     print(f"New journal found: {journal_name}")
#     # For simulation, we'll just use the original name with proper capitalization
#     # In a real application, you would prompt the user for input
#     words = journal_name.split()
#     corrected = ' '.join(word.capitalize() for word in words)
#     print(f"Using corrected name: {corrected}")
#     return corrected

# # Process papers
# corrected_papers = []
# for paper in data.get("papers", []):
#     # Check if paper has an ID
#     if not paper.get("id"):
#         print(f"Paper missing ID: {paper.get('title', 'Unknown title')}")
#         continue
    
#     # Check for duplicate IDs
#     if paper["id"] in unique_paper_ids:
#         print(f"Duplicate paper ID found: {paper['id']} - Skipping")
#         continue
    
#     # Add to unique IDs
#     unique_paper_ids.add(paper["id"])
    
#     # Check and correct year
#     if "year" in paper:
#         try:
#             paper["year"] = int(paper["year"])
#         except (ValueError, TypeError):
#             print(f"Invalid year for paper {paper['id']}: {paper.get('year')} - Setting to None")
#             paper["year"] = None
    
#     # Check and correct journal name
#     if "journal" in paper and paper["journal"]:
#         journal_lower = paper["journal"].lower()
#         if journal_lower in journal_mapping:
#             paper["journal"] = journal_mapping[journal_lower]
#         else:
#             # Get correct journal name (in a real app, this would prompt the user)
#             correct_journal = get_user_input_for_journal(paper["journal"])
#             journal_mapping[journal_lower] = correct_journal
#             paper["journal"] = correct_journal
    
#     # Add the corrected paper to our list
#     corrected_papers.append(paper)

# # Create the corrected JSON
# corrected_data = {"papers": corrected_papers}

# # Save the corrected JSON
# with open(output_file, 'w', encoding='utf-8') as f:
#     json.dump(corrected_data, f, indent=2, ensure_ascii=False)

# # Save unique paper IDs
# df_paper_ids = pd.DataFrame({"id": list(unique_paper_ids)})
# df_paper_ids.to_csv(unique_paper_id_file, index=False)

# # Save journal mappings
# df_journals = pd.DataFrame({
#     "lowercase_name": list(journal_mapping.keys()),
#     "correct_name": list(journal_mapping.values())
# })
# df_journals.to_csv(unique_journal_file, index=False)

# print(f"Processed {len(data.get('papers', []))} papers")
# print(f"Saved {len(corrected_papers)} papers to {output_file}")
# print(f"Saved {len(unique_paper_ids)} unique paper IDs to {unique_paper_id_file}")
# print(f"Saved {len(journal_mapping)} journal mappings to {unique_journal_file}")


# =================================
# Create first version to topic.csv
# =================================
# import json
# import pandas as pd

# # Read the JSON file
# with open('../data/databases/corrected_combined.json', 'r', encoding='utf-8') as f:
#     data = json.load(f)

# # Extract all topics
# all_topics = []
# for paper in data['papers']:
#     if 'topic' in paper:
#         all_topics.extend(paper['topic'])

# # Get unique topics
# unique_topics = list(set(all_topics))

# # Create a DataFrame with the unique topics
# df = pd.DataFrame({'name': unique_topics})

# # Save to CSV without index
# df.to_csv('../data/databases/unique_topic.csv', index=False)