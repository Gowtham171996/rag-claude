#!/bin/bash

# Start Ollama server in the background
/bin/ollama serve &
pid=$!

# Give the server a moment to initialise
sleep 5

echo "Pulling qwen3.5:4b..."
ollama pull qwen3.5:4b
echo "qwen3.5:4b ready."

echo "Pulling qwen3-embedding:0.6b..."
ollama pull qwen3-embedding:0.6b
echo "qwen3-embedding:0.6b ready."

echo "All models loaded. Ollama is up."

# Keep container alive by waiting for the server process
wait $pid
