"""Unit tests for the image importer and metadata library."""

import unittest
from processing.import_images import IMAGE_METADATA


class ImportImagesTest(unittest.TestCase):
  """Checks image importer metadata layouts and configuration keys."""

  def test_metadata_structure(self):
    """Verifies that all entries in IMAGE_METADATA conform to schema."""
    self.assertIsInstance(IMAGE_METADATA, dict)
    self.assertGreater(len(IMAGE_METADATA), 0)

    for src_file, targets in IMAGE_METADATA.items():
      self.assertTrue(src_file.endswith(('.png', '.jpg', '.jpeg', '.webp')))
      self.assertIsInstance(targets, list)
      self.assertGreater(len(targets), 0)

      for target in targets:
        self.assertIn('target_name', target)
        self.assertIn('target_ratio', target)
        self.assertIn('description', target)

        self.assertTrue(target['target_name'].endswith(('.jpg', '.jpeg', '.png')))
        self.assertGreater(target['target_ratio'], 0.0)
        self.assertIsInstance(target['description'], str)


if __name__ == '__main__':
  unittest.main()
