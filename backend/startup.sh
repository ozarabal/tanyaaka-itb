#!/bin/bash

# Ingest documents if vector store is empty
if [ ! -d "chroma_db" ] || [ -z "$(ls -A chroma_db 2>/dev/null)" ]; then
    echo "Ingesting documents..."
    python -m scripts.ingest
fi

# Start the application
gunicorn app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120
