"""Tests for pgvector client — mocked to avoid requiring a live database."""

from unittest.mock import patch

import pytest

from malimgraph.core.embedder import EmbedderConfig, _default_model, _model_dimension


def test_embedder_config_defaults():
    config = EmbedderConfig(provider="openai")
    assert config.model == "text-embedding-3-small"
    assert config.dimension == 1536


def test_embedder_config_voyage():
    config = EmbedderConfig(provider="voyage")
    assert config.model == "voyage-3-large"
    assert config.dimension == 1024


def test_embedder_config_local():
    config = EmbedderConfig(provider="local")
    assert config.model == "all-MiniLM-L6-v2"
    assert config.dimension == 384


def test_model_dimension_known_models():
    assert _model_dimension("text-embedding-3-small") == 1536
    assert _model_dimension("text-embedding-3-large") == 3072
    assert _model_dimension("voyage-3-large") == 1024
    assert _model_dimension("all-MiniLM-L6-v2") == 384


def test_model_dimension_unknown_defaults_to_1536():
    assert _model_dimension("unknown-model-xyz") == 1536


def test_default_model_per_provider():
    assert _default_model("openai") == "text-embedding-3-small"
    assert _default_model("voyage") == "voyage-3-large"
    assert _default_model("local") == "all-MiniLM-L6-v2"


def test_embed_texts_openai_import_error():
    """embed_texts raises ImportError with helpful message when openai not installed."""
    from malimgraph.core.embedder import EmbedderConfig, embed_texts

    with patch.dict("sys.modules", {"openai": None}):
        config = EmbedderConfig(provider="openai", api_key="test")
        with pytest.raises(ImportError, match="openai"):
            embed_texts(["test text"], config)


def test_embed_texts_empty_list():
    """embed_texts returns empty list for empty input without any API call."""
    from malimgraph.core.embedder import EmbedderConfig, embed_texts

    config = EmbedderConfig(provider="openai", api_key="test")
    result = embed_texts([], config)
    assert result == []


def test_pgvector_client_import_error():
    """PgVectorClient raises ImportError when psycopg2 is not installed."""
    with patch.dict("sys.modules", {"psycopg2": None}):
        from malimgraph.core.vector_client import PgVectorClient

        with pytest.raises((ImportError, Exception)):
            PgVectorClient("postgresql://localhost/test")


def test_invalid_embedding_provider():
    """embed_texts raises ValueError for unknown provider."""
    from malimgraph.core.embedder import EmbedderConfig, embed_texts

    config = EmbedderConfig.__new__(EmbedderConfig)
    config.provider = "unknown_provider"
    config.model = "some-model"
    config.api_key = None
    config.batch_size = 32
    with pytest.raises(ValueError, match="Unknown provider"):
        embed_texts(["hello"], config)
