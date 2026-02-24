"""CLI script to ingest PDFs into the vector store.

Usage:
    cd backend
    python -m scripts.ingest
    python -m scripts.ingest --pdf-dir ./data/pdfs
    python -m scripts.ingest --export-json
    python -m scripts.ingest --export-json --json-output ./output/chunks.json
    python -m scripts.ingest --export-json-only --json-output ./output/chunks.json
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
    parser.add_argument(
        "--export-json",
        action="store_true",
        help="Export chunks ke file JSON setelah proses ingest",
    )
    parser.add_argument(
        "--json-output",
        default="./output/chunks.json",
        help="Path file JSON output (default: ./output/chunks.json)",
    )
    parser.add_argument(
        "--export-json-only",
        action="store_true",
        help="Hanya export JSON tanpa ingest ke vector store",
    )
    args = parser.parse_args()

    print(f"Ingesting PDFs from: {args.pdf_dir}")

    processor = DocumentProcessor()
    merged_docs = processor.load_pdf(args.pdf_dir+"/Buku_Peraturan_Akademik_2024_PR_25A.pdf")
    chunks = processor.split_into_ayat(merged_docs)

    if not chunks:
        print("No PDF documents found. Exiting.")
        return

    print(f"Created {len(chunks)} chunks from PDFs.")

    # ── Export JSON ────────────────────────────────────────────────────────────
    if args.export_json or args.export_json_only:
        from app.services.document_processor import export_to_json

        result = export_to_json(chunks, output_path=args.json_output)
        print(f"Exported {result['total_chunks']} chunks to JSON: '{args.json_output}'")

    # ── Ingest ke vector store (skip jika --export-json-only) ─────────────────
    if not args.export_json_only:
        count = vector_store_service.add_documents(chunks)
        print(f"Added {count} chunks to ChromaDB at '{settings.CHROMA_PERSIST_DIR}'.")

    print("Done.")


if __name__ == "__main__":
    main()