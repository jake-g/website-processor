"""Unit tests for the compressors library."""

import json
import os
import shutil
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch
from processing.compressors import WebMinifier
from processing.compressors import ImageCompressor
from processing.compressors import PdfCompressor


class TestCompressors(unittest.TestCase):
  """Tests for all compressors and minifiers classes."""

  def setUp(self) -> None:
    self.test_dir = 'temp_test_assets'
    os.makedirs(self.test_dir, exist_ok=True)

    self.temp_css_in = os.path.join(self.test_dir, 'input.css')
    self.temp_css_out = os.path.join(self.test_dir, 'output.css')

    # Patch the single cache path inside config to point to our test folder
    self.patcher_cache = patch(
        'processing.config.COMPRESS_CACHE_PATH',
        os.path.join(self.test_dir, 'test_compress_cache.json'))
    self.patcher_cache.start()

  def tearDown(self) -> None:
    self.patcher_cache.stop()
    if os.path.exists(self.test_dir):
      shutil.rmtree(self.test_dir)

  def test_web_minifier(self) -> None:
    """Verifies WebMinifier removes comments and whitespace from CSS."""
    raw_css = '/* comment */ body { color: #333; }'
    expected_css = 'body{color:#333;}'
    with open(self.temp_css_in, 'w', encoding='utf-8') as f:
      f.write(raw_css)

    minifier = WebMinifier()
    minifier.minify_css(self.temp_css_in, self.temp_css_out)

    self.assertTrue(os.path.exists(self.temp_css_out))
    with open(self.temp_css_out, 'r', encoding='utf-8') as f:
      minified = f.read()
    self.assertEqual(minified, expected_css)

  @patch('processing.compressors.ImageCompressor._compress_file')
  def test_image_compressor_thresholds(self, mock_compress: MagicMock) -> None:
    """Verifies that ImageCompressor only compresses images exceeding 250KB."""
    mock_compress.return_value = True

    small_img = os.path.join(self.test_dir, 'small.jpg')
    with open(small_img, 'w') as f:
      f.write('x' * 100)

    large_img = os.path.join(self.test_dir, 'large.jpg')
    with open(large_img, 'w') as f:
      f.write('x' * (260 * 1024))

    comp = ImageCompressor(self.test_dir)
    comp.run()

    mock_compress.assert_called_once()
    args, _ = mock_compress.call_args
    self.assertEqual(os.path.basename(args[0]), 'large.jpg')

  @patch('processing.compressors.PdfCompressor._is_gs_available')
  @patch('processing.compressors.PdfCompressor._compress_file')
  def test_pdf_compressor_thresholds(self, mock_compress: MagicMock,
                                     mock_gs: MagicMock) -> None:
    """Verifies that PdfCompressor only targets PDFs exceeding 1.5MB."""
    mock_gs.return_value = True

    def mock_compress_side_effect(input_path, output_path):
      with open(output_path, 'w') as f:
        f.write('compressed PDF data')
      return True

    mock_compress.side_effect = mock_compress_side_effect

    small_pdf = os.path.join(self.test_dir, 'small.pdf')
    with open(small_pdf, 'w') as f:
      f.write('x' * 100)

    large_pdf = os.path.join(self.test_dir, 'large.pdf')
    with open(large_pdf, 'w') as f:
      f.write('x' * int(1.6 * 1024 * 1024))

    comp = PdfCompressor(self.test_dir)
    comp.run()

    mock_compress.assert_called_once()
    args, _ = mock_compress.call_args
    self.assertEqual(os.path.basename(args[0]), 'large.pdf')


if __name__ == '__main__':
  unittest.main()
