"""Local Multilingual Pretrained Dense Embedding Service (BAAI/bge-m3).

Generates real 1024-dimensional semantic dense embeddings locally using
BAAI/bge-m3 via SentenceTransformer. Zero paid API keys, zero network calls
at query time, deterministic inference, and unit L2 normalization matching
pgvector HNSW cosine index `vector_cosine_ops`.
"""

from typing import Any

from src.core.logging import get_logger

logger = get_logger(__name__)

EMBEDDING_DIMENSION = 1024
MODEL_NAME = "BAAI/bge-m3"
MODEL_VERSION = "v1"


class BgeM3Embedder:
    """Loads and executes BAAI/bge-m3 locally to produce 1024-dimensional dense vectors."""

    def __init__(self, model_name: str = MODEL_NAME, dimension: int = EMBEDDING_DIMENSION) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self.model_version = MODEL_VERSION
        self._model: Any = None

    def _get_model(self) -> Any:
        """Lazy load SentenceTransformer model on first inference."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info(
                "Loading local embedding model '%s' (dimension=%d)...",
                self.model_name,
                self.dimension,
            )
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """Convert input text into an L2-normalized 1024-dimensional dense embedding vector."""
        clean_text = text.strip()
        if not clean_text:
            vec = [0.0] * self.dimension
            vec[0] = 1.0
            return vec

        model = self._get_model()
        # encode with normalize_embeddings=True produces unit L2 vectors
        embedding_arr = model.encode(clean_text, normalize_embeddings=True)
        vec = [float(x) for x in embedding_arr]

        # Verify dimension
        if len(vec) != self.dimension:
            raise ValueError(
                f"Model {self.model_name} produced {len(vec)}-dimensional vector, "
                f"expected {self.dimension} dimensions"
            )

        return vec

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embedding generation with unit L2 normalization."""
        if not texts:
            return []

        clean_texts = [t.strip() for t in texts]
        non_empty = [t for t in clean_texts if t]

        if not non_empty:
            empty_vec = [0.0] * self.dimension
            empty_vec[0] = 1.0
            return [list(empty_vec) for _ in texts]

        model = self._get_model()
        embeddings_arr = model.encode(clean_texts, normalize_embeddings=True)
        results: list[list[float]] = []
        for i, raw_vec in enumerate(embeddings_arr):
            if not clean_texts[i]:
                vec = [0.0] * self.dimension
                vec[0] = 1.0
                results.append(vec)
            else:
                results.append([float(x) for x in raw_vec])
        return results


# Global singleton instance
local_embedder = BgeM3Embedder()
