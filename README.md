# Website Developer & Processing Toolchain Guide

This directory contains the Python automation scripts, test suites, and Makefile console to build, maintain, and synchronize Jake's personal website.

---

## Directory Structure
*   `Makefile`: Development console target runner (minification, importing, checks).
*   `import_images.py`: Image management library containing metadata mappings, batch importer `process_images()`, and Tkinter desktop crop app `ImageCropApp`.
*   `compressors.py`: Asset minification and compression library containing `WebMinifier`, `ImageCompressor`, and `PdfCompressor`.
*   `compressors_test.py`: Consolidated unit test suite for asset processing engines.
*   `fetchers.py`: Structured profile synchronization library containing `ScholarFetcher`, `GithubFetcher`, `PatentsFetcher`, and `LinkedinFetcher`.
*   `fetchers_test.py`: Consolidated unit test suite for web profiles sync fetchers.
*   `check_links.py`: broken hyperlinks scanner.
*   `check_links_test.py`: hyperlink verification scanner tests.
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
