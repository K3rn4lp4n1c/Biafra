#!/bin/sh

# Loop through all the directories in the current directory
for dir in */; do
    # Check if the directory contains a build-docker.sh file
    if [ -f "$dir/build-docker.sh" ]; then
        echo "Building Docker image for $dir"
        # Run the build-docker.sh script in the directory
        (cd "$dir" && ./build-docker.sh)
    else
        echo "No build-docker.sh found in $dir, skipping..."
    fi
done