"""Tests for Cypher and AGE SQL generators."""

from malimgraph.generators.age_sql import generate_age_sql
from malimgraph.generators.cypher import _dict_to_cypher, generate_cypher


def test_generate_cypher_contains_constraints(sample_kg):
    cypher = generate_cypher(sample_kg)
    assert "CREATE CONSTRAINT" in cypher
    assert "Organization" in cypher
    assert "Location" in cypher


def test_generate_cypher_contains_merge_nodes(sample_kg):
    cypher = generate_cypher(sample_kg)
    assert "MERGE" in cypher
    assert "Malim AI Labs" in cypher


def test_generate_cypher_contains_relationships(sample_kg):
    cypher = generate_cypher(sample_kg)
    assert "LOCATED_IN" in cypher
    assert "MATCH" in cypher


def test_generate_cypher_includes_provenance(sample_kg):
    cypher = generate_cypher(sample_kg)
    assert "confidence" in cypher
    assert "source_text" in cypher
    assert "extraction_method" in cypher


def test_generate_age_sql_contains_setup(sample_kg):
    sql = generate_age_sql(sample_kg, graph_name="test_graph")
    assert "CREATE EXTENSION IF NOT EXISTS age" in sql
    assert "LOAD 'age'" in sql
    assert "create_graph('test_graph')" in sql


def test_generate_age_sql_contains_nodes(sample_kg):
    sql = generate_age_sql(sample_kg)
    assert "MERGE" in sql
    assert "Malim AI Labs" in sql


def test_generate_age_sql_contains_relationships(sample_kg):
    sql = generate_age_sql(sample_kg)
    assert "LOCATED_IN" in sql


def test_dict_to_cypher_escapes_strings():
    result = _dict_to_cypher({"name": "O'Brien", "count": 5})
    assert "O\\'Brien" in result
    assert "5" in result


def test_dict_to_cypher_handles_lists():
    result = _dict_to_cypher({"pages": [1, 2, 3]})
    assert "[1, 2, 3]" in result


def test_dict_to_cypher_handles_booleans():
    result = _dict_to_cypher({"active": True, "deleted": False})
    assert "true" in result
    assert "false" in result
