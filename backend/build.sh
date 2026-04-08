#!/bin/bash
# Delete all cached Python bytecode before installing
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
pip install -r requirements.txt
