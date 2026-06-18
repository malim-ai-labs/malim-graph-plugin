---
name: self-evolving-orchestrator
description: >
  Maintain, expand, and self-correct a dynamic network of concepts on every API call.
  Use this skill to update concept nodes, link entities, and manage categories using ReAct.
triggers:
  - "orchestrator"
  - "self-evolving graph"
  - "knowledge core"
  - "dynamic network of concepts"
  - "upsert concept"
  - "link concept"
  - "classify domain"
skip_if:
  - "chunk for RAG"
  - "render HTML"
---

# Self-Evolving Graph Orchestrator Skill

Implement and run the autonomous knowledge core workflow to mutate, update, and refine the concept network.

## Workflow

1. **upsert_node(node_id, label, category, properties)**: Register or update a concept.
2. **link_concepts(source_id, target_id, relation_type, context_justification)**: Connect concepts.
3. **classify_domain(category_id, description)**: Organize macro domains.

## Example

> "Upsert the concept 'Quantum Computing' with description 'A model of computation based on quantum physics' under category 'Technology'"
