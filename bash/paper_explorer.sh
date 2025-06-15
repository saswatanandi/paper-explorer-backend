#!/usr/bin/env bash

# Paper Explorer Management Script
# This script provides a menu to:
# 1. Run the Python script and upload data to GitHub
# 2. Only run the Python script
# 3. Only upload data to GitHub


# --- Configuration ---
# Determine directories relative to the script's new location
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
# The root of the backend-python-app repository
BACKEND_REPO_DIR=$(realpath "${SCRIPT_DIR}/..")
# The parent directory containing backend-python-app and paper-explorer-data
MAIN_DIR=$(realpath "${BACKEND_REPO_DIR}/..")

# Component Directories (adjust based on new MAIN_DIR and BACKEND_REPO_DIR)
PYTHON_APP_DIR="${BACKEND_REPO_DIR}" # This is now the root of the backend repo
DATA_REPO_DIR="${MAIN_DIR}/paper-explorer-data"
# BACKEND_REPO_DIR is already defined above

# Data Directories within Backend App
DATA_UPLOAD_DIR="${PYTHON_APP_DIR}/data/databases/upload" # Path relative to PYTHON_APP_DIR

# Conda Environment
CONDA_ENV_NAME="py24"
# Optional: Specify full path if needed, but activation by name is preferred
# CONDA_ENV_PATH="/home/sn/snd/soft/con/envs/py24"

# Git Configuration (remains the same)
DATA_REPO_REMOTE="origin"
DATA_REPO_BRANCH="main"
BACKEND_REPO_REMOTE="origin"
BACKEND_REPO_BRANCH="main"
DEFAULT_COMMIT_MSG_DATA="Update paper data"
DEFAULT_COMMIT_MSG_BACKEND="Update backend application"



# --- Color Codes ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color


# --- Helper Functions ---
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    local title=$1
    echo ""
    print_message "${BLUE}" "===================================================="
    print_message "${BLUE}" "  ${title}"
    print_message "${BLUE}" "===================================================="
}

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Function to activate conda environment
activate_conda() {
    print_message "${YELLOW}" "Activating conda environment '${CONDA_ENV_NAME}'..."
    if ! command_exists conda; then
        print_message "${RED}" "Error: conda command not found. Please ensure Anaconda/Miniconda is installed and in your PATH."
        return 1
    fi

    # Source conda initialization script
    # Using `conda info --base` is more robust than hardcoding path
    local CONDA_BASE_DIR
    CONDA_BASE_DIR=$(conda info --base)
    if [ -z "$CONDA_BASE_DIR" ]; then
         print_message "${RED}" "Error: Could not determine Conda base directory."
         return 1
    fi
    source "${CONDA_BASE_DIR}/etc/profile.d/conda.sh" || {
        print_message "${RED}" "Error: Failed to source conda profile script."
        return 1
    }

    conda activate "${CONDA_ENV_NAME}"
    if [ $? -ne 0 ]; then
        print_message "${RED}" "Error: Failed to activate conda environment '${CONDA_ENV_NAME}'."
        # Attempt to provide more info if env doesn't exist
        if ! conda env list | grep -q "${CONDA_ENV_NAME}"; then
             print_message "${YELLOW}" "Environment '${CONDA_ENV_NAME}' not found. You might need to create it using 'setup_project.sh' or 'conda env create -f ${BACKEND_REPO_DIR}/environment.yml'."
        fi
        return 1
    fi
    print_message "${GREEN}" "Conda environment '${CONDA_ENV_NAME}' activated successfully."
    return 0
    
}


# Function to deactivate conda environment
deactivate_conda() {
    if command_exists conda; then
        conda deactivate
        print_message "${YELLOW}" "Conda environment deactivated."
    fi
}


# --- Core Functions ---

# Function to run Python script
run_python_script() {
    print_header "Running Python Script (run.py)"
    if [ ! -d "${PYTHON_APP_DIR}/scripts" ]; then
        print_message "${RED}" "Error: Python scripts directory not found: ${PYTHON_APP_DIR}/scripts"
        return 1
    fi
    cd "${PYTHON_APP_DIR}/scripts" || return 1

    activate_conda || return 1

    if [ ! -f "run.py" ]; then
        print_message "${RED}" "Error: run.py not found in ${PYTHON_APP_DIR}/scripts"
        deactivate_conda
        return 1
    fi

    print_message "${YELLOW}" "Executing run.py..."
    python run.py
    local exit_code=$?

    deactivate_conda # Deactivate after script finishes or fails

    if [ $exit_code -ne 0 ]; then
        print_message "${RED}" "Error: Python script execution failed with exit code ${exit_code}."
        return 1
    fi

    print_message "${GREEN}" "Python script executed successfully."
    return 0
}


# Function to check for new data files and copy them
check_and_copy_new_data() {
    print_message "${YELLOW}" "Checking for new data files in ${DATA_UPLOAD_DIR}..."
    if [ ! -d "${DATA_UPLOAD_DIR}" ]; then
        print_message "${RED}" "Error: Upload directory not found: ${DATA_UPLOAD_DIR}"
        return 1
    fi
    local data_repo_papers_dir="${DATA_REPO_DIR}/papers"
    if [ ! -d "${data_repo_papers_dir}" ]; then
        print_message "${YELLOW}" "Creating 'papers' directory in data repository: ${data_repo_papers_dir}"
        mkdir -p "${data_repo_papers_dir}" || {
            print_message "${RED}" "Error: Failed to create papers directory."
            return 1
        }
    fi

    local upload_files
    upload_files=$(find "${DATA_UPLOAD_DIR}" -maxdepth 1 -name '*.json.gz' -print0 | xargs -0 ls -t 2>/dev/null)
    if [ -z "$upload_files" ]; then
        print_message "${YELLOW}" "No .json.gz files found in upload directory."
        return 0 # Not an error, just nothing to copy
    fi

    local copy_count=0
    # Use process substitution and read loop for safer filename handling
    while IFS= read -r file; do
        local filename
        filename=$(basename "$file")
        local dest_file="${data_repo_papers_dir}/${filename}"

        # Copy if destination doesn't exist or source is newer
        if [ ! -f "${dest_file}" ] || [ "$file" -nt "${dest_file}" ]; then
            print_message "${YELLOW}" "Copying ${filename} to data repository..."
            cp "$file" "${dest_file}" || {
                print_message "${RED}" "Error: Failed to copy ${filename}."
                # Decide whether to continue or stop on copy error
                # return 1 # Stop on first error
            }
            ((copy_count++))
        fi
    done <<< "$upload_files" # Feed find results into the loop

    if [ $copy_count -eq 0 ]; then
        print_message "${YELLOW}" "Data repository 'papers' directory is already up-to-date."
    else
        print_message "${GREEN}" "Copied ${copy_count} new/updated file(s) to data repository."
    fi
    return 0
}

# Function to update index.json file in the data repo
update_index_json() {
    print_message "${YELLOW}" "Updating index.json in ${DATA_REPO_DIR}..."
    cd "${DATA_REPO_DIR}" || return 1

    local papers_dir="papers"
    if [ ! -d "$papers_dir" ]; then
         print_message "${RED}" "Error: 'papers' directory not found in ${DATA_REPO_DIR}."
         return 1
    fi

    # Find files, sort them (optional, but nice), and count
    local files_list
    files_list=$(find "$papers_dir" -maxdepth 1 -name '*.json.gz' -printf '"%p"\n' | sort)
    local file_count
    file_count=$(echo "$files_list" | grep -c .) # Count non-empty lines

    if [ "$file_count" -eq 0 ]; then
        print_message "${YELLOW}" "Warning: No .json.gz files found in ${papers_dir}. index.json will be empty."
        files_json="[]"
    else
        # Join files with comma separator and wrap in brackets
        files_json=$(echo "$files_list" | paste -sd ',' | sed 's/^/[/' | sed 's/$/]/')
    fi

    local today
    today=$(date +"%Y-%m-%d")

    # Create the new index.json content using printf for better formatting control
    printf '{\n  "files": %s,\n  "totalCount": %d,\n  "lastUpdated": "%s"\n}\n' \
        "${files_json}" "${file_count}" "${today}" > index.json

    if [ $? -ne 0 ]; then
        print_message "${RED}" "Error: Failed to write index.json."
        return 1
    fi

    print_message "${GREEN}" "index.json updated successfully (${file_count} file(s))."
    return 0
}


# Generic function to commit and push changes in a Git repository
commit_and_push_repo() {
    local repo_dir="$1"
    local repo_name="$2" # User-friendly name (e.g., "Data Repo", "Backend Repo")
    local remote="$3"
    local branch="$4"
    local default_commit_msg="$5"

    # Add today's date to the default commit message
    local today
    today=$(date +"%Y-%m-%d")
    default_commit_msg="${default_commit_msg} [${today}]"    

    print_header "Syncing ${repo_name} with GitHub"
    cd "${repo_dir}" || return 1

    if ! command_exists git; then
        print_message "${RED}" "Error: git command not found."
        return 1
    fi
    if [ ! -d ".git" ]; then
        print_message "${RED}" "Error: ${repo_dir} is not a git repository."
        return 1
    fi

    # Fetch latest changes
    print_message "${YELLOW}" "Fetching latest changes from ${remote}/${branch}..."
    git fetch "${remote}" "${branch}"
    if [ $? -ne 0 ]; then
        print_message "${RED}" "Error: Git fetch failed for ${repo_name}."
        # Consider if this should be a fatal error
    fi

    # Check for changes
    if git diff --quiet HEAD --; then
        if git diff --quiet --cached --; then
             print_message "${GREEN}" "${repo_name}: No local changes to commit."
             # Check if local is behind remote
             local local_hash=$(git rev-parse HEAD)
             local remote_hash=$(git rev-parse ${remote}/${branch})
             if [ "$local_hash" != "$remote_hash" ]; then
                 if git merge-base --is-ancestor HEAD ${remote}/${branch}; then
                     print_message "${YELLOW}" "${repo_name}: Local branch is behind remote. Consider pulling changes."
                 elif git merge-base --is-ancestor ${remote}/${branch} HEAD; then
                      print_message "${YELLOW}" "${repo_name}: Local branch is ahead of remote. Pushing..."
                      # Proceed to push if needed (e.g., if previous push failed but commit succeeded)
                 else
                      print_message "${YELLOW}" "${repo_name}: Local and remote branches have diverged. Manual merge/rebase needed."
                      # return 1 # Or let push fail later
                 fi
             fi
             # If no changes and up-to-date, we can often skip the push.
             # However, let's try pushing anyway in case a previous push failed.
             # return 0 # Exit early if no changes
        fi
    fi


    print_message "${YELLOW}" "${repo_name}: Changes detected."
    git status -s # Short status

    read -p "$(echo -e "${YELLOW}Proceed with committing and pushing changes for ${repo_name}? (y/n): ${NC}")" proceed
    if [[ ! "$proceed" =~ ^[Yy]$ ]]; then
        print_message "${YELLOW}" "Skipping GitHub sync for ${repo_name}."
        return 0 # User chose not to proceed
    fi

    print_message "${YELLOW}" "Adding all changes in ${repo_name}..."
    git add .

    # Check again if anything was actually staged
    if git diff --quiet --cached --; then
        print_message "${YELLOW}" "${repo_name}: No changes staged for commit (perhaps only ignored files changed)."
        # Check if we need to push unpushed commits
        if ! git diff --quiet ${remote}/${branch} HEAD; then
             print_message "${YELLOW}" "${repo_name}: Local commits exist that are not on remote. Attempting push..."
             # Fall through to push logic
        else
             return 0 # Nothing to commit or push
        fi
    else
        print_message "${YELLOW}" "Committing changes in ${repo_name}..."
        read -p "$(echo -e "${YELLOW}Enter commit message (default: '${default_commit_msg}'): ${NC}")" commit_message
        commit_message=${commit_message:-"${default_commit_msg}"}
        git commit -m "${commit_message}"
        if [ $? -ne 0 ]; then
            print_message "${RED}" "Error: Git commit failed for ${repo_name}."
            return 1
        fi
    fi


    print_message "${YELLOW}" "Pushing ${repo_name} to ${remote}/${branch}..."
    git push "${remote}" "${branch}"
    local push_exit_code=$?

    if [ $push_exit_code -ne 0 ]; then
        print_message "${RED}" "Error: Git push failed for ${repo_name} (Code: ${push_exit_code})."
        print_message "${YELLOW}" "Attempting to pull changes and push again..."
        git pull "${remote}" "${branch}" --rebase # Use rebase to avoid merge commits for simple updates
        local pull_exit_code=$?
        if [ $pull_exit_code -ne 0 ]; then
             print_message "${RED}" "Error: Git pull failed. Please resolve conflicts manually in ${repo_dir}."
             return 1
        fi
        # Try pushing again after pull
        git push "${remote}" "${branch}"
        if [ $? -ne 0 ]; then
            print_message "${RED}" "Error: Git push failed again after pull. Please resolve conflicts manually in ${repo_dir}."
            return 1
        fi
    fi

    print_message "${GREEN}" "${repo_name} successfully synced with GitHub."
    return 0
}


# Function to upload data repo changes to GitHub
upload_data_to_github() {
    print_header "Preparing Data Repository"
    check_and_copy_new_data || return 1
    update_index_json || return 1
    commit_and_push_repo "${DATA_REPO_DIR}" "Data Repo" "${DATA_REPO_REMOTE}" "${DATA_REPO_BRANCH}" "${DEFAULT_COMMIT_MSG_DATA}"
    return $? # Return the exit status of the commit/push
}

# Function to upload backend repo changes to GitHub
upload_backend_to_github() {
    # No data prep needed here, just commit/push existing changes
    commit_and_push_repo "${BACKEND_REPO_DIR}" "Backend Repo" "${BACKEND_REPO_REMOTE}" "${BACKEND_REPO_BRANCH}" "${DEFAULT_COMMIT_MSG_BACKEND}"
    return $? # Return the exit status of the commit/push
}


# --- Main Menu ---
main() {
    clear
    print_header "Paper Explorer Management Script"
    echo " Main Project Directory: ${MAIN_DIR}"
    echo " Python App Directory: ${PYTHON_APP_DIR}"
    echo " Data Repo Directory:  ${DATA_REPO_DIR}"
    echo " Conda Environment:    ${CONDA_ENV_NAME}"
    echo ""
    print_message "${YELLOW}" "Select an option:"
    echo ""
    print_message "${GREEN}" " 1. Run Python script -> Upload Data Repo -> Upload Backend Repo"
    print_message "${GREEN}" " 2. Run Python script Only"
    print_message "${GREEN}" " 3. Upload Data Repo Only"
    print_message "${GREEN}" " 4. Upload Backend Repo Only"
    print_message "${GREEN}" " 5. Upload Both Data Repo and Backend Repo"
    print_message "${RED}"   " 6. Exit"
    echo ""
    print_message "${BLUE}" "===================================================="

    local choice
    read -p "$(echo -e "${YELLOW}Enter your choice (1-6): ${NC}")" choice

    case $choice in
        1)
            run_python_script
            local run_status=$?
            if [ $run_status -eq 0 ]; then
                upload_data_to_github
                local data_upload_status=$?
                # Optionally, only upload backend if data upload was ok, or always try
                # if [ $data_upload_status -eq 0 ]; then
                    upload_backend_to_github
                # fi
            else
                print_message "${RED}" "Skipping GitHub uploads due to Python script failure."
            fi
            ;;
        2)
            run_python_script
            ;;
        3)
            upload_data_to_github
            ;;
        4)
            upload_backend_to_github
            ;;
        5)
            upload_data_to_github
            upload_backend_to_github
            ;;
        6)
            print_message "${YELLOW}" "Exiting script."
            exit 0
            ;;
        *)
            print_message "${RED}" "Invalid option. Please select 1-6."
            sleep 2
            main # Show menu again
            ;;
    esac

    echo ""
    print_message "${BLUE}" "===================================================="
    read -p "$(echo -e "${YELLOW}Press Enter to return to the menu or Ctrl+C to exit.${NC}")"
    main # Loop back to menu after action completes
}

# --- Script Execution ---
# Ensure we are in the script's directory initially if needed, though paths are absolute
# cd "${SCRIPT_DIR}"

# Execute main function
main