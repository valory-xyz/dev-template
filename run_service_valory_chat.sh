#!/usr/bin/env bash
# Load env vars
export $(grep -v '^#' .env | xargs)

echo "OPENAI_API_KEY = $OPENAI_API_KEY"

make clean

autonomy push-all

rm -rf ./valory_chat_local

autonomy fetch --local --service algovera/valory_chat_local && cd valory_chat_local

# Build the image
autonomy build-image

# Copy keys and build the deployment
cp /home/marshath/play/openautonomy2/keys.json ./keys.json

autonomy deploy build -ltm

# Run the deployment
autonomy deploy run --build-dir abci_build/