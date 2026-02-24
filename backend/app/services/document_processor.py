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
