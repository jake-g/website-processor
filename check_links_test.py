"""Unit tests for the check_links module."""

import os
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch
from processing.check_links import check_url
from processing.check_links import verify_links


class TestCheckLinks(unittest.TestCase):
  """Tests for the check_links module functions."""

  def setUp(self) -> None:
    self.test_cache = 'temp_test_link_cache.json'
    self.patcher_cache = patch('processing.config.LINK_CACHE_PATH',
                               self.test_cache)
    self.patcher_cache.start()

  def tearDown(self) -> None:
    self.patcher_cache.stop()
    if os.path.exists(self.test_cache):
      os.remove(self.test_cache)

  @patch('urllib.request.urlopen')
  def test_check_url_active(self, mock_urlopen: MagicMock) -> None:
    """Verifies that an active URL returns True."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_urlopen.return_value.__enter__.return_value = mock_resp

    self.assertTrue(check_url('https://example.com/active'))

  @patch('urllib.request.urlopen')
  def test_check_url_dead(self, mock_urlopen: MagicMock) -> None:
    """Verifies that a dead URL (raising exception) returns False."""
    mock_urlopen.side_effect = Exception('HTTP Error 404')
    self.assertFalse(check_url('https://example.com/dead'))

  @patch('processing.check_links.check_url')
  def test_verify_links(self, mock_check_url: MagicMock) -> None:
    """Verifies that links are verified and dead links are logged."""
    mock_check_url.side_effect = lambda url: 'dead' not in url

    # Create dummy HTML content
    dummy_html = ('<html><body>'
                  '<a href="https://example.com/active">Active Link</a>'
                  '<a href="https://example.com/dead-link">Dead Link</a>'
                  '<a href="#anchor">Anchor Link (Skip)</a>'
                  '</body></html>')

    temp_html_path = 'temp_test_links.html'
    with open(temp_html_path, 'w', encoding='utf-8') as f:
      f.write(dummy_html)

    try:
      with patch('logging.Logger.warning') as mock_log_warn:
        verify_links(temp_html_path)
        # Check that warning was called for the dead link
        mock_log_warn.assert_any_call(' - %s', 'https://example.com/dead-link')
    finally:
      if os.path.exists(temp_html_path):
        os.remove(temp_html_path)


if __name__ == '__main__':
  unittest.main()
