# Website Developer & Processing Toolchain Guide

Personal Website: [jakegarrison.me](https://jakegarrison.me/)

This directory contains the Python automation scripts, test suites, and Makefile console to build, maintain, and synchronize personal website.

---

## Directory Structure
*   `Makefile`: Development console target runner (minification, importing, checks).
*   `import_images.py`: Image management library containing metadata mappings, batch importer `process_images()`, and Tkinter desktop crop app `ImageCropApp`.

*   `compressors.py`: Asset minification and compression library containing `WebMinifier`, `ImageCompressor`, and `PdfCompressor`.
*   `compressors_test.py`: Consolidated unit test suite for asset processing engines.
*   `fetchers.py`: Structured profile synchronization library containing `ScholarFetcher`, `GithubFetcher`, `PatentsFetcher`, and `LinkedinFetcher`.
*   `fetchers_test.py`: Consolidated unit test suite for web profiles sync fetchers.
*   `topics.py` / `tags.py`: shared topic vocabulary matching and the tag miner (`tags_test.py`).
*   `llms_txt.py` / `llms_txt_test.py`: generates `/llms.txt` (`llmstxt.org` v2) from `index.html` enriched with synced Scholar, patent, GitHub, and blog metadata.
*   `check_links.py`: broken hyperlinks scanner.
*   `check_links_test.py`: hyperlink verification scanner tests.
*   `format.py`: Code formatter script (yapf style formatter).
*   `format_test.py`: Code formatter validation tests.
*   `outputs/`: Stores raw files, profile sync output documents, and the coordinates cache `crop_cache.json`.
*   `requirements.txt`: Defines Python packages required by the processing scripts (Pillow, beautifulsoup4).

---

## Build & Maintenance Tooling

You can run development tasks either by navigating to this directory or using `make -C processing <command>` from the main repository root.

### 1. Interactive Asset Crop & Triage Tool
*   **Run Interactive Cropper**: Launches the aspect-ratio locked crop GUI on your desktop. It dynamically parses active site images from index.html, displays aspect ratio deviations, allows corner/edge resizing, and saves cropped JPEGs directly.
    ```bash
    make -C processing crop
    ```

### 2. Style & Asset Compression
*   **Minify CSS**: Compiles and shrinks the stylesheet (`main.css` -> `main.min.css`).
    ```bash
    make -C processing minify
    ```
*   **Compress Assets**: In-place optimizes new/modified image assets >`250KB` and PDF papers >`1.5MB` (uses local caches to prevent redundant compressions).
    ```bash
    make -C processing compress
    ```

### 3. Data Profile Synchronization
*   **Sync Web Profiles**: Scrapes/queries Google Scholar, Google Patents, and GitHub, and parses raw LinkedIn experience text dumps into Markdown files.
    ```bash
    make -C processing fetch
    ```
    *   GitHub includes repos authored outside `jake-g` via `config.EXTRA_GITHUB_REPOS` (e.g. `google-research/codegen-classroom`).
    *   `outputs/blogs_discovered.md`: scans the Google Research blog RSS (latest ~100 posts, cached in `outputs/blog_scan_cache.json`) and lists posts that link one of your papers or name you, plus topic-related posts, with an "On site" column.
*   **Mine Topic Tags**: Counts the `config.TOPIC_TAGS` vocabulary per site section and synced output, and suggests frequent untagged phrases.
    ```bash
    make -C processing tags   # -> outputs/tags.md, outputs/tags.json
    ```
*   **Generate `/llms.txt`**: Synchronizes the root `/llms.txt` file for AI agents and search engines directly from `index.html` and `outputs/*.md` (also runs automatically via pre-commit when `index.html` changes).
    ```bash
    make -C processing llms   # -> ../llms.txt
    ```

### 4. Verification & Testing
*   **Run Unit Tests**: Runs all unittest suites (`*_test.py`) to verify script compilation and helper logic.
    ```bash
    make -C processing test
    ```
*   **Scan for Broken Links**: Crawler that checks all external links in `index.html` to find dead URLs.
    ```bash
    make -C processing check-links
    ```


*   **Start Web Server**: Launches local testing server at [http://localhost:8000](http://localhost:8000).
    ```bash
    make -C processing server
    ```
*   **Clean Caches**: Removes Python bytecode caches.
    ```bash
    make -C processing clean
    ```

### 5. Analytics (GA4 + Search Console)
> **Privacy:** `processing/` is served publicly by GitHub Pages
> (`jakegarrison.me/processing/...`). Exports go to `outputs/analytics/`
> and credentials to `analytics/secrets/`; both are gitignored. Never commit
> them.

*   **Setup**: `make -C processing analytics-setup`, then authenticate with
    either a service account JSON at `analytics/secrets/sa.json` (grant it
    Viewer on the GA4 property + user on Search Console) or
    `gcloud auth application-default login` with the scopes listed in
    `analytics/pull.py`.
*   **Pull** (needs the numeric GA4 property ID, not the `G-` tag):
    ```bash
    GA4_PROPERTY_ID=123456789 make -C processing analytics-pull
    ```
*   **Report**: Writes `outputs/analytics/summary.md` (name-search ranking of
    homepage vs. resume PDF, yearly traffic, sources, downloads, queries).
    ```bash
    make -C processing analytics-report
    ```

---

## Pre-commit Hooks & CI Pipeline Architecture

The development workspace employs a bifurcated CI and pre-commit hook architecture to cleanly separate static web deployments from the Python developer toolchain:

### 1. Web Deployments CI & Pre-commit (Main Repo Root)
*   **Purpose**: Validates compiled web assets (HTML/CSS) and verifies hyperlinks and media sizes before deploying.
*   **Pre-commit Hooks (`.pre-commit-config.yaml`)**: Intercepts git commits to static files. Automatically minifies stylesheet changes (`make -C processing minify`) and checks/optimizes newly added images and PDFs (`make -C processing compress`) in-place.
*   **GitHub Actions CI (`.github/workflows/ci.yml`)**: Automatically executes on pushes and pull requests to `gh-pages`. Sets up Python, installs dependencies, verifies stylesheet compiles successfully, and runs all python unit tests.

### 2. Python Toolchain CI & Pre-commit (Submodule Repo Root)
*   **Purpose**: Maintains Python codebase style formatting and validates utility libraries logic.
*   **Pre-commit Hooks (`processing/.pre-commit-config.yaml`)**: Intercepts git commits inside the `processing/` folder. Automatically enforces Google Python Style formatting (`yapf`) and executes the unit tests suite (`make test`) before commits are finalized.

---
## Guidelines for AI Coding Agents

To maintain index file formatting consistency and prevent manual HTML tag errors, all updates to project cards, page structure, content, and links should be made by directly editing [index.html](file:///Users/jakegarrison/Downloads/projects/website/index.html).

### Core Rules:
1. **Careful direct edits:** Always review git diffs after editing `index.html` to ensure no closing tags are misaligned and no grid layout elements are broken.
2. **Aspect ratio compliance:** When adding/updating images, run `make -C processing diagnose` to verify that aspect ratios match target ratios (1.33 for project cards, 1.11 for blog cards, 0.77 for paper/patent covers, and 1.77 for slides).
3. **Optimizations:** After adding any new image or PDF file, run `make -C processing compress` to run automated in-place compression.
