# Paper Explorer Project Documentation

This document outlines the structure, deployment process, and data management for the Paper Explorer web application and its associated backend Python scripts.

---

## 1. Web Application (Frontend)

This section covers the web application details, including hosting, deployment, Git configuration, and troubleshooting common deployment issues.

### Hosting & Deployment

* **Live URL:** https://saswatanandi.github.io/paper-explorer/
* **Source Code:** https://github.com/saswatanandi/paper-explorer
* **Deployment Method:** GitHub Pages (via GitHub Actions, triggered on push to `main` or manually).
* **Data Source:** Reads data from the paper-explorer-data repository (https://github.com/saswatanandi/paper-explorer-data).

**Pushing Updates to GitHub:**

# Add all changes
git add .

# Commit changes with a descriptive message
git commit -m "Your commit message here"

# Push changes to the main branch
git push origin main




Git Setup (Multiple Accounts)

Prerequisites:

Set the default branch name globally (optional but recommended):
git config --global init.defaultBranch main

Generate separate SSH key pairs for each GitHub account (e.g., id_ed25519_account1, id_ed25519_account2).

Add the public key (.pub file) of each pair to the corresponding GitHub account settings. (See: GitHub SSH Docs - https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account)

SSH Configuration (~/.ssh/config):

Create or edit your SSH config file (~/.ssh/config) to manage multiple identities:


# Default GitHub account (e.g., using id_rsa)

Host git-iamsaswata
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_rsa
  IdentitiesOnly yes

# Second GitHub account (saswatanandi)
Host git-saswatanandi
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519_git_saswatanandi_officepc # <-- Update with your key file name
  IdentitiesOnly yes


Testing SSH Connection:Test the connection for a specific account using its host alias:ssh -T git@git-saswatanandi

Expected success message: Hi saswatanandi! You've successfully authenticated, but GitHub does not provide shell access.

Configuring Remote Repository URL: When cloning or adding a remote, use the appropriate host alias defined in your ~/.ssh/config:# Example for the 'saswatanandi' account


git remote add origin git@git-saswatanandi:saswatanandi/paper-explorer.git
# Or if cloning: git clone git@git-saswatanandi:saswatanandi/paper-explorer.git


Deployment Troubleshooting
--------------------------

Here are solutions to common deployment issues encountered with Astro and Vite:

Issue 1: Vite Worker Build Format Error

Problem: Vite fails to build worker files (new Worker(new URL(...))) because the default output format (iife or umd) doesn't support code-splitting needed for workers. Error message: "UMD and IIFE output formats are not supported for code-splitting builds."

Solution: Explicitly configure Vite to use the esm format for workers in your Astro config file.

File: astro.config.mjs


import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// [https://astro.build/config](https://astro.build/config)
export default defineConfig({
  site: '[https://saswatanandi.github.io](https://saswatanandi.github.io)', // Your site URL
  base: '/paper-explorer',             // Your base path
  output: 'static',
  integrations: [react()],
  // Add Vite configuration for workers
  vite: {
    worker: {
      // Set worker output format to ES Module
      format: 'esm'
    }
  }
});



Issue 2: Styling Differences Between Local Dev and Production

Problem: Styles defined in global.css appear correctly locally but are missing or incorrect in the deployed version on GitHub Pages. This often happens when linking the CSS file directly using <link rel="stylesheet" href="/src/styles/global.css" /> in the layout. Astro's build process needs to import CSS to process, bundle, and optimize it correctly for production.

Solution: Import the global CSS file within the frontmatter script (---) of your main layout file. Astro will then handle its processing and injection.

File: src/layouts/Layout.astro (or your main layout file)

---
// Import the global CSS file here
import '../styles/global.css';

export interface Props {
  title: string;
}

const { title } = Astro.props;
const faviconUrl = `${import.meta.env.BASE_URL}favicon.svg`; // Correctly handle base path for favicon
---

<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width" />
    <link rel="icon" type="image/svg+xml" href={faviconUrl} />
    <meta name="generator" content={Astro.generator} />
    <title>{title}</title>
    </head>
  <body>
    <slot />
  </body>
</html>





2. Backend Python Application

This application processes .eml files containing Google Scholar alerts, scrapes paper details, manages a database, and prepares data for the web application.

Directory Structure

📦 backend-python-app
├── 📂 data
│   ├── 📂 eml             # Input: Email files (*.eml) downloaded from Gmail alerts
│   │   └── 📄 *.eml
│   └── 📂 databases       # Output: Processed data
│       ├── 📂 json        # Uncompressed yearly paper data
│       │   └── 📄 YYYY.json
│       ├── 📂 csv         # Supporting CSV files for data management
│       │   ├── 📄 avoid.csv            # Journals to exclude
│       │   ├── 📄 unique_paper_id.csv  # Hash-based unique paper identifiers
│       │   ├── 📄 unique_journal.csv   # Normalized unique journal names
│       │   └── 📄 unique_topic.csv     # Unique topics/keywords
│       └── 📂 upload      # Compressed data ready for GitHub data repository
│           └── 📄 YYYY.json.gz
└── 📂 scripts             # Python scripts for processing
    ├── 📄 run.py              # Main execution script
    ├── 📄 gscholarNoprint.py  # Google Scholar scraper (silent version)
    ├── 📄 gscholar.py         # Google Scholar scraper (verbose version, not essential for run.py)
    ├── 📄 csv_to_json.py      # Utility for data migration (likely not needed for regular runs)
    └── 📄 utility.py          # Helper functions (likely not needed for regular runs)

Script Functions

 - run.py:
  - Orchestrates the entire process.
  - Reads .eml files from the data/eml/ directory.
  - Uses gscholarNoprint.py to scrape paper details from Google Scholar based on information extracted from emails.
  - Performs deduplication using title/year hashes (unique_paper_id.csv).
  - Normalizes journal names (unique_journal.csv) and checks against the exclusion list (avoid.csv).
  - Saves processed paper data into yearly JSON files (data/databases/json/YYYY.json).
  - Compresses the final JSON databases (data/databases/upload/YYYY.json.gz) for upload.

 - gscholarNoprint.py / gscholar.py:
  - Contains the logic for web scraping Google Scholar search results and paper pages.
  - Uses libraries like nodriver (presumably) for browser automation.
  - Extracts metadata (title, authors, year, journal, abstract, citation counts, etc.).
  - Includes mechanisms to handle potential CAPTCHAs.
  - Manages browser instances and sessions.
  - gscholarNoprint.py is optimized for run.py by suppressing print statements.

Data Flow

1. Ingestion: Google Scholar alert emails are saved as .eml files in the data/eml/ directory.
2. Processing: run.py parses each .eml file.
3. Scraping: For each potential paper identified, gscholarNoprint.py is invoked to fetch detailed metadata from Google Scholar.
4. Validation & Normalization:
- Paper uniqueness is checked using a hash of the title and year (managed via unique_paper_id.csv).
- Journal names are normalized using unique_journal.csv.
- Papers from journals listed in avoid.csv are excluded.
5. Storage: Validated and enriched paper data is appended to the corresponding yearly JSON file in data/databases/json/.
6. Compression: After processing all emails, run.py compresses the yearly JSON files into .json.gz format in data/databases/upload/.
7. Upload: The compressed .json.gz files (and the index.json file described below) are manually uploaded/committed to the paper-explorer-data GitHub repository.



3. GitHub Data Repository

The central data store read by the live web application.

Repository URL: https://github.com/saswatanandi/paper-explorer-data

Repository Structure

📦 paper-explorer-data (root)
├── 📄 index.json          # Index file listing available data files and metadata
└── 📂 papers/             # Directory containing compressed paper data
    └── 📄 YYYY.json.gz    # Compressed data for each year (multiple files)


index.json File
- This file acts as a manifest for the web application, telling it which data files are available.
- Purpose: Allows the web app to dynamically discover and load the necessary data files without hardcoding filenames.
- Generation: This file needs to be created or updated manually (or potentially automated as part of the Python script) whenever new yearly data files are added or updated in the papers/ directory.

Example index.json:{
  "files": [
    "papers/2023.json.gz",
    "papers/2024.json.gz",
    "papers/2025.json.gz"
    // Add entries for each available year file
  ],
"totalCount": N, # N is number of YYYY.json.gz files
  "lastUpdated": "2025-04-10"  # date of today
}


Cross-platform settings (Linux + macOS)
--------------------------------------

Some settings may differ across machines. You can override them without editing code:

1) Conda environment name used by `bash/paper_explorer.sh`
   export PAPER_EXPLORER_CONDA_ENV="py25"

2) Chrome executable path used for Google Scholar scraping (`nodriver`)
   export PAPER_EXPLORER_BROWSER_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

This repository is there at local storeage (by doing git clone git@git-saswatanandi:saswatanandi/paper-explorer-data.git), at under current folder : 'paper-explorer-data'


There is alias created at .bashrc, so if i type the alias keyword (paper-explorer), it  activate this( This is a script locating at current directory (/mnt/d/work/coding/2025/10_paper_explorer) under bash sbdirectory with name paper_explorer.sh. It give me 3 optons to choose from.
1. Run  the run.py  and then upload the final data to github (need to create this, how to check and update the pa
per-explorer-data).
2. Only run run.py
3. Only upload the final data to github (need to create this, how to check and update the pa
per-explorer-data).

Remember curernt directory path is : /mnt/d/work/coding/2025/10_paper_explorer
it has these three subirectory; paper-explorer-data, bash and backend-python-app.


==================================

I need two things.

Currently, only paper-explorer-data is backedup in github, but not the repo backend-python-app (and its data), which is critical (if pc fails). Also it need to be updated (pushing to github) each time we execute the program same like  paper-explorer-data. 

second i need to setup this in a new pc, this will be multiple step. There should be a script to setup this also.

Create a well thought plan and then come up with the solutions for the two problem. Content of paper_explorer.sh is given below.

Have full freedom to restructure and other acitivities to make it robust and effective. Think also like removing hard coded part

======================================


<paper_explroer.sh>

#!/usr/bin/env bash

# Paper Explorer Management Script
# This script provides a menu to:
# 1. Run the Python script and upload data to GitHub
# 2. Only run the Python script
# 3. Only upload data to GitHub

# Constants
MAIN_DIR="/mnt/d/work/coding/2025/10_paper_explorer"
PYTHON_APP_DIR="${MAIN_DIR}/backend-python-app"
DATA_REPO_DIR="${MAIN_DIR}/paper-explorer-data"
DATA_UPLOAD_DIR="${PYTHON_APP_DIR}/data/databases/upload"
CONDA_ENV="py24"
CONDA_ENV_PATH="/home/sn/snd/soft/con/envs/py24"

# Color codes for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display messages with colors
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to display section header
print_header() {
    local title=$1
    echo ""
    print_message "${BLUE}" "===================================================="
    print_message "${BLUE}" "  ${title}"
    print_message "${BLUE}" "===================================================="
}

# Function to activate conda environment
activate_conda() {
    print_message "${YELLOW}" "Activating conda environment '${CONDA_ENV}'..."
    
    # Check if conda command is available
    if ! command -v conda &> /dev/null; then
        print_message "${RED}" "Error: conda command not found. Please ensure Anaconda/Miniconda is installed and in your PATH."
        return 1
    fi
    
    # Use source to ensure conda activate works in the script
    source "$(conda info --base)/etc/profile.d/conda.sh"
    conda activate "${CONDA_ENV}"
    
    if [ $? -ne 0 ]; then
        print_message "${RED}" "Error: Failed to activate conda environment '${CONDA_ENV}'."
        return 1
    fi
    
    print_message "${GREEN}" "Conda environment '${CONDA_ENV}' activated successfully."
    return 0
}

# Function to run Python script
run_python_script() {
    print_header "Running Python Script (run.py)"
    
    # Check if Python app directory exists
    if [ ! -d "${PYTHON_APP_DIR}" ]; then
        print_message "${RED}" "Error: Python application directory not found: ${PYTHON_APP_DIR}"
        return 1
    fi
    
    # Change to Python app directory
    cd "${PYTHON_APP_DIR}"/scripts || {
        print_message "${RED}" "Error: Failed to change to directory: ${PYTHON_APP_DIR}"
        return 1
    }
    
    # Activate conda environment
    activate_conda || return 1
    
    # Check if run.py exists
    if [ ! -f "run.py" ]; then
        print_message "${RED}" "Error: run.py not found in ${PYTHON_APP_DIR}"
        conda deactivate
        return 1
    fi
    
    # Run the Python script
    print_message "${YELLOW}" "Executing run.py..."
    python run.py
    
    # Check if Python script executed successfully
    if [ $? -ne 0 ]; then
        print_message "${RED}" "Error: Python script execution failed."
        conda deactivate
        return 1
    fi
    
    print_message "${GREEN}" "Python script executed successfully."
    conda deactivate
    return 0
}

# Function to check for new data files
check_for_new_data() {
    print_message "${YELLOW}" "Checking for new data files..."
    
    # Check if upload directory exists
    if [ ! -d "${DATA_UPLOAD_DIR}" ]; then
        print_message "${RED}" "Error: Upload directory not found: ${DATA_UPLOAD_DIR}"
        return 1
    fi
    
    # Check if papers directory exists in data repo
    if [ ! -d "${DATA_REPO_DIR}/papers" ]; then
        print_message "${YELLOW}" "Creating 'papers' directory in data repository..."
        mkdir -p "${DATA_REPO_DIR}/papers"
    fi
    
    # Get list of .json.gz files in upload directory
    local upload_files=($(ls -1 "${DATA_UPLOAD_DIR}"/*.json.gz 2>/dev/null))
    if [ ${#upload_files[@]} -eq 0 ]; then
        print_message "${YELLOW}" "No .json.gz files found in upload directory."
        return 0
    fi
    
    # Copy new files to papers directory in data repo
    local copy_count=0
    for file in "${upload_files[@]}"; do
        local filename=$(basename "$file")
        
        # Check if file exists and is newer than the one in papers directory
        if [ ! -f "${DATA_REPO_DIR}/papers/${filename}" ] || [ "$file" -nt "${DATA_REPO_DIR}/papers/${filename}" ]; then
            print_message "${YELLOW}" "Copying file: ${filename} to data repository..."
            cp "$file" "${DATA_REPO_DIR}/papers/${filename}"
            ((copy_count++))
        fi
    done
    
    if [ $copy_count -eq 0 ]; then
        print_message "${YELLOW}" "No new files to copy to data repository."
    else
        print_message "${GREEN}" "Copied ${copy_count} file(s) to data repository."
    fi
    
    return 0
}

# Function to update index.json file
update_index_json() {
    print_message "${YELLOW}" "Updating index.json file..."
    
    # Change to data repo directory
    cd "${DATA_REPO_DIR}" || {
        print_message "${RED}" "Error: Failed to change to directory: ${DATA_REPO_DIR}"
        return 1
    }
    
    # Count the number of .json.gz files in papers directory
    local file_count=$(ls -1 papers/*.json.gz 2>/dev/null | wc -l)
    if [ $? -ne 0 ] || [ $file_count -eq 0 ]; then
        print_message "${RED}" "Error: No .json.gz files found in papers directory."
        return 1
    fi
    
    # Get the list of files for index.json
    local files_json="["
    for file in papers/*.json.gz; do
        # Extract just the filename with path relative to repo root
        files_json+="\"${file}\","
    done
    # Remove the trailing comma and close the array
    files_json="${files_json%,}]"
    
    # Get current date in YYYY-MM-DD format
    local today=$(date +"%Y-%m-%d")
    
    # Create the new index.json content
    local index_content="{
  \"files\": ${files_json},
  \"totalCount\": ${file_count},
  \"lastUpdated\": \"${today}\"
}"
    
    # Write to index.json
    echo "${index_content}" > index.json
    
    print_message "${GREEN}" "index.json updated successfully with ${file_count} file(s)."
    return 0
}

# Function to upload to GitHub
upload_to_github() {
    print_header "Uploading Data to GitHub"
    
    # Copy new data files from upload directory to data repo
    check_for_new_data || return 1
    
    # Update index.json with current files
    update_index_json || return 1
    
    # Change to data repo directory
    cd "${DATA_REPO_DIR}" || {
        print_message "${RED}" "Error: Failed to change to directory: ${DATA_REPO_DIR}"
        return 1
    }
    
    # Check if git is installed
    if ! command -v git &> /dev/null; then
        print_message "${RED}" "Error: git command not found. Please ensure Git is installed."
        return 1
    fi
    
    # Check if it's a git repository
    if [ ! -d ".git" ]; then
        print_message "${RED}" "Error: ${DATA_REPO_DIR} is not a git repository."
        return 1
    fi
    
    # Fetch latest changes to avoid conflicts
    print_message "${YELLOW}" "Fetching latest changes from remote repository..."
    git fetch origin
    
    # Check if there are any changes to commit
    local changes=$(git status --porcelain)
    if [ -z "$changes" ]; then
        print_message "${YELLOW}" "No changes to commit. Everything is up to date."
        return 0
    fi
    
    # Show status
    print_message "${YELLOW}" "Changes detected in the repository:"
    git status
    
    # Ask user if they want to proceed with the update
    read -p "$(echo -e "${YELLOW}Proceed with committing and pushing changes? (y/n): ${NC}")" proceed
    if [[ ! "$proceed" =~ ^[Yy]$ ]]; then
        print_message "${YELLOW}" "Upload canceled by user."
        return 0
    fi
    
    # Add all changes
    print_message "${YELLOW}" "Adding changes..."
    git add .
    
    # Commit changes
    print_message "${YELLOW}" "Committing changes..."
    read -p "$(echo -e "${YELLOW}Enter commit message (default: 'Update paper data'): ${NC}")" commit_message
    commit_message=${commit_message:-"Update paper data"}
    git commit -m "${commit_message}"
    
    # Check if commit successful
    if [ $? -ne 0 ]; then
        print_message "${RED}" "Error: Git commit failed."
        return 1
    fi
    
    # Push changes
    print_message "${YELLOW}" "Pushing to GitHub..."
    git push origin main
    
    # Check if push successful
    if [ $? -ne 0 ]; then
        print_message "${RED}" "Error: Git push failed."
        print_message "${YELLOW}" "Trying to pull changes first and then push..."
        
        # Pull changes if push failed
        git pull origin main
        
        # Try pushing again
        git push origin main
        
        if [ $? -ne 0 ]; then
            print_message "${RED}" "Error: Git push failed again. Please resolve conflicts manually."
            return 1
        fi
    fi
    
    print_message "${GREEN}" "Data successfully uploaded to GitHub."
    return 0
}

# Main function to display menu and handle user selection
main() {
    clear
    print_header "Paper Explorer Management Script"
    echo ""
    print_message "${YELLOW}" "Select an option:"
    echo ""
    print_message "${GREEN}" "1. Run Python script and upload data to GitHub"
    print_message "${GREEN}" "2. Only run Python script"
    print_message "${GREEN}" "3. Only upload data to GitHub"
    print_message "${RED}" "4. Exit"
    echo ""
    print_message "${BLUE}" "=============================================="
    
    read -p "$(echo -e "${YELLOW}Enter your choice (1-4): ${NC}")" choice
    
    case $choice in
        1)
            run_python_script
            if [ $? -eq 0 ]; then
                upload_to_github
            else
                print_message "${RED}" "Skipping upload due to Python script failure."
            fi
            ;;
        2)
            run_python_script
            ;;
        3)
            upload_to_github
            ;;
        4)
            print_message "${YELLOW}" "Exiting script."
            exit 0
            ;;
        *)
            print_message "${RED}" "Invalid option. Please select 1-4."
            sleep 2
            main
            ;;
    esac
    
    echo ""
    print_message "${BLUE}" "=============================================="
    print_message "${YELLOW}" "Script execution completed."
    print_message "${BLUE}" "=============================================="
}

# Execute main function
main

</paper_explorer.sh>
