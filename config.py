"""Unified configuration and constants for the processing utilities."""

import os

# Project Directories & Paths
BASE_DIR = '/Users/jakegarrison/Downloads/projects/website'
IMAGE_DIR = os.path.join(BASE_DIR, 'image')
DOC_DIR = os.path.join(BASE_DIR, 'doc')
HTML_PATH = os.path.join(BASE_DIR, 'index.html')
CSS_PATH = os.path.join(BASE_DIR, 'main.css')
MIN_CSS_PATH = os.path.join(BASE_DIR, 'main.min.css')

# Profiles & Credentials Sync
SCHOLAR_ID = 'kXNcQegAAAAJ'
GITHUB_USERNAME = 'jake-g'

# Caching & Optimization Settings
OUTPUTS_DIR = os.path.join(BASE_DIR, 'processing', 'outputs')
COMPRESS_CACHE_PATH = os.path.join(OUTPUTS_DIR, 'compress_cache.json')
LINK_CACHE_PATH = os.path.join(OUTPUTS_DIR, 'link_cache.json')

# Threshold limits (bytes)
MAX_IMAGE_SIZE_BYTES = 250 * 1024  # 250KB
MAX_PDF_SIZE_BYTES = int(1.5 * 1024 * 1024)  # 1.5MB
DEFAULT_JPEG_QUALITY = 80

# Web Scraper User-Agent Header
USER_AGENT = (
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
