"""Unit tests for the PageBuilder compilation class."""

import os
import unittest
from processing.builder import PageBuilder


class TestPageBuilder(unittest.TestCase):
  """Tests for PageBuilder class operations."""

  def setUp(self) -> None:
    self.temp_template = 'temp_test_template.html'
    self.temp_output = 'temp_test_output.html'

    # Simple base HTML template
    self.base_html = ('<!DOCTYPE html>\n'
                      '<html>\n'
                      '  <body>\n'
                      '    <h4>Bots &amp; Automation</h4>\n'
                      '    <img src="image/test.jpg" alt="">\n'
                      '    <p>Replace me 1. Replace me 2.</p>\n'
                      '  </body>\n'
                      '</html>\n')
    with open(self.temp_template, 'w', encoding='utf-8') as f:
      f.write(self.base_html)

  def tearDown(self) -> None:
    for path in (self.temp_template, self.temp_output):
      if os.path.exists(path):
        os.remove(path)

  def test_from_string(self) -> None:
    """Verifies creating PageBuilder from in-memory string content."""
    builder = PageBuilder.from_string("<div>Test</div>")
    self.assertEqual(builder.html, "<div>Test</div>")
    self.assertIsNone(builder.template_path)

  def test_string_replace(self) -> None:
    """Verifies string replacement with count limit constraints."""
    builder = PageBuilder(self.temp_template)

    # Replace only the first occurrence
    builder.replace('Replace me', 'Replaced', count=1)
    self.assertIn('Replaced 1.', builder.html)
    self.assertIn('Replace me 2.', builder.html)

    # Replace all occurrences
    builder.replace('Replace me', 'Replaced')
    self.assertIn('Replaced 2.', builder.html)

  def test_regex_replace(self) -> None:
    """Verifies regex pattern substitution."""
    builder = PageBuilder(self.temp_template)
    builder.replace_pattern(r'<p>.*?</p>', '<p>New Content</p>')
    self.assertIn('<p>New Content</p>', builder.html)
    self.assertNotIn('Replace me 1.', builder.html)

  def test_lazy_loading(self) -> None:
    """Verifies image lazy loading injection."""
    builder = PageBuilder(self.temp_template)
    builder.enable_lazy_loading()
    self.assertIn('<img loading="lazy" src="image/test.jpg" alt="">',
                  builder.html)

  def test_normalize_headers(self) -> None:
    """Verifies header character normalization (ampersand to 'and')."""
    builder = PageBuilder(self.temp_template)
    builder.normalize_headers()
    self.assertIn('<h4>Bots and Automation</h4>', builder.html)
    self.assertNotIn('<h4>Bots &amp; Automation</h4>', builder.html)

  def test_save_and_format(self) -> None:
    """Verifies compiling and formatting saved file on disk."""
    builder = PageBuilder(self.temp_template)
    builder.replace('Replace me 1. Replace me 2.</p>', 'Final content</p>   ')

    # Save and run formatting check
    builder.save(self.temp_output, format_content=True)

    self.assertTrue(os.path.exists(self.temp_output))
    with open(self.temp_output, 'r', encoding='utf-8') as f:
      content = f.read()

    # Formatter should strip trailing spaces from the end of the line
    self.assertIn('    <p>Final content</p>\n', content)


if __name__ == '__main__':
  unittest.main()
