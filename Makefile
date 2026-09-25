.PHONY: pipeline rebuild reports test test-pipeline test-site site build lint fmt

# Recompute indicators and re-export the JSON bundle from the existing store.
# --public: site/public/data ships to GitHub Pages with no non-public
# audience -- CI refuses to deploy a bundle missing this flag, so building
# without it here just means redoing the work.
pipeline:
	python3 pipeline/src/penplus_pipeline/run.py --transform --export --public

# Full rebuild from raw evidence. Requires data/raw/*.xlsx (see docs/architecture.md).
rebuild:
	python3 pipeline/src/penplus_pipeline/run.py --rebuild

# The partner workbook and one data-quality report per country, from the
# current store. Run after `make pipeline`.
reports:
	python3 pipeline/src/penplus_pipeline/consolidate.py \
		--workbook reports/partner_workbook.xlsx \
		--reports-dir reports/country

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
