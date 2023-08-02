#!/usr/bin/env bash

# Load env vars
export $(grep -v '^#' .env | xargs)

make clean

autonomy push-all

autonomy fetch --local --service algovera/chat_completion_local && cd chat_completion_local

# Build the image
autonomy build-image

# Copy keys and build the deployment
cp /home/david/Cloud/env/governatooorr/governatooorr_1_key.json ./keys.json

autonomy deploy build -ltm

# Run the deployment
autonomy deploy run --build-dir abci_build/