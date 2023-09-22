#!/usr/bin/env bash

# Load env vars
export $(grep -v '^#' .env | xargs)

rm -rf valory_chat_mas

make clean

autonomy packages lock

autonomy push-all

autonomy fetch --local --service algovera/valory_chat_mas && cd valory_chat_mas

# Build the image
autonomy build-image

# Copy keys and build the deployment
cp /home/marshath/play/openautonomy2/daios/keys.json ./keys.json

autonomy deploy build -ltm

# Run the deployment
autonomy deploy run --build-dir abci_build/