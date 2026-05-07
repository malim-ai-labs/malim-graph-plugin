.PHONY: install dev lint test build skills clean

install:
	pip install -e .

dev:
	pip install -e ".[dev,all]"

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --tb=short --cov=malimgraph --cov-report=term-missing

build:
	python -m build

skills:
	@echo "Packaging skills..."
	@mkdir -p dist
	cd skills/pdf-to-knowledge-graph && zip -r ../../dist/pdf-to-knowledge-graph.skill SKILL.md scripts/
	cd skills/pdf-to-chunks && zip -r ../../dist/pdf-to-chunks.skill SKILL.md scripts/
	cd skills/document-to-html && zip -r ../../dist/document-to-html.skill SKILL.md scripts/
	cd skills/graph-db-admin && zip -r ../../dist/graph-db-admin.skill SKILL.md scripts/
	@echo "Skills packaged in dist/"

clean:
	rm -rf dist/ build/ *.egg-info src/*.egg-info __pycache__
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete

serve:
	malimgraph serve

serve-http:
	malimgraph serve --transport http --port 8080
