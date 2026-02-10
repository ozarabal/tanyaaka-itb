import os
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class DocumentProcessor:
    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
    ):
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )

    def load_pdf(self, file_path: str) -> list[Document]:
        """Load a single PDF and return LangChain Documents (one per page)."""
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        for doc in docs:
            doc.metadata["source_filename"] = Path(file_path).name
        logger.info("loaded_pdf", file=file_path, pages=len(docs))
        return docs

    def load_directory(self, directory: str | None = None) -> list[Document]:
        """Load all PDFs from a directory."""
        pdf_dir = directory or settings.PDF_DIR
        all_docs = []
        for filename in os.listdir(pdf_dir):
            if filename.lower().endswith(".pdf"):
                file_path = os.path.join(pdf_dir, filename)
                all_docs.extend(self.load_pdf(file_path))
        logger.info("loaded_directory", directory=pdf_dir, total_pages=len(all_docs))
        return all_docs

    def split_documents(self, documents: list[Document]) -> list[Document]:
        """Split documents into chunks."""
        chunks = self.text_splitter.split_documents(documents)
        logger.info(
            "split_documents",
            input_docs=len(documents),
            output_chunks=len(chunks),
        )
        return chunks

    def process_directory(self, directory: str | None = None) -> list[Document]:
        """Full pipeline: load PDFs from directory, split into chunks."""
        documents = self.load_directory(directory)
        chunks = self.split_documents(documents)
        return chunks
