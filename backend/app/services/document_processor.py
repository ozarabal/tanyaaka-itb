import os
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain.schema import Document

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AcademicRegulationProcessor:
    """Processor khusus untuk dokumen peraturan akademik ITB"""

    def __init__(self):
        self.pasal_pattern = r"Pasal\s+\d+"

        # ------------------------------------------------------------------ #
        # Ayat VALID: (N) di awal baris (boleh ada spasi/tab sebelumnya),
        # diikuti spasi lalu karakter non-spasi.
        #
        # Ini mencegah false-positive seperti:
        #   "sebagaimana dimaksud pada ayat (1) huruf a"  ← di tengah kalimat
        #   "ayat (2) dan ayat (3)"                       ← referensi silang
        # ------------------------------------------------------------------ #
        self.ayat_pattern = re.compile(
            r"(?m)"           # multiline: ^ dan $ berlaku per baris
            r"^\s*"           # awal baris, boleh ada whitespace
            r"\((\d+)\)"      # capture nomor ayat → group(1)
            r"(?=\s+\S)"      # lookahead: harus diikuti spasi lalu karakter
        )

    # ---------------------------------------------------------------------- #
    #  Text Cleaning                                                           #
    # ---------------------------------------------------------------------- #

    def clean_text(self, text: str) -> str:
        """
        Normalisasi teks mentah hasil ekstraksi PDF.

        Langkah-langkah:
        1. Normalisasi line ending
        2. Gabungkan kata yang terpotong dengan soft-hyphen
        3. Gabungkan baris yang wrap di tengah kalimat
        4. Ganti newline tunggal (dalam paragraf) dengan spasi
        5. Normalkan spasi berlebih
        6. Normalkan newline berlebih (>2 menjadi 2)
        """
        # 1. Normalisasi line ending
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 2. Gabungkan kata terpotong soft-hyphen: "proses-\nkan" → "prosesekan"
        text = re.sub(r"-\n(?=[a-z])", "", text)

        # 3. Gabungkan baris wrap di tengah kalimat:
        #    baris berakhir huruf/angka/koma/titik koma DAN baris berikut
        #    dimulai huruf kecil → kemungkinan besar satu kalimat
        text = re.sub(r"(?<=[a-zA-Z0-9,;:])\n(?=[a-z])", " ", text)

        # 4. Newline tunggal sisa (dalam paragraf) → spasi
        text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)

        # 5. Normalkan spasi/tab berlebih (tidak menyentuh newline)
        text = re.sub(r"[ \t]+", " ", text)

        # 6. Maksimal 2 newline berturut-turut
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def clean_chunk_text(self, text: str) -> str:
        """Cleaning ringan untuk konten chunk setelah di-split."""
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # ---------------------------------------------------------------------- #
    #  Pasal Extraction                                                        #
    # ---------------------------------------------------------------------- #

    def extract_pasal_from_text(self, text: str) -> Optional[str]:
        """
        Ekstrak nama pasal lengkap dari teks.
        Contoh hasil: "Pasal 18 Mahasiswa Aktif"
        """
        match = re.search(self.pasal_pattern, text, re.IGNORECASE)
        if not match:
            return None

        pasal_start = match.start()
        pasal_end = text.find("\n", pasal_start)
        if pasal_end == -1:
            pasal_end = min(pasal_start + 120, len(text))

        pasal_text = text[pasal_start:pasal_end].strip()

        # Cek baris berikutnya — sering berisi nama pasal
        # Contoh:  "Pasal 18\n" + "Mahasiswa Aktif\n"
        after_pasal = text[pasal_end:].lstrip("\n ")
        next_line_end = after_pasal.find("\n")
        next_line = (
            after_pasal[:next_line_end].strip()
            if next_line_end != -1
            else after_pasal.strip()
        )

        # Gabungkan jika baris berikut bukan awal ayat atau pasal baru
        if next_line and not re.match(r"^\(\d+\)|^Pasal\s+\d+", next_line):
            pasal_text = f"{pasal_text} {next_line}"

        return pasal_text

    # ---------------------------------------------------------------------- #
    #  Split by Ayat                                                           #
    # ---------------------------------------------------------------------- #

    def split_by_ayat(
        self, text: str, pasal_name: str, page_num: int, source_file: str
    ) -> list[Document]:
        """
        Split teks berdasarkan ayat.
        Setiap chunk diberi prefix nama pasal agar mandiri secara semantik.
        """
        chunks = []
        ayat_matches = list(self.ayat_pattern.finditer(text))

        if not ayat_matches:
            cleaned = self.clean_chunk_text(text)
            if cleaned:
                chunks.append(Document(
                    page_content=cleaned,
                    metadata={
                        "pasal": pasal_name,
                        "ayat": "0",
                        "page": page_num,
                        "source_filename": source_file,
                        "chunk_type": "pasal_without_ayat",
                    },
                ))
            return chunks

        for i, match in enumerate(ayat_matches):
            ayat_num = match.group(1)
            start_pos = match.start()
            end_pos = (
                ayat_matches[i + 1].start()
                if i < len(ayat_matches) - 1
                else len(text)
            )

            ayat_content = self.clean_chunk_text(text[start_pos:end_pos])
            if not ayat_content:
                continue

            # Prefix pasal sebagai konteks agar chunk bisa berdiri sendiri
            content_with_context = f"{pasal_name}\n{ayat_content}"

            chunks.append(Document(
                page_content=content_with_context,
                metadata={
                    "pasal": pasal_name,
                    "ayat": ayat_num,
                    "page": page_num,
                    "source_filename": source_file,
                    "chunk_type": "ayat",
                },
            ))

        return chunks

    # ---------------------------------------------------------------------- #
    #  Process One Page                                                        #
    # ---------------------------------------------------------------------- #

    def process_document(
        self, text: str, page_num: int, source_file: str
    ) -> list[Document]:
        """Process satu halaman dokumen: clean dulu, baru split."""
        cleaned_text = self.clean_text(text)

        if not cleaned_text:
            return []

        pasal_name = self.extract_pasal_from_text(cleaned_text)

        if pasal_name:
            return self.split_by_ayat(cleaned_text, pasal_name, page_num, source_file)

        return [Document(
            page_content=cleaned_text,
            metadata={
                "pasal": "Unknown",
                "ayat": "N/A",
                "page": page_num,
                "source_filename": source_file,
                "chunk_type": "general_content",
            },
        )]


# --------------------------------------------------------------------------- #
#  JSON Export Utilities                                                        #
# --------------------------------------------------------------------------- #

def documents_to_json(documents: list[Document]) -> list[dict]:
    result = []
    for idx, doc in enumerate(documents):
        result.append({
            "chunk_id": idx,
            "content": doc.page_content,
            "metadata": doc.metadata,
        })
    return result


def export_to_json(
    documents: list[Document],
    output_path: Optional[str] = None,
    return_string: bool = False,
) -> str | dict:
    data = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "total_chunks": len(documents),
        "chunks": documents_to_json(documents),
    }

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("exported_json", path=output_path, total_chunks=len(documents))

    if return_string:
        return json.dumps(data, ensure_ascii=False, indent=2)

    return data


# --------------------------------------------------------------------------- #
#  DocumentProcessor                                                            #
# --------------------------------------------------------------------------- #

# class DocumentProcessor:
#     def __init__(
#         self,
#         chunk_size: int = settings.CHUNK_SIZE,
#         chunk_overlap: int = settings.CHUNK_OVERLAP,
#         use_academic_processor: bool = False,
#         skip_first_pages: int = 5,
#     ):
#         self.chunk_size = chunk_size
#         self.chunk_overlap = chunk_overlap
#         self.use_academic_processor = use_academic_processor
#         self.skip_first_pages = skip_first_pages

#         if use_academic_processor:
#             self.academic_processor = AcademicRegulationProcessor()

#     def load_pdf(self, file_path: str) -> list[Document]:
#         loader = PyPDFLoader(file_path)
#         docs = loader.load()

#         if self.use_academic_processor:
#             docs = docs[self.skip_first_pages:]
#             logger.info(
#                 "skipped_first_pages",
#                 file=file_path,
#                 skipped=self.skip_first_pages,
#                 remaining_pages=len(docs),
#             )

#         for doc in docs:
#             doc.metadata["source_filename"] = Path(file_path).name

#         logger.info("loaded_pdf", file=file_path, pages=len(docs))
#         return docs

#     def load_directory(self, directory: str | None = None) -> list[Document]:
#         pdf_dir = directory or settings.PDF_DIR
#         all_docs = []
#         for filename in os.listdir(pdf_dir):
#             if filename.lower().endswith(".pdf"):
#                 file_path = os.path.join(pdf_dir, filename)
#                 all_docs.extend(self.load_pdf(file_path))
#         logger.info("loaded_directory", directory=pdf_dir, total_pages=len(all_docs))
#         return all_docs

#     def split_documents(self, documents: list[Document]) -> list[Document]:
#         if self.use_academic_processor:
#             all_chunks = []
#             for doc in documents:
#                 page_num = doc.metadata.get("page", 0)
#                 source_file = doc.metadata.get("source_filename", "unknown")
#                 chunks = self.academic_processor.process_document(
#                     doc.page_content, page_num, source_file
#                 )
#                 all_chunks.extend(chunks)

#             logger.info(
#                 "split_documents_academic",
#                 input_docs=len(documents),
#                 output_chunks=len(all_chunks),
#             )
#             return all_chunks
#         else:
#             from langchain.text_splitter import RecursiveCharacterTextSplitter

#             text_splitter = RecursiveCharacterTextSplitter(
#                 chunk_size=self.chunk_size,
#                 chunk_overlap=self.chunk_overlap,
#                 separators=["\n\n", "\n", ". ", " ", ""],
#                 length_function=len,
#             )
#             chunks = text_splitter.split_documents(documents)
#             logger.info(
#                 "split_documents",
#                 input_docs=len(documents),
#                 output_chunks=len(chunks),
#             )
#             return chunks

#     def process_directory(self, directory: str | None = None) -> list[Document]:
#         documents = self.load_directory(directory)
#         return self.split_documents(documents)

#     def process_directory_to_json(
#         self,
#         directory: str | None = None,
#         output_path: str | None = None,
#         return_string: bool = False,
#     ) -> str | dict:
#         chunks = self.process_directory(directory)
#         return export_to_json(chunks, output_path=output_path, return_string=return_string)

#     def split_documents_to_json(
#         self,
#         documents: list[Document],
#         output_path: str | None = None,
#         return_string: bool = False,
#     ) -> str | dict:
#         chunks = self.split_documents(documents)
#         return export_to_json(chunks, output_path=output_path, return_string=return_string)
    


class DocumentProcessor:
    def __init__(
            self,
            chunk_size: int = settings.CHUNK_SIZE,
            chunk_overlap: int = settings.CHUNK_OVERLAP,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.pasal_pattern = re.compile(r"Pasal\s+\d+", re.IGNORECASE)
        self.ayat_pattern = re.compile(r"(?:^|\n)(\(\d+\))", re.MULTILINE)

    def is_cover_page(self, page_index: int) -> bool:
        return page_index <= 1

    def is_toc_page(self, doc: Document) -> bool:
        lines = doc.page_content.splitlines()
        dotted_lines = sum(1 for line in lines if re.search(r"\.{5,}", line))
        return dotted_lines >= 2

    # --------------------------------------------------------------------------- #
    #  Header / Footer Cleaner                                                      #
    # --------------------------------------------------------------------------- #

    def strip_page_header(self, text: str) -> str:
        """Hapus baris header berulang: judul buku dan label BAB."""
        lines = text.splitlines()
        cleaned = []
        for line in lines:
            if re.search(r"Buku Peraturan Akademik ITB\s+\d{4}", line):
                continue
            if re.match(r"^\s*BAB\s+[IVXLC]+\s*$", line):
                continue
            cleaned.append(line)
        return "\n".join(cleaned)

    # --------------------------------------------------------------------------- #
    #  Pasal Detection                                                              #
    # --------------------------------------------------------------------------- #

    def extract_pasal_name(self, text: str) -> str | None:
        """Ekstrak nama pasal lengkap, misal: 'Pasal 14 Rencana Studi Semester'"""
        match = self.pasal_pattern.search(text)
        if not match:
            return None

        pasal_start = match.start()
        pasal_end = text.find("\n", pasal_start)
        pasal_line = text[pasal_start: pasal_end if pasal_end != -1 else pasal_start + 100].strip()

        after = text[pasal_end:].lstrip("\n ") if pasal_end != -1 else ""
        next_end = after.find("\n")
        next_line = after[:next_end].strip() if next_end != -1 else after.strip()

        if next_line and not re.match(r"^\(\d+\)|^Pasal\s+\d+", next_line):
            pasal_line = f"{pasal_line} {next_line}"

        return pasal_line

    def page_has_new_pasal(self, text: str) -> bool:
        """Cek apakah halaman memiliki deklarasi Pasal baru."""
        return bool(self.pasal_pattern.search(text))

    def page_is_continuation(self, text: str) -> bool:
        """
        Halaman lanjutan jika baris pertama non-kosong BUKAN merupakan:
        1. Header BAB / judul bab  → semua huruf kapital, misal 'LAYANAN AKADEMIK'
        2. Deklarasi Pasal          → 'Pasal 29 ...'
        3. Awal ayat bernomor       → '(3) Jadwal ujian ...'

        Halaman DIANGGAP lanjutan jika baris pertama dimulai dengan:
        - huruf kecil              → misal 'iii. Pada akhir Tahun ...'
        - kata sambungan campuran  → misal 'Sarjana-Magister dengan ...'
        """
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue

            # 1. Dimulai dengan Pasal → bukan lanjutan
            if self.pasal_pattern.match(stripped):
                return False

            # 2. Dimulai dengan nomor ayat '(\d+)' → bukan lanjutan
            if re.match(r"^\(\d+\)", stripped):
                return False

            # 3. Baris pertama SEMUA HURUF KAPITAL (header bab) → bukan lanjutan
            letters = re.sub(r"[^a-zA-Z]", "", stripped)
            if letters and letters == letters.upper():
                return False

            # 4. Sisanya → lanjutan
            return True

        return False

    # --------------------------------------------------------------------------- #
    #  Ayat Splitter                                                                #
    # --------------------------------------------------------------------------- #

    def split_into_ayat(self, documents: list[Document]) -> list[Document]:
        """
        Pecah setiap Document menjadi chunk per ayat.

        Aturan split:
        - Ayat dimulai dengan '(\d+)' di awal teks ATAU setelah '\n'
        - Teks sebelum ayat pertama (misal: judul Pasal / header bab) 
          dijadikan chunk tersendiri jika tidak kosong
        - pasal_context diambil dari chunk itu sendiri; jika tidak ada,
          diwariskan dari pasal_context terakhir yang ditemukan (carry-forward)

        Returns:
            list[Document]: satu Document per ayat (atau per blok pra-ayat)
        """
        result: list[Document] = []
        last_pasal_context: str = "Unknown"

        for doc in documents:
            text = doc.page_content
            base_meta = doc.metadata.copy()

            # Temukan semua posisi awal ayat: '(\d+)' di awal atau setelah '\n'
            # Kita pakai finditer dengan pola yang menangkap posisi '(' itu sendiri
            splits: list[int] = []
            for m in re.finditer(r"(?:^|\n)(\(\d+\))", text):
                # Posisi karakter '(' — jika diawali '\n', geser +1
                pos = m.start() if text[m.start()] == "(" else m.start() + 1
                splits.append(pos)

            if not splits:
                # Tidak ada ayat → simpan dokumen utuh
                pasal = self.extract_pasal_name(text) or base_meta.get("pasal_context", "Unknown")
                if pasal == "Unknown":
                    pasal = last_pasal_context
                else:
                    last_pasal_context = pasal

                result.append(Document(
                    page_content=text,
                    metadata={**base_meta, "pasal_context": pasal, "ayat": None},
                ))
                continue

            # Potong teks menjadi segmen: [0 → split[0]], [split[0] → split[1]], dst.
            boundaries = splits + [len(text)]
            segments: list[str] = []

            # Segmen sebelum ayat pertama (bisa berisi header Pasal / judul bab)
            preamble = text[: splits[0]].strip()
            if preamble:
                segments_with_pos = [(0, preamble)]
            else:
                segments_with_pos = []

            for i, start in enumerate(splits):
                end = boundaries[i + 1]
                seg = text[start:end].strip()
                if seg:
                    segments_with_pos.append((start, seg))

            # Ambil pasal_context yang berlaku untuk dokumen ini
            doc_pasal = self.extract_pasal_name(text) or base_meta.get("pasal_context", "Unknown")

            for _pos, seg in segments_with_pos:
                # Cek apakah segmen ini sendiri punya pasal baru
                seg_pasal = self.extract_pasal_name(seg)

                if seg_pasal:
                    last_pasal_context = seg_pasal
                    effective_pasal = seg_pasal
                elif doc_pasal and doc_pasal != "Unknown":
                    effective_pasal = doc_pasal
                    last_pasal_context = doc_pasal
                else:
                    effective_pasal = last_pasal_context

                # Ekstrak nomor ayat dari segmen (misal: "(4)")
                ayat_match = re.match(r"^\((\d+)\)", seg)
                ayat_num = int(ayat_match.group(1)) if ayat_match else None

                result.append(Document(
                    page_content=seg,
                    metadata={
                        **base_meta,
                        "pasal_context": effective_pasal,
                        "ayat": ayat_num,
                    },
                ))

        return result

    # --------------------------------------------------------------------------- #
    #  Main Loader                                                                  #
    # --------------------------------------------------------------------------- #

    def load_pdf(self, file_path: str, verbose: bool = False) -> list[Document]:
        """
        Load PDF dengan 3 tahap:
        1. Filter  : buang cover dan daftar isi
        2. Clean   : hapus header berulang tiap halaman
        3. Merge   : gabungkan halaman lanjutan ke halaman sebelumnya
        """
        loader = PyPDFLoader(file_path)
        raw_docs = loader.load()

        # ── Pass 1: filter + clean ───────────────────────────────────────────────
        candidates: list[tuple[int, str]] = []
        skipped_pages: list[tuple[int, str]] = []

        for i, doc in enumerate(raw_docs):
            if self.is_cover_page(i):
                skipped_pages.append((i, "cover"))
                continue
            if self.is_toc_page(doc):
                skipped_pages.append((i, "daftar_isi"))
                continue

            clean = self.strip_page_header(doc.page_content).strip()
            if clean:
                candidates.append((i, clean))

        # ── Pass 2: merge halaman lanjutan ───────────────────────────────────────
        merged: list[tuple[int, str, list[int]]] = []
        merged_count = 0

        for page_idx, text in candidates:
            if merged and self.page_is_continuation(text):
                prev_idx, prev_text, prev_pages = merged[-1]
                merged[-1] = (prev_idx, prev_text + "\n" + text, prev_pages + [page_idx])
                merged_count += 1
            else:
                merged.append((page_idx, text, [page_idx]))

        # ── Pass 3: bangun Document ───────────────────────────────────────────────
        result: list[Document] = []

        for page_idx, text, all_pages in merged:
            pasal_name = self.extract_pasal_name(text)
            result.append(Document(
                page_content=text,
                metadata={
                    "source": file_path,
                    "source_filename": Path(file_path).name,
                    "page": page_idx,
                    "page_index": page_idx,
                    "merged_pages": all_pages,
                    "is_multi_page": len(all_pages) > 1,
                    "pasal_context": pasal_name or "Unknown",
                },
            ))

        # ── Verbose report ───────────────────────────────────────────────────────
        if verbose:
            print(f"Total halaman raw  : {len(raw_docs)}")
            print(f"Halaman dilewati   : {len(skipped_pages)}")
            for page_idx, reason in skipped_pages:
                print(f"  - page index {page_idx:>3}  →  {reason}")
            print(f"Halaman kandidat   : {len(candidates)}")
            print(f"Halaman di-merge   : {merged_count}")
            print(f"Dokumen hasil      : {len(result)}")
            multi = [d for d in result if d.metadata["is_multi_page"]]
            if multi:
                print(f"\nDokumen hasil merge ({len(multi)}):")
                for d in multi:
                    print(f"  pages {d.metadata['merged_pages']}  →  '{d.metadata['pasal_context']}'")

        return result

    def split_documents_to_json(
        self,
        documents: list[Document],
        output_path: str | None = None,
        return_string: bool = False,
    ) -> str | dict:
        chunks = self.load_pdf(documents)
        return export_to_json(chunks, output_path=output_path, return_string=return_string)
