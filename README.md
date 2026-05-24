# Processing Automation Library

This directory contains Python automation scripts, test suites, and caches to maintain Jake's personal website.

## Directory Structure
*   `compressors.py`: Asset minification and compression library containing `WebMinifier`, `ImageCompressor`, and `PdfCompressor`.
*   `compressors_test.py`: Consolidated unit test suite for asset processing engines.
*   `fetchers.py`: Structured synchronization library containing `ScholarFetcher`, `GithubFetcher`, `PatentsFetcher`, and `LinkedinFetcher`.
*   `fetchers_test.py`: Consolidated unit test suite for web profiles sync fetchers.
*   `check_links.py`: broken hyperlinks scanner.
*   `check_links_test.py`: hyperlink verification scanner tests.
*   `.image_compress_cache.json`: Local cache tracking size, modification times, and MD5 hashes of optimized images to prevent redundant re-compressions.
*   `.pdf_compress_cache.json`: Local cache tracking size, modified times, and status of optimized PDF papers to prevent redundant compressions.

---

## Command Line Actions (Via root Makefile)

### 1. Style & Asset Compression
Optimizes the site's assets and minifies stylesheets:
*   **Minify CSS**: Minifies `main.css` to `main.min.css`.
    ```bash
    make minify
    ```
*   **Compress Assets**: Scans images (`image/`) and documents (`doc/`). Compresses only **new or modified** JPEGs/PNGs >`250KB` and PDFs >`1.5MB` in-place.
    ```bash
    make compress
    ```

### 2. Testing
Executes all consolidated test suites:
```bash
make test
```

### 3. Data Synchronization
Syncs live academic citations and developer profile activities into clean Markdown dumps inside the project root:
```bash
make fetch
```
*   **Output Dumps**:
    *   `scholar_publications.md`: Chronological table of research papers from Google Scholar.
    *   `github_projects.md`: Directory of latest active repositories and commit logs.
    *   `patents.md`: Search query pointers and confirmed Google Patents listings.
    *   `linkedin_experience.md`: Parsed experience blocks from raw LinkedIn copy-pastes.
