"""Embedding generation — supports OpenAI, Voyage AI, and local sentence-transformers."""

from __future__ import annotations

import os
from typing import Optional


SUPPORTED_PROVIDERS = ("openai", "voyage", "local")


class EmbedderConfig:
    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        batch_size: int = 32,
    ):
        self.provider = provider
        self.model = model or _default_model(provider)
        self.api_key = api_key or _default_api_key(provider)
        self.batch_size = batch_size

    @property
    def dimension(self) -> int:
        return _model_dimension(self.model)


def _default_model(provider: str) -> str:
    defaults = {
        "openai": "text-embedding-3-small",
        "voyage": "voyage-3-large",
        "local": "all-MiniLM-L6-v2",
    }
    return defaults.get(provider, "text-embedding-3-small")


def _default_api_key(provider: str) -> Optional[str]:
    env_vars = {
        "openai": "OPENAI_API_KEY",
        "voyage": "VOYAGE_API_KEY",
    }
    var = env_vars.get(provider)
    return os.environ.get(var) if var else None


def _model_dimension(model: str) -> int:
    dimensions = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
        "voyage-3-large": 1024,
        "voyage-3": 1024,
        "voyage-3-lite": 512,
        "all-MiniLM-L6-v2": 384,
        "all-mpnet-base-v2": 768,
        "BAAI/bge-small-en-v1.5": 384,
        "BAAI/bge-base-en-v1.5": 768,
        "BAAI/bge-large-en-v1.5": 1024,
    }
    return dimensions.get(model, 1536)


def embed_texts(texts: list[str], config: EmbedderConfig) -> list[list[float]]:
    """
    Generate embeddings for a list of texts.
    Returns a list of float vectors, one per input text.
    """
    if not texts:
        return []

    if config.provider == "openai":
        return _embed_openai(texts, config)
    elif config.provider == "voyage":
        return _embed_voyage(texts, config)
    elif config.provider == "local":
        return _embed_local(texts, config)
    else:
        raise ValueError(f"Unknown provider '{config.provider}'. Use: {SUPPORTED_PROVIDERS}")


def _embed_openai(texts: list[str], config: EmbedderConfig) -> list[list[float]]:
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("Install openai: pip install openai")

    if not config.api_key:
        raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings.")

    client = OpenAI(api_key=config.api_key)
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), config.batch_size):
        batch = texts[i : i + config.batch_size]
        # Truncate to 8191 tokens (OpenAI limit) — rough char estimate
        batch = [t[:30000] for t in batch]
        response = client.embeddings.create(input=batch, model=config.model)
        all_embeddings.extend([item.embedding for item in response.data])

    return all_embeddings


def _embed_voyage(texts: list[str], config: EmbedderConfig) -> list[list[float]]:
    try:
        import voyageai
    except ImportError:
        raise ImportError("Install voyageai: pip install voyageai")

    if not config.api_key:
        raise ValueError("VOYAGE_API_KEY is required for Voyage AI embeddings.")

    client = voyageai.Client(api_key=config.api_key)
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), config.batch_size):
        batch = texts[i : i + config.batch_size]
        result = client.embed(batch, model=config.model, input_type="document")
        all_embeddings.extend(result.embeddings)

    return all_embeddings


def _embed_local(texts: list[str], config: EmbedderConfig) -> list[list[float]]:
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ImportError("Install sentence-transformers: pip install sentence-transformers")

    model = SentenceTransformer(config.model)
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), config.batch_size):
        batch = texts[i : i + config.batch_size]
        vecs = model.encode(batch, normalize_embeddings=True)
        all_embeddings.extend(vecs.tolist())

    return all_embeddings
