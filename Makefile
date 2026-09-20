.PHONY: pipeline rebuild test test-pipeline test-site site build lint fmt

# Recompute indicators and re-export the JSON bundle from the existing store.
pipeline:
	python3 pipeline/src/penplus_pipeline/run.py --transform --export

# Full rebuild from raw evidence. Requires data/raw/*.xlsx (see docs/architecture.md).
rebuild:
	python3 pipeline/src/penplus_pipeline/run.py --rebuild

test: test-pipeline test-site

test-pipeline:
	cd pipeline && python3 -m pytest

test-site:
	cd site && npm test

site:
	cd site && npm run dev

build:
	cd site && npm run build

lint:
	cd pipeline && ruff check src
	cd site && npm run lint

fmt:
	cd pipeline && ruff format src
	cd site && npm run format
