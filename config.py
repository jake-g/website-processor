"""Unified configuration and constants for the processing utilities."""

import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
IMAGE_DIR = os.path.join(BASE_DIR, 'image')
DOC_DIR = os.path.join(BASE_DIR, 'doc')
HTML_PATH = os.path.join(BASE_DIR, 'index.html')
CSS_PATH = os.path.join(BASE_DIR, 'main.css')
MIN_CSS_PATH = os.path.join(BASE_DIR, 'main.min.css')
LLMS_TXT_PATH = os.path.join(BASE_DIR, 'llms.txt')
SITE_URL = 'https://jakegarrison.me'

# Profiles & Credentials Sync
SCHOLAR_ID = 'kXNcQegAAAAJ'
GITHUB_USERNAME = 'jake-g'
# Repos authored outside the personal account.
EXTRA_GITHUB_REPOS = ('google-research/codegen-classroom',)
AUTHOR_NAMES = ('Jake Garrison', 'Jacob Garrison', 'Jake Henry Garrison')

# Google Research blog discovery (RSS holds roughly the latest 100 posts).
RESEARCH_BLOG_RSS = 'https://research.google/blog/rss/'
BLOG_SCAN_CACHE_NAME = 'blog_scan_cache.json'

# Topic vocabulary: tag -> regex aliases (case-insensitive, word-bounded).
# Used to score blog relevance and to mine tags from site content.
TOPIC_TAGS = {
    'health agents': [r'health agents?', r'personal health agent'],
    'ai agents': [r'agents?', r'agentic'],
    'multi-agent / swarms': [
        r'multi-agent', r'swarms?', r'parallel (?:llm )?agents',
        r'classroom of (?:llm )?agents'
    ],
    'self-improving ai': [
        r'self-improving', r'self-improvement', r'recursive self-improvement',
        r'rsi'
    ],
    'autoresearch': [
        r'autoresearch', r'automated research', r'empirical software',
        r'research assistan(?:t|ce)', r'code generation', r'codegen'
    ],
    'foundation models': [
        r'foundation models?', r'large sensor models?', r'lsm-?\d?',
        r'sensorfm', r'audiofm'
    ],
    'llms': [r'llms?', r'large language models?', r'gemini', r'gemma'],
    'frontier ai': [r'frontier'],
    'edge ai': [
        r'edge ai', r'on-device', r'tinyml', r'esp32', r'microcontrollers?',
        r'embedded'
    ],
    'wearables': [r'wearables?', r'fitbit', r'sensors?'],
    'health acoustics': [
        r'health acoustics?', r'cough\w*', r'health acoustic representations',
        r'respirat\w+', r'spirometr\w+', r'sleep'
    ],
    'audio': [r'audio', r'sound', r'speech', r'music'],
    'computer vision': [r'computer vision', r'image', r'vision'],
    'robotics / sim': [
        r'robot\w*', r'mujoco', r'physics sim\w*', r'autonomous'
    ],
    'signal processing': [r'signal processing', r'dsp', r'sonar'],
}

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
