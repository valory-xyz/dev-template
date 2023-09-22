#!/usr/bin/env bash

# Load env vars
export $(grep -v '^#' .env | xargs)

rm -rf chat_completion_mas

make clean

autonomy packages lock

autonomy push-all

autonomy fetch --local --service algovera/chat_completion_mas && cd chat_completion_mas

# Build the image
autonomy build-image

# Copy keys and build the deployment
cp /home/marshath/play/openautonomy2/daios/keys.json ./keys.json

autonomy deploy build -ltm

# Run the deployment
autonomy deploy run --build-dir abci_build/