#!/bin/bash

ollama serve &

echo "Waiting for Ollama server to start"
while ! curl -s http://localhost:11434/api/tags > /dev/null; do
  sleep 1
done


echo "Creating model 'financial-orchestrator' from Modelfile"
ollama create financial-orchestrator -f /root/Modelfile

wait