"""Unit tests for the format formatting utility."""

import os
import unittest
from processing.format import format_web_file


class TestFormatWeb(unittest.TestCase):
  """Tests for format_web utility functions."""

  def setUp(self) -> None:
    self.temp_file = 'temp_test_format.html'

  def tearDown(self) -> None:
    if os.path.exists(self.temp_file):
      os.remove(self.temp_file)

  def test_format_web_file(self) -> None:
    """Verifies that line endings are normalized and trailing spaces are stripped."""
    raw_content = ('<!DOCTYPE html>\r\n'
                   '<html>   \r\n'
                   '  <body>\r\n'
                   '    <h1>Title</h1>  \n'
                   '  </body>\r\n'
                   '</html>\r\n\r\n')
    expected_content = ('<!DOCTYPE html>\n'
                        '<html>\n'
                        '  <body>\n'
                        '    <h1>Title</h1>\n'
                        '  </body>\n'
                        '</html>\n')

    with open(self.temp_file, 'wb') as f:
      f.write(raw_content.encode('utf-8'))

    format_web_file(self.temp_file)

    self.assertTrue(os.path.exists(self.temp_file))
    with open(self.temp_file, 'rb') as f:
      formatted = f.read().decode('utf-8')

    self.assertEqual(formatted, expected_content)


if __name__ == '__main__':
  unittest.main()
