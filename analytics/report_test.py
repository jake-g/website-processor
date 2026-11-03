"""Tests for the offline analytics report."""

import csv
import os
import tempfile
import unittest
from unittest import mock

from processing.analytics import pull
from processing.analytics import report


class ReportTest(unittest.TestCase):

  def setUp(self):
    super().setUp()
    self._tmp = tempfile.TemporaryDirectory()
    self.addCleanup(self._tmp.cleanup)
    patcher = mock.patch.object(pull, 'OUT_DIR', self._tmp.name)
    patcher.start()
    self.addCleanup(patcher.stop)

  def _write(self, name, header, rows):
    with open(os.path.join(self._tmp.name, f'{name}.csv'), 'w',
              newline='', encoding='utf-8') as f:
      w = csv.writer(f)
      w.writerow(header)
      w.writerows(rows)

  def test_name_query_by_page_weights_position(self):
    self._write('gsc_query_page',
                ['query', 'page', 'clicks', 'impressions', 'ctr', 'position'],
                [['jake garrison', '/doc/r.pdf', 5, 100, 0.05, 2.0],
                 ['Jake Garrison', '/', 1, 50, 0.02, 6.0],
                 ['jake garrison', '/', 1, 50, 0.02, 4.0],
                 ['spirometry', '/', 9, 900, 0.01, 1.0]])
    rows = report.name_query_by_page()
    self.assertEqual([r['page'] for r in rows], ['/doc/r.pdf', '/'])
    self.assertAlmostEqual(rows[1]['position'], 5.0)
    self.assertEqual(rows[1]['impressions'], 100)

  def test_yearly_traffic(self):
    self._write('ga4_daily',
                ['date', 'activeUsers', 'sessions', 'screenPageViews',
                 'engagementRate'],
                [['20240101', 2, 3, 4, 0.5], ['20240102', 1, 1, 1, 0.5],
                 ['20250101', 7, 7, 7, 0.5]])
    years = report.yearly_traffic()
    self.assertEqual(years['2024']['users'], 3)
    self.assertEqual(years['2025']['views'], 7)

  def test_build_markdown_handles_missing_files(self):
    md = report.build_markdown()
    self.assertIn('# jakegarrison.me analytics summary', md)


if __name__ == '__main__':
  unittest.main()
