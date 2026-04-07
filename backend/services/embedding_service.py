from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from ..core.config import get_settings

settings = get_settings()


class EmbeddingService:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _load_model(self):
        if self._model is None:
            self._model = SentenceTransformer(
                "shibing624/text2vec-base-chinese", device=settings.embedding_device
            )
        return self._model

    def encode(self, texts: List[str], batch_size: int = None) -> np.ndarray:
        model = self._load_model()
        batch_size = batch_size or settings.embedding_batch_size

        embeddings = model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return embeddings

    def encode_single(self, text: str) -> np.ndarray:
        model = self._load_model()
        embedding = model.encode(
            text, show_progress_bar=False, normalize_embeddings=True
        )
        return embedding

    def get_dimension(self) -> int:
        model = self._load_model()
        return model.get_sentence_embedding_dimension()


embedding_service = EmbeddingService()
