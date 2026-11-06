"""Deterministic, Zero-API-Key 1536-Dimensional Local Embedding Generator."""

import hashlib
import math
import re

from src.core.logging import get_logger

logger = get_logger(__name__)

EMBEDDING_DIMENSION = 1536
MODEL_NAME = "schemesaathi-deterministic-v1"
MODEL_VERSION = "v1"

# Semantic keywords assigned specific subspace emphasis for enhanced dense recall
DOMAIN_WEIGHTS: dict[str, float] = {
    "scholarship": 2.5,
    "scheme": 2.0,
    "merit": 2.5,
    "matric": 2.2,
    "income": 2.5,
    "ceiling": 2.0,
    "allowance": 2.4,
    "hosteller": 2.5,
    "hostel": 2.2,
    "day": 1.8,
    "scholar": 2.0,
    "displaced": 3.0,
    "rehabilitation": 3.0,
    "manipur": 2.0,
    "st": 2.8,
    "sc": 2.8,
    "obc": 2.8,
    "otr": 2.5,
    "nsp": 2.5,
    "face": 2.0,
    "rd": 2.0,
    "tuition": 2.0,
    "fee": 2.0,
    "waiver": 2.2,
    "aishe": 2.0,
    "undergraduate": 2.0,
    "postgraduate": 2.0,
    "degree": 1.8,
    "bonafide": 1.8,
    "certificate": 1.8,
    "freeship": 2.5,
}


def _hash_to_index_and_sign(
    token: str, seed: int, dim: int = EMBEDDING_DIMENSION
) -> tuple[int, float]:
    """Map token and seed to an index in [0, dim) and a pseudo-random sign {-1.0, 1.0}."""
    h_bytes = hashlib.md5(f"{seed}:{token}".encode()).digest()
    idx = int.from_bytes(h_bytes[:4], "little") % dim
    sign = 1.0 if (h_bytes[4] % 2 == 0) else -1.0
    return idx, sign


class LocalDeterministicEmbedder:
    """Generates reproducible 1536-dimensional L2-normalized dense embeddings locally."""

    def __init__(self, dimension: int = EMBEDDING_DIMENSION) -> None:
        self.dimension = dimension
        self.model_name = MODEL_NAME
        self.model_version = MODEL_VERSION

    def embed_text(self, text: str) -> list[float]:
        """Convert text into an L2-normalized 1536-dimensional embedding vector."""
        vec = [0.0] * self.dimension
        clean_text = text.lower().strip()
        if not clean_text:
            vec[0] = 1.0
            return vec

        tokens = re.findall(r"\w+", clean_text)
        if not tokens:
            vec[0] = 1.0
            return vec

        # 1. Word unigrams & bigrams
        for i, tok in enumerate(tokens):
            w = DOMAIN_WEIGHTS.get(tok, 1.0)
            # Unigram hashing
            for seed in (17, 31, 79):
                idx, sign = _hash_to_index_and_sign(tok, seed, self.dimension)
                vec[idx] += sign * w

            # Bigram hashing
            if i < len(tokens) - 1:
                bigram = f"{tok}_{tokens[i + 1]}"
                for seed in (43, 97):
                    idx, sign = _hash_to_index_and_sign(bigram, seed, self.dimension)
                    vec[idx] += sign * 1.5

        # 2. Character n-grams (3-grams and 4-grams) to capture subwords and transliterated variants
        for tok in tokens:
            if len(tok) >= 3:
                for j in range(len(tok) - 2):
                    tri = tok[j : j + 3]
                    idx, sign = _hash_to_index_and_sign(tri, 101, self.dimension)
                    vec[idx] += sign * 0.4

        # 3. L2 Normalization (Unit Length)
        norm_sq = sum(x * x for x in vec)
        if norm_sq > 0.0:
            inv_norm = 1.0 / math.sqrt(norm_sq)
            vec = [x * inv_norm for x in vec]
        else:
            vec[0] = 1.0

        return vec

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Batch embedding generation."""
        return [self.embed_text(t) for t in texts]


# Global singleton instance
local_embedder = LocalDeterministicEmbedder()
