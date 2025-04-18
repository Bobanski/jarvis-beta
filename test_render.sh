#!/bin/bash

# Test the /parse endpoint on Render with our improved implementation
curl -X POST https://jarvis-beta.onrender.com/parse \
  -H "Content-Type: application/json" \
  -d '{"text": "Turn on the AC"}' \
  | python -m json.tool

echo -e "\n\nAlternative test command with a different request:"
echo "curl -X POST https://jarvis-beta.onrender.com/parse \
  -H \"Content-Type: application/json\" \
  -d '{\"text\": \"Make the bedroom orange\"}' \
  | python -m json.tool"