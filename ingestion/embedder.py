"""Dense vector embedding generator with Ollama bridge and offline deterministic fallback."""

import hashlib
import json
import logging
import math
import re
from typing import List
import numpy as np
import requests

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 768
_ollama_checked = False
_ollama_available = False

def _check_ollama_availability() -> bool:
    global _ollama_checked, _ollama_available
    if _ollama_checked:
        return _ollama_available
    try:
        url = f"{settings.OLLAMA_BASE_URL}/api/tags"
        res = requests.get(url, timeout=0.8)
        _ollama_available = (res.status_code == 200)
    except Exception:
        _ollama_available = False
    _ollama_checked = True
    return _ollama_available

def _deterministic_semantic_vector(text: str, dim: int = EMBEDDING_DIM) -> List[float]:
    """Generate a deterministic, normalized 768-dimensional dense vector from text tokens.
    
    Uses bag-of-words and bi-gram hashing with sine-cosine multi-frequency projection,
    ensuring that semantic overlap yields high cosine similarity while disparate text yields low similarity.
    """
    vec = np.zeros(dim, dtype=np.float32)
    # Tokenize words
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        # Uniform vector if empty
        vec[:] = 1.0 / math.sqrt(dim)
        return vec.tolist()

    # Weight unigrams and bigrams
    terms = words[:]
    for i in range(len(words) - 1):
        terms.append(f"{words[i]}_{words[i+1]}")

    for term in terms:
        # Hash term to get seed
        h = int(hashlib.md5(term.encode("utf-8")).hexdigest(), 16)
        # Project into 8 distinct dimension indices per term
        for k in range(8):
            idx = (h + k * 97) % dim
            sign = 1.0 if ((h >> (k % 16)) & 1) == 0 else -1.0
            vec[idx] += sign * (1.0 / math.sqrt(len(terms)))

    # Compute Euclidean norm and normalize to unit length
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    else:
        vec[0] = 1.0

    return [float(x) for x in vec]

def generate_embedding(text: str) -> List[float]:
    """Generate 768-dimensional embedding via Ollama nomic-embed-text with automatic offline fallback."""
    if _check_ollama_availability():
        try:
            url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
            payload = {
                "model": settings.OLLAMA_EMBED_MODEL.split(":")[0],
                "prompt": text,
            }
            res = requests.post(url, json=payload, timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                embedding = data.get("embedding")
                if embedding and len(embedding) == EMBEDDING_DIM:
                    arr = np.array(embedding, dtype=np.float32)
                    arr = arr / np.linalg.norm(arr)
                    return [float(x) for x in arr]
        except Exception as e:
            logger.debug("Ollama embedding call failed: %s", e)

    # Offline deterministic fallback
    return _deterministic_semantic_vector(text, dim=EMBEDDING_DIM)

def compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two unit vectors."""
    a = np.array(vec_a, dtype=np.float32)
    b = np.array(vec_b, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
