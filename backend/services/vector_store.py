import os
import json
import numpy as np
from typing import List, Dict, Optional, Tuple
import faiss
from pathlib import Path
from ..core.config import get_settings
from .embedding_service import embedding_service

settings = get_settings()


class VectorStore:
    _instance = None
    _index = None
    _metadata = None
    _dimension = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _get_index_path(self) -> Path:
        path = Path(settings.vector_index_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _get_index_file(self) -> Path:
        return self._get_index_path() / "index.faiss"

    def _get_meta_file(self) -> Path:
        return self._get_index_path() / "metadata.json"

    def _init_index(self):
        if self._index is None:
            self._dimension = embedding_service.get_dimension()
            self._index = faiss.IndexFlatIP(self._dimension)
            self._metadata = []

    def load(self) -> bool:
        index_file = self._get_index_file()
        meta_file = self._get_meta_file()

        if index_file.exists() and meta_file.exists():
            self._index = faiss.read_index(str(index_file))
            with open(meta_file, "r", encoding="utf-8") as f:
                self._metadata = json.load(f)
            self._dimension = int(self._index.d)
            return True
        return False

    def save(self):
        self._init_index()
        faiss.write_index(self._index, str(self._get_index_file()))
        with open(self._get_meta_file(), "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, ensure_ascii=False, indent=2)

    def add(self, texts: List[str], metadata: List[Dict] = None):
        self._init_index()

        embeddings = embedding_service.encode(texts)

        if metadata is None:
            metadata = [{"text": text} for text in texts]
        elif isinstance(metadata, list):
            for i, m in enumerate(metadata):
                if "text" not in m:
                    m["text"] = texts[i]

        self._index.add(embeddings.astype(np.float32))
        self._metadata.extend(metadata)

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        if self._index is None or self._index.ntotal == 0:
            if not self.load():
                return []

        query_embedding = embedding_service.encode_single(query)
        query_embedding = query_embedding.reshape(1, -1).astype(np.float32)

        distances, indices = self._index.search(
            query_embedding, min(top_k, self._index.ntotal)
        )

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx < len(self._metadata):
                result = {"distance": float(dist), **self._metadata[idx]}
                results.append(result)

        return results

    def clear(self):
        self._init_index()
        self._metadata = []

    def count(self) -> int:
        if self._index is None:
            if not self.load():
                return 0
        return self._index.ntotal if self._index else 0

    def delete(self):
        index_file = self._get_index_file()
        meta_file = self._get_meta_file()

        if index_file.exists():
            os.remove(index_file)
        if meta_file.exists():
            os.remove(meta_file)

        self._index = None
        self._metadata = []


vector_store = VectorStore()
