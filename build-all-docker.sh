#!/bin/sh

PUSH=false
while getopts "p" opt; do
  case $opt in
    p)
      PUSH=true
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
  esac
done

# Loop through all the directories in the current directory
for dir in */; do
    # Check if the directory contains a build-docker.sh file
    if [ -f "$dir/build-docker.sh" ]; then
        echo "Building Docker image for $dir"
        # Run the build-docker.sh script in the directory and pass the -p option if PUSH is true
        if [ "$PUSH" = true ]; then
            (cd "$dir" && ./build-docker.sh -p)
        else
            (cd "$dir" && ./build-docker.sh)
        fi
    else
        echo "No build-docker.sh found in $dir, skipping..."
    fi
done