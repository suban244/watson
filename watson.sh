#!/bin/bash

# Directory to navigate to
TARGET_DIR="$HOME/Documents/watson"

# Navigate to the directory
cd "$TARGET_DIR" || { echo "Failed to navigate to $TARGET_DIR"; exit 1; }

# Start a new tmux session named "watson" with the first window
tmux new-session -d -s watson -n "docker"

# Create three additional windows (tabs)
tmux new-window -t watson:2 -n "python"
tmux new-window -t watson:3 -n "watson-tui"

# Tab 1
tmux send-keys -t watson:1 "make prod" C-m
# Tab 3
tmux send-keys -t watson:3 "cd watson-tui" C-m

# Switch back to the first tab
tmux select-window -t watson:1

# Attach to the session
tmux attach-session -t watson
