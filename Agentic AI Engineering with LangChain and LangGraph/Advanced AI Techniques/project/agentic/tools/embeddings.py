import numpy as np
from agentic.config import get_embeddings


def _norm(a: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(a, axis=-1, keepdims=True)
    return a / np.where(n == 0, 1, n)


def embed_documents(texts: list[str]) -> np.ndarray:
    return _norm(np.array(get_embeddings().embed_documents(texts), dtype=float))


def embed_query(text: str) -> np.ndarray:
    return _norm(np.array(get_embeddings().embed_query(text), dtype=float))
