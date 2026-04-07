from pathlib import Path
from typing import List, Optional
import re

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None


class DocumentParser:
    @staticmethod
    def parse_file(file_path: str) -> str:
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return DocumentParser._parse_pdf(file_path)
        elif suffix in [".docx", ".doc"]:
            return DocumentParser._parse_docx(file_path)
        elif suffix == ".txt":
            return DocumentParser._parse_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    @staticmethod
    def _parse_pdf(file_path: str) -> str:
        if PdfReader is None:
            raise ImportError("PyPDF2 is not installed. Run: pip install PyPDF2")

        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n".join(text_parts)

    @staticmethod
    def _parse_docx(file_path: str) -> str:
        if Document is None:
            raise ImportError(
                "python-docx is not installed. Run: pip install python-docx"
            )

        doc = Document(file_path)
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        return "\n".join(text_parts)

    @staticmethod
    def _parse_txt(file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            if end < len(text):
                last_period = chunk.rfind("。")
                last_newline = chunk.rfind("\n")
                split_pos = max(last_period, last_newline)
                if split_pos > chunk_size - 500:
                    chunk = chunk[: split_pos + 1]
                    end = start + split_pos + 1

            chunks.append(chunk)
            start = end - overlap

        return chunks


document_parser = DocumentParser()
