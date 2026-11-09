"""Verifies external and local links and asset filenames for index.html."""

import argparse
from html.parser import HTMLParser
import http.client
import json
import logging
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
import urllib.error
import urllib.parse
import urllib.request

from processing import config

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

CACHE_EXPIRY_SECONDS = 24 * 60 * 60  # Cache passes for 24 hours
IGNORED_ASSET_DIRS = ('orig_image', 'new_image')
SKIPPED_SCHEMES = (
    'http://',
    'https://',
    'mailto:',
    'tel:',
    'javascript:',
    'data:',
)
_BAD_PERCENT_RE = re.compile(r'%(?![0-9A-Fa-f]{2})')
_WHITESPACE_RE = re.compile(r'\s')


class _LinkExtractor(HTMLParser):
  """Extracts element IDs and href/src attributes from HTML."""

  def __init__(self) -> None:
    super().__init__()
    self.element_ids: Set[str] = set()
    self.refs: List[Tuple[str, str, str]] = []

  def handle_starttag(
      self, tag: str, attrs: List[Tuple[str, Optional[str]]]
  ) -> None:
    attr_map = dict(attrs)
    elem_id = attr_map.get('id')
    if elem_id:
      self.element_ids.add(elem_id)

    for target_tag, attr_name in (
        ('a', 'href'),
        ('img', 'src'),
        ('link', 'href'),
    ):
      if tag == target_tag and attr_name in attr_map:
        val = attr_map[attr_name]
        if val is not None:
          self.refs.append((tag, attr_name, val))


def _parse_html_refs(html: str) -> _LinkExtractor:
  """Parses HTML content and returns extracted IDs and references."""
  extractor = _LinkExtractor()
  extractor.feed(html)
  return extractor


def load_link_cache() -> Dict[str, Any]:
  """Loads the link check cache from outputs folder.

  Returns:
    Dict[str, Any]: The link check cache mapping URL to status/timestamp.
  """
  if os.path.exists(config.LINK_CACHE_PATH):
    try:
      with open(config.LINK_CACHE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
      logger.warning('Failed to load link check cache: %s', e)
  return {}


def save_link_cache(cache: Dict[str, Any]) -> None:
  """Saves the link check cache to outputs folder.

  Args:
    cache (Dict[str, Any]): The link check cache mapping URL to status/time.
  """
  try:
    parent_dir = os.path.dirname(config.LINK_CACHE_PATH)
    if parent_dir:
      os.makedirs(parent_dir, exist_ok=True)
    with open(config.LINK_CACHE_PATH, 'w', encoding='utf-8') as f:
      json.dump(cache, f, indent=2)
  except OSError as e:
    logger.error('Failed to save link check cache: %s', e)


def check_url(url: str) -> bool:
  """Checks if a URL is active by performing a HEAD or GET request.

  Args:
    url (str): The URL to test.

  Returns:
    bool: True if the URL is active, False otherwise.
  """
  headers = {'User-Agent': config.USER_AGENT}
  for method in ('HEAD', 'GET'):
    try:
      req = urllib.request.Request(url, headers=headers, method=method)
      with urllib.request.urlopen(req, timeout=5) as response:
        if response.status < 400:
          return True
    except (urllib.error.URLError, http.client.HTTPException, OSError,
            ValueError):
      continue
  return False


def verify_asset_filenames(
    asset_dirs: Sequence[str],
    ignore_dirs: Sequence[str] = IGNORED_ASSET_DIRS,
) -> List[str]:
  """Checks asset directories for filenames containing whitespace.

  Args:
    asset_dirs (Sequence[str]): Directories (e.g. image/, doc/) to scan.
    ignore_dirs (Sequence[str]): Staging directory basenames to skip.

  Returns:
    List[str]: Descriptions of any asset paths containing whitespace.
  """
  issues: List[str] = []
  for asset_dir in asset_dirs:
    if not os.path.exists(asset_dir):
      continue
    for root, dirs, files in os.walk(asset_dir):
      dirs[:] = [
          d for d in dirs if d not in ignore_dirs and not d.startswith('.')
      ]
      for name in sorted(dirs + files):
        if name.startswith('.'):
          continue
        if _WHITESPACE_RE.search(name):
          full_path = os.path.join(root, name)
          rel_path = os.path.relpath(full_path, config.BASE_DIR)
          issues.append(f'Asset filename contains whitespace: {rel_path}')
  return issues


def verify_local_links(
    html_path: str,
    base_dir: Optional[str] = None,
    check_anchors: bool = True,
) -> List[str]:
  """Validates local asset references, anchors, and URL encoding in HTML.

  Flags empty href/src attributes, unencoded whitespace, malformed percent
  escapes, local asset references containing spaces (%20), missing local files,
  and broken in-page #anchor links.

  Args:
    html_path (str): Path to the HTML file to validate.
    base_dir (Optional[str]): Root directory for resolving relative paths.
      Defaults to the directory containing html_path.
    check_anchors (bool): Whether to verify #anchor targets exist in HTML.

  Returns:
    List[str]: Human-readable validation error strings (empty if valid).
  """
  root_dir = base_dir or os.path.dirname(os.path.abspath(html_path))
  with open(html_path, 'r', encoding='utf-8') as f:
    parsed = _parse_html_refs(f.read())

  issues: List[str] = []
  for tag_name, attr_name, raw_val in parsed.refs:
    if not raw_val.strip():
      issues.append(f'Empty <{tag_name} {attr_name}=""> attribute')
      continue

    if _WHITESPACE_RE.search(raw_val):
      issues.append(
          f'Unencoded whitespace in <{tag_name} {attr_name}="{raw_val}">')

    if _BAD_PERCENT_RE.search(raw_val):
      issues.append(
          f'Malformed percent-encoding in '
          f'<{tag_name} {attr_name}="{raw_val}">')

    if raw_val.startswith('#'):
      target_id = raw_val[1:]
      if check_anchors and target_id and target_id not in parsed.element_ids:
        issues.append(f'Broken anchor link: {raw_val}')
      continue

    if raw_val.startswith(SKIPPED_SCHEMES):
      continue

    clean_ref = raw_val.split('?', 1)[0].split('#', 1)[0]
    decoded_ref = urllib.parse.unquote(clean_ref)
    if (_WHITESPACE_RE.search(decoded_ref) and
        not _WHITESPACE_RE.search(raw_val)):
      issues.append(f'Local path references spaced filename: {raw_val}')

    full_path = os.path.normpath(
        os.path.join(root_dir, decoded_ref.lstrip('/')))
    if not os.path.isfile(full_path):
      issues.append(
          f'Missing local file for <{tag_name} {attr_name}="{raw_val}">')

  return list(dict.fromkeys(issues))


def verify_links(html_path: str) -> List[str]:
  """Extracts and verifies local and external links from an HTML file.

  Args:
    html_path (str): Path to the HTML file to scan.

  Returns:
    List[str]: All detected local and external link issues.
  """
  try:
    local_issues = verify_local_links(html_path)
    with open(html_path, 'r', encoding='utf-8') as f:
      parsed = _parse_html_refs(f.read())
  except OSError as e:
    logger.error('Error reading HTML file %s: %s', html_path, e)
    return [str(e)]

  unique_urls = {
      val.strip()
      for tag, attr, val in parsed.refs
      if tag == 'a' and attr == 'href' and
      val.strip().startswith(('http://', 'https://'))
  }

  logger.info('Found %d unique external URLs to check.', len(unique_urls))
  logger.info('=' * 80)

  cache = load_link_cache()
  updated_cache: Dict[str, Any] = {}
  dead_links: List[str] = []
  current_time = time.time()

  for i, url in enumerate(sorted(unique_urls), 1):
    is_cached_active = False
    if url in cache:
      entry = cache[url]
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

  save_link_cache(updated_cache)

  all_issues = local_issues + dead_links
  logger.info('=' * 80)
  if all_issues:
    logger.warning('Scan completed. Found %d issues:', len(all_issues))
    for issue in all_issues:
      logger.warning(' - %s', issue)
  else:
    logger.info('Scan completed. All links are active (or cached active)!')
  return all_issues


def main(argv: Optional[Sequence[str]] = None) -> None:
  """CLI entry point for checking local and external site links.

  Args:
    argv (Optional[Sequence[str]]): Command-line arguments.
  """
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument(
      '--local-only',
      action='store_true',
      help='Only validate local HTML links and asset filenames (no network).',
  )
  args = parser.parse_args(argv)

  asset_issues = verify_asset_filenames((config.IMAGE_DIR, config.DOC_DIR))
  if args.local_only:
    local_issues = verify_local_links(config.HTML_PATH)
    issues = asset_issues + local_issues
    if issues:
      logger.warning('Found %d local link/asset issues:', len(issues))
      for issue in issues:
        logger.warning(' - %s', issue)
      sys.exit(1)
    logger.info('Local link and asset filename checks passed!')
    return

  link_issues = verify_links(config.HTML_PATH)
  for issue in asset_issues:
    logger.warning(' - %s', issue)
  if link_issues or asset_issues:
    sys.exit(1)


if __name__ == '__main__':
  main()
