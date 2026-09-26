#!/bin/bash

# Tapo P115 Control .rpm builder wrapper
# This script ensures dependencies are installed before running build_rpm.py

set -e

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "Checking build dependencies..."

# Check for python3
if ! command_exists python3; then
    echo "python3 not found. Installing..."
    sudo dnf install -y python3
else
    echo "python3 is already installed."
fi

# Check for python3-pip
if ! python3 -m pip --version >/dev/null 2>&1; then
    echo "python3-pip not found. Installing..."
    sudo dnf install -y python3-pip
else
    echo "python3-pip is already installed."
fi

# Check for rpmbuild (part of rpm-build package)
if ! command_exists rpmbuild; then
    echo "rpmbuild not found. Installing rpm-build..."
    sudo dnf install -y rpm-build
else
    echo "rpmbuild is already installed."
fi

# Check if build_rpm.py exists in the current directory
if [ ! -f "build_rpm.py" ]; then
    echo "Error: build_rpm.py not found in the current directory."
    exit 1
fi

echo "All dependencies checked. Running build_rpm.py..."
python3 build_rpm.py

if [ $? -eq 0 ]; then
    echo "Build completed successfully."
else
    echo "Build failed."
    exit 1
fi
