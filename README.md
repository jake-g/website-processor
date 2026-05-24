# Website Developer & Processing Toolchain Guide

This directory contains the Python automation scripts, test suites, and Makefile console to build, maintain, and synchronize Jake's personal website.

---

## Directory Structure
*   `Makefile`: Development console target runner (minification, importing, checks).
*   `import_images.py`: Image management library containing metadata mappings, batch importer `process_images()`, and Tkinter desktop crop app `ImageCropApp`.
*   `builder.py`: PageBuilder compilation library and programmatic index.html rebuild compiler script.
*   `builder_test.py`: Unit test suite for PageBuilder rendering and layout modifiers.
*   `compressors.py`: Asset minification and compression library containing `WebMinifier`, `ImageCompressor`, and `PdfCompressor`.
*   `compressors_test.py`: Consolidated unit test suite for asset processing engines.
*   `fetchers.py`: Structured profile synchronization library containing `ScholarFetcher`, `GithubFetcher`, `PatentsFetcher`, and `LinkedinFetcher`.
*   `fetchers_test.py`: Consolidated unit test suite for web profiles sync fetchers.
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

### 4. Verification & Testing
*   **Run Unit Tests**: Runs all unittest suites (`*_test.py`) to verify script compilation and helper logic.
    ```bash
    make -C processing test
    ```
*   **Scan for Broken Links**: Crawler that checks all external links in `index.html` to find dead URLs.
    ```bash
    make -C processing check-links
    ```

### 5. Local Development
*   **Compile index.html**: Programmatically rebuilds the flat-formatted `index.html` landing page from baseline.
    ```bash
    make -C processing rebuild
    ```
*   **Start Web Server**: Launches local testing server at [http://localhost:8000](http://localhost:8000).
    ```bash
    make -C processing server
    ```
*   **Clean Caches**: Removes Python bytecode caches.
    ```bash
    make -C processing clean
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

To maintain index file formatting consistency and prevent manual HTML tag errors, **all visual layout, section ordering, page structure, and card modifications** to the live website must be made programmatically rather than editing `index.html` manually.

### Core Workflow:
1. **Never edit `index.html` directly:** Direct edits of the 2000+ line static HTML file easily introduce nesting errors, misaligned grids, or broken cards.
2. **Implement rules in PageBuilder:** Create your layout rules, project card modifications, or grid reorderings inside [builder.py](builder.py) as a method on the `PageBuilder` class.
3. **Register in rebuild script:** Chain your new builder method inside the pipeline of [builder.py](builder.py) at the bottom.
4. **Compile Output:** Run the build console command to compile the changes:
   ```bash
   make -C processing rebuild
   ```
5. **Run Verification tests:** Run `make -C processing test` to confirm that the compiled outputs successfully parse and satisfy all aspect ratio checks.
6. **Double-Commit Strategy:** Since the source templates live inside the submodule and the compiled pages live in the root website, always commit your Python builder updates inside the `processing` repository and your compiled outputs inside the main `website` repository concurrently.

