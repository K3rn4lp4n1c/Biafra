#!/bin/sh

# Loop through all the directories in the current directory
for dir in */; do
    # Check if the directory contains a compress.sh file
    if [ -f "$dir/compress.sh" ]; then
        echo "Compressing files in $dir"
        # Run the compress.sh script in the directory and copy the resulting tar.gz file to the current directory
        (cd "$dir" && ./compress.sh)
        mv "*.tar.gz" .
    else
        echo "No compress.sh found in $dir, skipping..."
    fi
done