#!/usr/bin/env bash

# Define job parameters
JOB_IDENTIFIER="FPL_Update"
PY_PATH="/home/kumar/Media/Obsidian-Vault/_bin/_manDB/FPL/.venv/bin/python3"
SCRIPT_PATH="/home/kumar/Media/Obsidian-Vault/_bin/_manDB/FPL/fantasy.py" # ⚠️ Update this to your actual file path
ANACRON_TAB="/etc/anacrontab"

# Format: period_in_days  delay_in_minutes  job-identifier  command
# This runs daily (1) with a 10-minute delay after system boot using system Python
JOB_LINE="1	10	$JOB_IDENTIFIER	$PY_PATH $SCRIPT_PATH"

# Ensure the script is run with root privileges
if [ "$EUID" -ne 0 ]; then
    echo "Error: Please run this script as root or using sudo." >&2
    exit 1
fi

# Ensure the anacrontab file exists
if [ ! -f "$ANACRON_TAB" ]; then
    echo "Error: $ANACRON_TAB not found. Is anacron installed?" >&2
    exit 1
fi

# Verify the Python script actually exists before adding it
if [ ! -f "$SCRIPT_PATH" ]; then
    echo "Warning: Python script not found at $SCRIPT_PATH."
    echo "Please update the SCRIPT_PATH variable inside this installer script."
fi

# Check if the job identifier already exists in the file
if grep -q "[[:space:]]$JOB_IDENTIFIER[[:space:]]" "$ANACRON_TAB"; then
    echo "Anacron job '$JOB_IDENTIFIER' already exists. Skipping."
else
    # Append the job line to the end of the file safely
    echo -e "\n$JOB_LINE" >> "$ANACRON_TAB"
    echo "Success: Anacron job '$JOB_IDENTIFIER' added to $ANACRON_TAB."
fi
