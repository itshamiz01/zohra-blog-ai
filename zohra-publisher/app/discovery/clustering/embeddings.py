"""
Zohra — Embedding Provider Abstraction.

Allows plugging in pgvector, OpenAI, Gemini, Cohere, or local embeddings.
Provides a DeterministicEmbeddingProvider for offline unit/integration tests
and lightweight local execution without external billing.
"""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstract interface for text embeddings."""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Generate a float embedding vector for a single string."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate float embedding vectors for a batch of strings."""
        ...


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two normalized vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0

    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))

    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    return max(-1.0, min(1.0, dot / (norm1 * norm2)))


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """
    Fast, deterministic, zero-dependency embedding provider.
    Uses hashed character/word n-grams into a fixed-dimension vector (default: 64)
    with L2-normalization. Provides high similarity for semantically aligned text.
    """

    def __init__(self, dimension: int = 64) -> None:
        self.dimension = dimension

    async def embed_text(self, text: str) -> list[float]:
        return self._generate_vector(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._generate_vector(t) for t in texts]

    def _generate_vector(self, text: str) -> list[float]:
        if not text:
            return [0.0] * self.dimension

        vec = [0.0] * self.dimension
        words = re.findall(r"\b\w+\b", text.lower())

        if not words:
            return [0.0] * self.dimension

        # Accumulate word, 2-gram, and subword hashes
        tokens = list(words)
        for i in range(len(words) - 1):
            tokens.append(f"{words[i]}_{words[i + 1]}")
        for w in words:
            if len(w) >= 3:
                for i in range(len(w) - 2):
                    tokens.append(w[i : i + 3])

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:2], byteorder="big") % self.dimension
            vec[idx] += 1.0

        # L2-normalize
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [round(x / norm, 5) for x in vec]

        return vec
