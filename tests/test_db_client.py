"""Tests for db_client — mocked to avoid requiring live databases."""

from unittest.mock import patch

import pytest

from malimgraph.core.db_client import get_client


def test_get_client_invalid_target():
    with pytest.raises(ValueError, match="Unknown target"):
        get_client("mysql")


@patch("malimgraph.core.db_client.Neo4jClient.__init__", return_value=None)
def test_get_client_neo4j(mock_init):
    client = get_client("neo4j", uri="bolt://localhost:7687", user="neo4j", password="test")
    assert client is not None


@patch("malimgraph.core.db_client.AGEClient.__init__", return_value=None)
def test_get_client_age(mock_init):
    client = get_client("age", uri="host=localhost dbname=test user=postgres", graph_name="mygraph")
    assert client is not None


def test_neo4j_import_error():
    """Neo4jClient raises ImportError with helpful message when neo4j not installed."""
    with patch.dict("sys.modules", {"neo4j": None}):
        from malimgraph.core.db_client import Neo4jClient

        with pytest.raises((ImportError, Exception)):
            Neo4jClient("bolt://localhost:7687", "neo4j", "password")


def test_age_import_error():
    """AGEClient raises ImportError with helpful message when psycopg2 not installed."""
    with patch.dict("sys.modules", {"psycopg2": None}):
        from malimgraph.core.db_client import AGEClient

        with pytest.raises((ImportError, Exception)):
            AGEClient("host=localhost dbname=test user=postgres")
