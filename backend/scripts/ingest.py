"""CLI script to ingest PDFs into the vector store.

Usage:
    cd backend
    python -m scripts.ingest
    python -m scripts.ingest --pdf-dir ./data/pdfs
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import vector_store_service


def main():
    parser = argparse.ArgumentParser(
        description="Ingest PDF documents into vector store"
    )
    parser.add_argument(
        "--pdf-dir", default=settings.PDF_DIR, help="Directory containing PDFs"
    )
    args = parser.parse_args()

    print(f"Ingesting PDFs from: {args.pdf_dir}")

    processor = DocumentProcessor()
    chunks = processor.process_directory(args.pdf_dir)

    if not chunks:
        print("No PDF documents found. Exiting.")
        return

    print(f"Created {len(chunks)} chunks from PDFs.")
    count = vector_store_service.add_documents(chunks)
    print(f"Added {count} chunks to ChromaDB at '{settings.CHROMA_PERSIST_DIR}'.")
    print("Done.")


if __name__ == "__main__":
    main()
