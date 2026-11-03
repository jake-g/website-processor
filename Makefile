.PHONY: help all minify compress test fetch check-links server clean format crop analytics-setup analytics-pull analytics-report tags

# Default target displays the help menu
help:
	@echo "========================================================="
	@echo "🌐 Website Processing Console"
	@echo "========================================================="
	@echo "Available commands:"
	@echo "  make crop        - Launch interactive GUI crop & triage tool"
	@echo "  make diagnose    - Scan active site images and check aspect ratio anomalies"
	@echo "  make minify      - Minify CSS stylesheet (main.css -> main.min.css)"
	@echo "  make compress    - Compress new large images (>250KB) and PDFs (>1.5MB)"
	@echo "  make format      - Auto-format Python scripts and trim web trailing whitespace"
	@echo "  make test        - Run all Python unit tests under processing/"
	@echo "  make fetch       - Run sync scripts (Scholar, GitHub, Patents, LinkedIn, blogs)"
	@echo "  make tags        - Mine topic tags from site + synced outputs (outputs/tags.md)"
	@echo "  make check-links - Scan website for broken/dead URLs"
	@echo "  make server      - Launch local testing server at http://localhost:8000"
	@echo "  make clean       - Remove Python bytecode cache files"
	@echo "  make analytics-setup  - Install GA4/Search Console client libs"
	@echo "  make analytics-pull   - Export GA4 + Search Console CSVs (private)"
	@echo "  make analytics-report - Summarize exported CSVs to summary.md"
	@echo "========================================================="

minify:
	PYTHONPATH=.. python3 -c "from processing.compressors import WebMinifier; WebMinifier().minify_css('../main.css', '../main.min.css')"

compress:
	PYTHONPATH=.. python3 -c "from processing.compressors import ImageCompressor, PdfCompressor; ImageCompressor('../image').run(); PdfCompressor('../doc').run()"

test:
	PYTHONPATH=.. python3 -m unittest discover -s . -p "*_test.py"

fetch:
	PYTHONPATH=.. python3 -m processing.fetchers

check-links:
	PYTHONPATH=.. python3 -m processing.check_links

server:
	@echo "Starting local web server at http://localhost:8005 ..."
	python3 -m http.server 8005 --directory ..

format:
	PYTHONPATH=.. python3 -m processing.format

clean:
	@echo "🧹 Cleaning up pycache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "✅ Clean completed."

crop:
	PYTHONPATH=.. python3 import_images.py crop

diagnose:
	PYTHONPATH=.. python3 import_images.py diagnose

analytics-setup:
	python3 -m pip install -r analytics/requirements.txt

analytics-pull:
	PYTHONPATH=.. python3 -m processing.analytics.pull

analytics-report:
	PYTHONPATH=.. python3 -m processing.analytics.report

tags:
	PYTHONPATH=.. python3 -m processing.tags
