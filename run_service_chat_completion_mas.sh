#!/usr/bin/env bash

# Load env vars
export $(grep -v '^#' .env | xargs)

echo "OPENAI_API_KEY = $OPENAI_API_KEY"

rm -rf chat_completion_mas

make clean

autonomy push-all

echo "Pushed all"

autonomy fetch --local --service algovera/chat_completion_mas && cd chat_completion_mas

echo "Fetched chat_completion_mas"

# Build the image
autonomy build-image

# Copy keys and build the deployment
cp /home/marshath/play/openautonomy2/daios/keys.json ./keys.json

autonomy deploy build -ltm

# Run the deployment
autonomy deploy run --build-dir abci_build/