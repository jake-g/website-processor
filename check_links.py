"""Utility script to verify all links in index.html for dead URLs, using a local cache."""

import json
import logging
import os
import re
import time
import urllib.request
from bs4 import BeautifulSoup
from processing import config

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

CACHE_EXPIRY_SECONDS = 24 * 60 * 60  # Cache passes for 24 hours


def load_link_cache() -> dict:
  """Loads the link check cache from outputs folder.

  Returns:
      dict: The link check cache mapping URL to status/timestamp.
  """
  if os.path.exists(config.LINK_CACHE_PATH):
    try:
      with open(config.LINK_CACHE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)
    except Exception as e:  # pylint: disable=broad-except
      logger.warning('Failed to load link check cache: %s', e)
  return {}


def save_link_cache(cache: dict) -> None:
  """Saves the link check cache to outputs folder.

  Args:
      cache (dict): The link check cache mapping URL to status/timestamp.
  """
  try:
    parent_dir = os.path.dirname(config.LINK_CACHE_PATH)
    if parent_dir:
      os.makedirs(parent_dir, exist_ok=True)
    with open(config.LINK_CACHE_PATH, 'w', encoding='utf-8') as f:
      json.dump(cache, f, indent=2)
  except Exception as e:  # pylint: disable=broad-except
    logger.error('Failed to save link check cache: %s', e)


def check_url(url: str) -> bool:
  """Checks if a URL is active by performing a HEAD or GET request.

  Args:
      url (str): The URL to test.

  Returns:
      bool: True if the URL is active, False otherwise.
  """
  headers = {'User-Agent': config.USER_AGENT}
  # Try HEAD request first for speed, fallback to GET
  for method in ('HEAD', 'GET'):
    try:
      req = urllib.request.Request(url, headers=headers, method=method)
      with urllib.request.urlopen(req, timeout=5) as response:
        if response.status < 400:
          return True
    except Exception:  # pylint: disable=broad-except
      continue
  return False


def verify_links(html_path: str) -> None:
  """Extracts and verifies all external links from index.html with cache checks.

  Args:
      html_path (str): Path to the HTML file to scan.
  """
  try:
    with open(html_path, 'r', encoding='utf-8') as f:
      html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    links = soup.find_all('a', href=True)

    unique_urls = set()
    for link in links:
      url = link['href'].strip()
      # Only verify external HTTP/HTTPS links
      if url.startswith(('http://', 'https://')):
        unique_urls.add(url)

    logger.info('Found %d unique external URLs to check.', len(unique_urls))
    logger.info('=' * 80)

    cache = load_link_cache()
    updated_cache = {}
    dead_links = []
    current_time = time.time()

    for i, url in enumerate(sorted(unique_urls), 1):
      # Check if cached and active
      is_cached_active = False
      if url in cache:
        entry = cache[url]
        # Skip checking if it succeeded and cache hasn't expired yet
        if entry.get('status') == 'active' and (
            current_time - entry.get('timestamp', 0) < CACHE_EXPIRY_SECONDS):
          is_cached_active = True
          updated_cache[url] = entry

      if is_cached_active:
        logger.info('[%d/%d] (Cached Active): %s', i, len(unique_urls), url)
        continue

      logger.info('[%d/%d] Checking: %s', i, len(unique_urls), url)
      if check_url(url):
        updated_cache[url] = {'status': 'active', 'timestamp': current_time}
      else:
        dead_links.append(url)
        logger.warning('--> DEAD LINK DETECTED!')
        updated_cache[url] = {'status': 'dead', 'timestamp': current_time}

    # Save the updated link check cache back to disk
    save_link_cache(updated_cache)

    logger.info('=' * 80)
    if dead_links:
      logger.warning('Scan completed. Found %d dead links:', len(dead_links))
      for url in dead_links:
        logger.warning(' - %s', url)
    else:
      logger.info('Scan completed. All links are active (or cached active)!')

  except Exception as e:  # pylint: disable=broad-except
    logger.error('Error scanning file: %s', e)


def main() -> None:
  verify_links(config.HTML_PATH)


if __name__ == '__main__':
  main()
