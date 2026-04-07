from pathlib import Path
from typing import List, Tuple
import re

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

try:
    from docx import Document
except ImportError:
    Document = None


class DocumentProcessor:
    def __init__(self, chunk_size: int = 1500, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def parse_file(self, file_path: str) -> str:
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            return self._parse_pdf(file_path)
        elif suffix in [".docx", ".doc"]:
            return self._parse_docx(file_path)
        elif suffix == ".txt":
            return self._parse_txt(file_path)
        else:
            raise ValueError(f"Unsupported file format: {suffix}")

    def _parse_pdf(self, file_path: str) -> str:
        if PdfReader is None:
            raise ImportError("PyPDF2 is not installed")

        reader = PdfReader(file_path)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n".join(text_parts)

    def _parse_docx(self, file_path: str) -> str:
        if Document is None:
            raise ImportError("python-docx is not installed")

        doc = Document(file_path)
        text_parts = []
        for para in doc.paragraphs:
            if para.text.strip():
                text_parts.append(para.text)
        return "\n".join(text_parts)

    def _parse_txt(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def clean_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)
        text = re.sub(r"http[s]?://\S+", "", text)
        text = re.sub(r"\[\d+\]", "", text)
        text = re.sub(r"脚注.*", "", text)
        text = re.sub(r"注：.*", "", text)
        text = re.sub(r"参考文献.*", "", text, flags=re.DOTALL)
        text = re.sub(r"©.*", "", text)
        text = text.strip()
        return text

    def split_sentences(self, text: str) -> List[str]:
        sentences = re.split(r"[。！？；\n]+", text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk_text(self, text: str) -> List[Tuple[str, int, int]]:
        cleaned = self.clean_text(text)
        if len(cleaned) <= self.chunk_size:
            return [(cleaned, 0, len(cleaned))]

        chunks = []
        start = 0
        while start < len(cleaned):
            end = min(start + self.chunk_size, len(cleaned))
            chunk = cleaned[start:end]

            if end < len(cleaned):
                last_period = chunk.rfind("。")
                last_newline = chunk.rfind("\n")
                split_pos = max(last_period, last_newline)

                if split_pos > self.chunk_size - 300:
                    chunk = chunk[: split_pos + 1]
                    end = start + split_pos + 1

            chunks.append((chunk, start, end))
            start = end - self.overlap

        return chunks

    def process_document(self, file_path: str) -> dict:
        raw_text = self.parse_file(file_path)
        cleaned_text = self.clean_text(raw_text)
        chunks = self.chunk_text(cleaned_text)

        return {
            "filename": Path(file_path).name,
            "raw_length": len(raw_text),
            "cleaned_length": len(cleaned_text),
            "chunk_count": len(chunks),
            "chunks": [{"text": c[0], "start": c[1], "end": c[2]} for c in chunks],
        }


document_processor = DocumentProcessor()
