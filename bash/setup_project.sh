
#!/usr/bin/env bash

# Paper Explorer Project Setup Script
# Clones repositories and sets up the Conda environment.

# --- Configuration ---
# Base directory where the project will be cloned
# Default: Current directory where the script is run
TARGET_PARENT_DIR="."
# Name of the main project folder to be created
PROJECT_FOLDER_NAME="10_paper_explorer"

# GitHub User/Organization
GITHUB_USER="saswatanandi"

# Repository Names
FRONTEND_REPO="paper-explorer"
DATA_REPO="paper-explorer-data"
BACKEND_REPO="paper-explorer-backend" # Use the actual name you created

# Conda Environment Name (should match environment.yml if specified there)
CONDA_ENV_NAME="py24"

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

# --- Setup Steps ---

# 1. Check Prerequisites
print_header "Checking Prerequisites"
if ! command_exists git; then
    print_message "${RED}" "Error: Git is not installed. Please install Git and run this script again."
    exit 1
fi
if ! command_exists conda; then
    print_message "${RED}" "Error: Conda is not installed. Please install Anaconda or Miniconda and run this script again."
    exit 1
fi
print_message "${GREEN}" "Git and Conda found."

# 2. SSH Key Confirmation and Alias Input
print_header "GitHub SSH Configuration"
print_message "${YELLOW}" "This script assumes you have configured an SSH key for GitHub."
print_message "${YELLOW}" "Refer to your project's readme.txt or GitHub documentation for instructions."
print_message "${YELLOW}" "You need to know the SSH 'Host' alias you defined in your ~/.ssh/config"
print_message "${YELLOW}" "(e.g., git-saswatanandi in the example config)."
print_message "${YELLOW}" "(more info on https://github.com/iamsaswata/utils/blob/master/notes/github.md)."
echo ""
read -p "$(echo -e "${YELLOW}Enter the SSH Host alias for GitHub (e.g., git-saswatanandi): ${NC}")" GIT_SSH_ALIAS
if [ -z "${GIT_SSH_ALIAS}" ]; then
    print_message "${RED}" "Error: SSH Host alias cannot be empty."
    exit 1
fi
print_message "${GREEN}" "Using SSH alias: ${GIT_SSH_ALIAS}"
# Optional: Add a test connection here
# print_message "${YELLOW}" "Testing SSH connection..."
# ssh -T git@${GIT_SSH_ALIAS} || { print_message "${RED}" "SSH connection test failed. Check your ~/.ssh/config and key setup."; exit 1; }


# 3. Define Target Directory
TARGET_DIR="${TARGET_PARENT_DIR}/${PROJECT_FOLDER_NAME}"
print_header "Project Directory Setup"
if [ -d "${TARGET_DIR}" ]; then
    print_message "${YELLOW}" "Warning: Target directory ${TARGET_DIR} already exists."
    read -p "$(echo -e "${YELLOW}Do you want to continue (potentially overwriting files)? (y/n): ${NC}")" proceed
    if [[ ! "$proceed" =~ ^[Yy]$ ]]; then
        print_message "${RED}" "Setup aborted by user."
        exit 1
    fi
else
    print_message "${YELLOW}" "Creating project directory: ${TARGET_DIR}"
    mkdir -p "${TARGET_DIR}" || {
        print_message "${RED}" "Error: Failed to create directory ${TARGET_DIR}."
        exit 1
    }
fi
cd "${TARGET_DIR}" || exit 1
MAIN_DIR=$(pwd) # Set MAIN_DIR to the absolute path

# 4. Clone Repositories
print_header "Cloning Repositories"

# Frontend Repo
print_message "${YELLOW}" "Cloning ${FRONTEND_REPO}..."
git clone "git@${GIT_SSH_ALIAS}:${GITHUB_USER}/${FRONTEND_REPO}.git" "${FRONTEND_REPO}" || {
    print_message "${RED}" "Error: Failed to clone ${FRONTEND_REPO}."
    exit 1
}

# Data Repo
print_message "${YELLOW}" "Cloning ${DATA_REPO}..."
git clone "git@${GIT_SSH_ALIAS}:${GITHUB_USER}/${DATA_REPO}.git" "${DATA_REPO}" || {
    print_message "${RED}" "Error: Failed to clone ${DATA_REPO}."
    exit 1
}

# Backend Repo
print_message "${YELLOW}" "Cloning ${BACKEND_REPO}..."
git clone "git@${GIT_SSH_ALIAS}:${GITHUB_USER}/${BACKEND_REPO}.git" "backend-python-app" || {
    print_message "${RED}" "Error: Failed to clone ${BACKEND_REPO}."
    exit 1
}
print_message "${GREEN}" "All repositories cloned successfully."

# 5. Setup Conda Environment
print_header "Setting up Conda Environment"
BACKEND_APP_DIR="${MAIN_DIR}/backend-python-app"
ENV_FILE="${BACKEND_APP_DIR}/environment.yml"

if [ ! -f "${ENV_FILE}" ]; then
    print_message "${RED}" "Error: environment.yml not found in ${BACKEND_APP_DIR}."
    print_message "${YELLOW}" "Skipping Conda environment creation. Please create it manually."
else
    print_message "${YELLOW}" "Creating Conda environment '${CONDA_ENV_NAME}' from ${ENV_FILE}..."
    # Check if env already exists
    if conda env list | grep -q "^${CONDA_ENV_NAME}\s"; then
         print_message "${YELLOW}" "Conda environment '${CONDA_ENV_NAME}' already exists."
         read -p "$(echo -e "${YELLOW}Do you want to remove the existing environment and recreate it? (y/n): ${NC}")" recreate_env
         if [[ "$recreate_env" =~ ^[Yy]$ ]]; then
              print_message "${YELLOW}" "Removing existing environment..."
              conda env remove -n "${CONDA_ENV_NAME}" -y || {
                   print_message "${RED}" "Failed to remove existing environment. Please remove it manually ('conda env remove -n
${CONDA_ENV_NAME}') and rerun setup."
                   exit 1
              }
              print_message "${YELLOW}" "Recreating environment..."
              conda env create -f "${ENV_FILE}" -n "${CONDA_ENV_NAME}" || {
                   print_message "${RED}" "Error: Failed to create Conda environment '${CONDA_ENV_NAME}'. Check ${ENV_FILE} and conda logs."
                   exit 1
              }
         else
              print_message "${YELLOW}" "Skipping environment creation. Using existing environment."
         fi
    else
        # Create the environment
        conda env create -f "${ENV_FILE}" -n "${CONDA_ENV_NAME}" || {
            print_message "${RED}" "Error: Failed to create Conda environment '${CONDA_ENV_NAME}'. Check ${ENV_FILE} and conda logs."
            exit 1
        }
    fi
    print_message "${GREEN}" "Conda environment '${CONDA_ENV_NAME}' setup complete."
    print_message "${YELLOW}" "Activate it using: conda activate ${CONDA_ENV_NAME}"
fi


# 6. Setup Alias (Optional)
print_header "Setup Bash Alias (Optional)"
BASH_SCRIPT_PATH="${MAIN_DIR}/${PROJECT_FOLDER_NAME}/backend-python-app/bash/paper_explorer.sh" # Updated path
ALIAS_NAME="paper-explorer"
RC_FILE="$HOME/.bashrc" # Or detect .zshrc, .profile etc.

if [ -f "$BASH_SCRIPT_PATH" ]; then
    print_message "${YELLOW}" "Do you want to add the '${ALIAS_NAME}' alias to your ${RC_FILE}?"
    read -p "$(echo -e "${YELLOW}This will allow you to run the management script by typing '${ALIAS_NAME}'. (y/n): ${NC}")" add_alias
    if [[ "$add_alias" =~ ^[Yy]$ ]]; then
        # Check if alias already exists
        if grep -q "alias ${ALIAS_NAME}=" "${RC_FILE}"; then
            print_message "${YELLOW}" "Alias '${ALIAS_NAME}' already exists in ${RC_FILE}. Skipping."
        else
            print_message "${YELLOW}" "Adding alias to ${RC_FILE}..."
            echo "" >> "${RC_FILE}" # Add a newline for separation
            echo "# Alias for Paper Explorer project" >> "${RC_FILE}"
            # Make sure the path is correct and quoted if it contains spaces
            echo "alias ${ALIAS_NAME}='${BASH_SCRIPT_PATH}'" >> "${RC_FILE}"
            print_message "${GREEN}" "Alias added. Please run 'source ${RC_FILE}' or restart your terminal to use it."
        fi
    else
        print_message "${YELLOW}" "Skipping alias setup."
    fi
else
    print_message "${YELLOW}" "Management script not found at ${BASH_SCRIPT_PATH}. Skipping alias setup."
fi

# 7. Check for Google Chrome
print_message "${YELLOW}" "Checking for Google Chrome..."
print_message "${YELLOW}" "The backend scraping script need chrome at ~/chrome/opt/google/chrome/chrome"
if ! command_exists ~/chrome/opt/google/chrome/chrome; then
    print_message "${RED}" "Warning: Google Chrome (google-chrome-stable) not found in PATH."
    print_message "${YELLOW}" "The backend scraping script requires Google Chrome."
    print_message "${YELLOW}" "Please install it manually. On Debian/Ubuntu, you can usually run:"
    print_message "${YELLOW}" "  wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
    print_message "${YELLOW}" " ar x google-chrome-stable_current_amd64.deb"
    print_message "${YELLOW}" " tar -xf data.tar.xz"
    print_message "${YELLOW}" "Setup will continue, but the backend script may fail until Chrome is installed."
    read -p "$(echo -e "${YELLOW}Press Enter to acknowledge and continue...${NC}")"
else
    print_message "${GREEN}" "Google Chrome found."
fi


# 8. Final Instructions
print_header "Setup Complete!"
print_message "${GREEN}" "Project setup finished in: ${MAIN_DIR}"
print_message "${YELLOW}" "Next Steps:"
print_message "${YELLOW}" "1. If you added the alias, run 'source ${RC_FILE}' or restart your terminal."
print_message "${YELLOW}" "2. Activate the conda environment: conda activate ${CONDA_ENV_NAME}"
print_message "${YELLOW}" "3. Run the management script using the alias '${ALIAS_NAME}' (if set up) or directly: '${BASH_SCRIPT_PATH}'"
print_message "${YELLOW}" "4. Place your input .eml files in: ${BACKEND_APP_DIR}/data/eml/"
echo ""

exit 0