#!/bin/bash

# Tapo P115 Control .deb builder wrapper
# This script ensures dependencies are installed before running build_deb.py

set -e

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "Checking build dependencies..."

# Check for python3
if ! command_exists python3; then
    echo "python3 not found. Installing..."
    sudo apt-get update && sudo apt-get install -y python3
else
    echo "python3 is already installed."
fi

# Check for python3-pip
if ! python3 -m pip --version >/dev/null 2>&1; then
    echo "python3-pip not found. Installing..."
    sudo apt-get update && sudo apt-get install -y python3-pip
else
    echo "python3-pip is already installed."
fi

# Check for dpkg-deb (usually part of dpkg package, but let's be sure)
if ! command_exists dpkg-deb; then
    echo "dpkg-deb not found. Installing dpkg..."
    sudo apt-get update && sudo apt-get install -y dpkg
else
    echo "dpkg-deb is already installed."
fi

# Check if build_deb.py exists in the current directory
if [ ! -f "build_deb.py" ]; then
    echo "Error: build_deb.py not found in the current directory."
    exit 1
fi

echo "All dependencies checked. Running build_deb.py..."
python3 build_deb.py

if [ $? -eq 0 ]; then
    echo "Build completed successfully."
else
    echo "Build failed."
    exit 1
fi
