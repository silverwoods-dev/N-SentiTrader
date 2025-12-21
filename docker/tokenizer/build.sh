#!/bin/bash
# build.sh - Build the tokenizer docker image

IMAGE_NAME="n-sentitrader-tokenizer"
TAG="latest"

echo "Building $IMAGE_NAME:$TAG..."

docker build -t $IMAGE_NAME:$TAG -f docker/tokenizer/Dockerfile .

echo "Build completed."
