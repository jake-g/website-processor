"""Unit tests for the check_links module."""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from processing import config
from processing.check_links import check_url
from processing.check_links import verify_asset_filenames
from processing.check_links import verify_links
from processing.check_links import verify_local_links


class TestCheckLinks(unittest.TestCase):
  """Tests for the check_links module functions."""

  def setUp(self) -> None:
    self.temp_dir = tempfile.mkdtemp()
    self.test_cache = os.path.join(self.temp_dir, 'link_cache.json')
    self.patcher_cache = patch('processing.config.LINK_CACHE_PATH',
                               self.test_cache)
    self.patcher_cache.start()

  def tearDown(self) -> None:
    self.patcher_cache.stop()
    if os.path.exists(self.temp_dir):
      shutil.rmtree(self.temp_dir)

  @patch('urllib.request.urlopen')
  def test_check_url_active(self, mock_urlopen: MagicMock) -> None:
    """Verifies that an active URL returns True."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    self.assertTrue(check_url('https://example.com/active'))

  @patch('urllib.request.urlopen')
  def test_check_url_dead(self, mock_urlopen: MagicMock) -> None:
    """Verifies that a dead URL returns False."""
    mock_urlopen.side_effect = OSError('HTTP Error 404')
    self.assertFalse(check_url('https://example.com/dead'))

  @patch('processing.check_links.check_url')
  def test_verify_links(self, mock_check_url: MagicMock) -> None:
    """Verifies that links are verified and dead links are logged."""
    mock_check_url.side_effect = lambda url: 'dead' not in url

    dummy_html = ('<html><body>'
                  '<div id="anchor"></div>'
                  '<a href="https://example.com/active">Active Link</a>'
                  '<a href="https://example.com/dead-link">Dead Link</a>'
                  '<a href="#anchor">Anchor Link (Skip)</a>'
                  '</body></html>')

    temp_html_path = os.path.join(self.temp_dir, 'links.html')
    with open(temp_html_path, 'w', encoding='utf-8') as f:
      f.write(dummy_html)

    with patch('logging.Logger.warning') as mock_log_warn:
      verify_links(temp_html_path)
      mock_log_warn.assert_any_call(' - %s', 'https://example.com/dead-link')

  def test_verify_local_links_catches_bugs(self) -> None:
    """Verifies missing files, empty hrefs, spaces, and bad escapes fail."""
    doc_dir = os.path.join(self.temp_dir, 'doc')
    os.makedirs(doc_dir, exist_ok=True)
    with open(os.path.join(doc_dir, 'valid_paper.pdf'), 'wb') as f:
      f.write(b'%PDF-1.4')
    with open(os.path.join(doc_dir, 'spaced paper.pdf'), 'wb') as f:
      f.write(b'%PDF-1.4')

    html_path = os.path.join(self.temp_dir, 'index.html')
    html = (
        '<html><body>'
        '<div id="about"></div>'
        '<a href="#about">OK Anchor</a>'
        '<a href="doc/valid_paper.pdf">OK Local</a>'
        '<a href="">Empty Href</a>'
        '<a href="missing_prefix.pdf">Missing File</a>'
        '<a href="doc/spaced paper.pdf">Raw Space</a>'
        '<a href="doc/spaced%20paper.pdf">Encoded Space</a>'
        '<a href="doc/Towards%20Accurate%">Bad Escape</a>'
        '<a href="#nonexistent">Broken Anchor</a>'
        '</body></html>')
    with open(html_path, 'w', encoding='utf-8') as f:
      f.write(html)

    issues = verify_local_links(html_path)
    self.assertTrue(any('Empty <a href="">' in i for i in issues))
    self.assertTrue(any('missing_prefix.pdf' in i for i in issues))
    self.assertTrue(any('Unencoded whitespace' in i for i in issues))
    self.assertTrue(any('spaced filename' in i for i in issues))
    self.assertTrue(any('Malformed percent-encoding' in i for i in issues))
    self.assertTrue(
        any('Broken anchor link: #nonexistent' in i for i in issues))

  def test_verify_asset_filenames(self) -> None:
    """Verifies spaced asset filenames are caught while staging dirs skip."""
    doc_dir = os.path.join(self.temp_dir, 'doc')
    staging_dir = os.path.join(self.temp_dir, 'image', 'orig_image')
    os.makedirs(doc_dir, exist_ok=True)
    os.makedirs(staging_dir, exist_ok=True)

    with open(os.path.join(doc_dir, 'clean_name.pdf'), 'wb') as f:
      f.write(b'ok')
    with open(os.path.join(doc_dir, 'bad name.pdf'), 'wb') as f:
      f.write(b'bad')
    with open(os.path.join(staging_dir, 'raw screenshot.png'), 'wb') as f:
      f.write(b'staging')

    issues = verify_asset_filenames(
        (doc_dir, os.path.join(self.temp_dir, 'image')))
    self.assertEqual(len(issues), 1)
    self.assertIn('bad name.pdf', issues[0])

  def test_live_site_local_links_and_assets(self) -> None:
    """Guards repository index.html and asset folders against regressions."""
    if not os.path.exists(config.HTML_PATH):
      self.skipTest('index.html not present outside main website checkout.')
    self.assertEqual(verify_local_links(config.HTML_PATH), [])
    self.assertEqual(
        verify_asset_filenames((config.IMAGE_DIR, config.DOC_DIR)), [])


if __name__ == '__main__':
  unittest.main()
