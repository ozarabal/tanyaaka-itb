import os
import re
from pathlib import Path
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain.schema import Document

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AcademicRegulationProcessor:
    """Processor khusus untuk dokumen peraturan akademik ITB"""
    
    def __init__(self):
        # Pattern untuk mendeteksi pasal dan ayat
        self.pasal_pattern = r"Pasal\s+\d+"
        self.ayat_pattern = r"\((\d+)\)"
        
    def extract_pasal_from_text(self, text: str) -> Optional[str]:
        """Ekstrak nomor dan nama pasal dari teks"""
        match = re.search(self.pasal_pattern, text, re.IGNORECASE)
        if match:
            # Ambil beberapa kata setelah "Pasal X" sebagai judul
            pasal_start = match.start()
            pasal_end = text.find('\n', pasal_start)
            if pasal_end == -1:
                pasal_end = min(pasal_start + 100, len(text))
            
            pasal_text = text[pasal_start:pasal_end].strip()
            return pasal_text
        return None
    
    def split_by_ayat(self, text: str, pasal_name: str, page_num: int, source_file: str) -> list[Document]:
        """Split teks berdasarkan ayat dan buat dokumen untuk setiap ayat"""
        chunks = []
        
        # Cari semua ayat dalam teks
        ayat_matches = list(re.finditer(self.ayat_pattern, text))
        
        if not ayat_matches:
            # Jika tidak ada ayat, buat satu chunk untuk seluruh pasal
            doc = Document(
                page_content=text.strip(),
                metadata={
                    "pasal": pasal_name,
                    "ayat": "0",  # ← UBAH dari None menjadi "0" atau "N/A"
                    "page": page_num,
                    "source_filename": source_file,
                    "chunk_type": "pasal_without_ayat"
                }
            )
            chunks.append(doc)
            return chunks
        
        # Split berdasarkan ayat
        for i, match in enumerate(ayat_matches):
            ayat_num = match.group(1)
            start_pos = match.start()
            
            # Tentukan akhir ayat (awal ayat berikutnya atau akhir teks)
            if i < len(ayat_matches) - 1:
                end_pos = ayat_matches[i + 1].start()
            else:
                end_pos = len(text)
            
            ayat_content = text[start_pos:end_pos].strip()
            
            doc = Document(
                page_content=ayat_content,
                metadata={
                    "pasal": pasal_name,
                    "ayat": ayat_num,
                    "page": page_num,
                    "source_filename": source_file,
                    "chunk_type": "ayat"
                }
            )
            chunks.append(doc)
        
        return chunks

    def process_document(self, text: str, page_num: int, source_file: str) -> list[Document]:
        """Process satu halaman dokumen"""
        chunks = []
        
        # Cari pasal dalam halaman ini
        pasal_name = self.extract_pasal_from_text(text)
        
        if pasal_name:
            # Split berdasarkan ayat
            ayat_chunks = self.split_by_ayat(text, pasal_name, page_num, source_file)
            chunks.extend(ayat_chunks)
        else:
            # Jika tidak ada pasal terdeteksi, tetap simpan sebagai konten umum
            doc = Document(
                page_content=text.strip(),
                metadata={
                    "pasal": "Unknown",
                    "ayat": "N/A",  # ← UBAH dari None menjadi "N/A"
                    "page": page_num,
                    "source_filename": source_file,
                    "chunk_type": "general_content"
                }
            )
            chunks.append(doc)
        
        return chunks


class DocumentProcessor:
    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
        use_academic_processor: bool = False,
        skip_first_pages: int = 5,  # Skip halaman 1-5
    ):
        self.use_academic_processor = use_academic_processor
        self.skip_first_pages = skip_first_pages
        
        if use_academic_processor:
            self.academic_processor = AcademicRegulationProcessor()

    def load_pdf(self, file_path: str) -> list[Document]:
        """Load a single PDF and return LangChain Documents"""
        loader = PyPDFLoader(file_path)
        docs = loader.load()

        # Skip halaman 1-5 (index 0-4)
        if self.use_academic_processor:
            docs = docs[self.skip_first_pages:]
            logger.info(
                "skipped_first_pages", 
                file=file_path, 
                skipped=self.skip_first_pages,
                remaining_pages=len(docs)
            )

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
        if self.use_academic_processor:
            # Gunakan academic processor untuk split per ayat
            all_chunks = []
            for doc in documents:
                page_num = doc.metadata.get("page", 0)
                source_file = doc.metadata.get("source_filename", "unknown")
                
                chunks = self.academic_processor.process_document(
                    doc.page_content,
                    page_num,
                    source_file
                )
                all_chunks.extend(chunks)
            
            logger.info(
                "split_documents_academic",
                input_docs=len(documents),
                output_chunks=len(all_chunks),
            )
            return all_chunks
        else:
            # Untuk non-academic, gunakan text splitter biasa
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.chunk_size if hasattr(self, 'chunk_size') else 1000,
                chunk_overlap=self.chunk_overlap if hasattr(self, 'chunk_overlap') else 200,
                separators=["\n\n", "\n", ". ", " ", ""],
                length_function=len,
            )
            
            chunks = text_splitter.split_documents(documents)
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