import os
import json
import shutil
import pytest
from malimgraph.plugin import upsert_node, link_concepts, classify_domain

@pytest.fixture
def temp_output_dir(tmp_path):
    d = tmp_path / "output"
    d.mkdir()
    yield str(d)
    shutil.rmtree(str(d), ignore_errors=True)

@pytest.mark.asyncio
async def test_upsert_node(temp_output_dir):
    # Test error case (no definition/description)
    res = await upsert_node("n_test", "Test Node", "Concept", {}, output_dir=temp_output_dir)
    assert res["status"] == "error"
    assert "Properties must include" in res["message"]

    # Test success creation
    res = await upsert_node(
        "n_test",
        "Test Node",
        "Concept",
        {"definition": "A test concept node for orchestrator."},
        output_dir=temp_output_dir
    )
    assert res["status"] == "success"
    assert res["action"] == "created"
    assert res["node_id"] == "n_test"

    # Verify JSON content
    kg_path = os.path.join(temp_output_dir, "knowledge_graph.json")
    assert os.path.exists(kg_path)
    with open(kg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["entities"]) == 1
    assert data["entities"][0]["id"] == "n_test"
    assert data["entities"][0]["properties"]["definition"] == "A test concept node for orchestrator."
    assert data["metadata"]["total_entities"] == 1

    # Test success update
    res = await upsert_node(
        "n_test",
        "Test Node",
        "Concept",
        {"definition": "An updated test concept node."},
        output_dir=temp_output_dir
    )
    assert res["action"] == "updated"
    with open(kg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["entities"]) == 1
    assert data["entities"][0]["properties"]["definition"] == "An updated test concept node."

@pytest.mark.asyncio
async def test_link_concepts(temp_output_dir):
    # Link concepts should auto-create stubs if they don't exist
    res = await link_concepts(
        "n_src",
        "n_tgt",
        "RELATES_TO",
        "Verbatim quote showing relations.",
        output_dir=temp_output_dir
    )
    assert res["status"] == "success"
    assert res["action"] == "created"

    kg_path = os.path.join(temp_output_dir, "knowledge_graph.json")
    with open(kg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 2 stubs created + 1 relationship
    assert len(data["entities"]) == 2
    assert len(data["relationships"]) == 1
    assert data["relationships"][0]["source"] == "n_src"
    assert data["relationships"][0]["target"] == "n_tgt"
    assert data["relationships"][0]["type"] == "RELATES_TO"

@pytest.mark.asyncio
async def test_classify_domain(temp_output_dir):
    res = await classify_domain("AI", "Artificial Intelligence domain.", output_dir=temp_output_dir)
    assert res["status"] == "success"
    assert res["category_id"] == "AI"
    assert res["node_id"] == "cat_ai"

    kg_path = os.path.join(temp_output_dir, "knowledge_graph.json")
    with open(kg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert len(data["entities"]) == 1
    assert data["entities"][0]["type"] == "Category"
    assert data["entities"][0]["properties"]["description"] == "Artificial Intelligence domain."
