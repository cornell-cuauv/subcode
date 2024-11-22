#!/bin/bash

# Ask the user to choose the base
echo "Choose the base:"
echo "1) jetson-base"
echo "2) local-base"
read -p "Enter the number (1 or 2): " base_choice

if [[ "$base_choice" == "1" ]]; then
    DOCKERFILE="Dockerfile.jetson"
    TAG_NAME="docker.cuauv.org/cuauv-jetson:master"
elif [[ "$base_choice" == "2" ]]; then
    DOCKERFILE="Dockerfile.local"
    
    # Ask the user to choose the tag for local-base
    echo "Choose the tag for local:"
    echo "1) aarch64"
    echo "2) x86_64"
    read -p "Enter the number (1 or 2): " tag_choice
    
    if [[ "$tag_choice" == "1" ]]; then
        TAG_NAME="docker.cuauv.org/cuauv-20-aarch64:master"
    elif [[ "$tag_choice" == "2" ]]; then
        TAG_NAME="docker.cuauv.org/cuauv-20-x86_64:master"
    else
        echo "Invalid choice for tag. Exiting."
        exit 1
    fi
else
    echo "Invalid choice for base docker image. Exiting."
    exit 1
fi

# Print the tag name for verification
echo "Using Dockerfile: $DOCKERFILE"
echo "Using tag name: $TAG_NAME"

# Wait 2 seconds
sleep 2

# Build the Docker image with the appropriate Dockerfile and tag name
docker build -f $DOCKERFILE -t $TAG_NAME .

