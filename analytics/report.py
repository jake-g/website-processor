"""Local summary of exported analytics CSVs (no network).

Answers the main question: for searches like "jake garrison", does the
homepage or the resume PDF get more impressions/clicks and better position?

Usage:
  PYTHONPATH=.. python3 -m processing.analytics.report
"""

import collections
import csv
import logging
import os
from typing import Dict, Iterator, List

from processing.analytics import pull

logger = logging.getLogger(__name__)

NAME_TERMS = ('jake garrison', 'garrison jake', 'jakegarrison')
REPORT_PATH = os.path.join(pull.OUT_DIR, 'summary.md')


def read_csv(name: str) -> Iterator[Dict[str, str]]:
  """Yields rows of an exported CSV, or nothing if it is missing.

  Args:
    name (str): Report name (file stem).

  Yields:
    Dict[str, str]: One CSV row.
  """
  path = os.path.join(pull.OUT_DIR, f'{name}.csv')
  if not os.path.exists(path):
    logger.warning('Missing %s (run `make analytics-pull`).', path)
    return
  with open(path, newline='', encoding='utf-8') as f:
    yield from csv.DictReader(f)


def name_query_by_page() -> List[Dict[str, float]]:
  """Aggregates name-search performance per landing page.

  Returns:
    List[Dict[str, float]]: Rows with page, clicks, impressions, avg position
    (impression-weighted), sorted by impressions.
  """
  agg = collections.defaultdict(lambda: [0.0, 0.0, 0.0])
  for row in read_csv('gsc_query_page'):
    if not any(t in row['query'].lower() for t in NAME_TERMS):
      continue
    imp = float(row['impressions'])
    a = agg[row['page']]
    a[0] += float(row['clicks'])
    a[1] += imp
    a[2] += float(row['position']) * imp
  out = [{'page': p, 'clicks': c, 'impressions': i,
          'position': (w / i) if i else 0.0}
         for p, (c, i, w) in agg.items()]
  return sorted(out, key=lambda r: -r['impressions'])


def yearly_traffic() -> Dict[str, Dict[str, float]]:
  """Sums GA4 daily metrics per year.

  Returns:
    Dict[str, Dict[str, float]]: year -> {users, sessions, views}.
  """
  years: Dict[str, Dict[str, float]] = collections.defaultdict(
      lambda: {'users': 0.0, 'sessions': 0.0, 'views': 0.0})
  for row in read_csv('ga4_daily'):
    y = years[row['date'][:4]]
    y['users'] += float(row['activeUsers'])
    y['sessions'] += float(row['sessions'])
    y['views'] += float(row['screenPageViews'])
  return dict(sorted(years.items()))


def top_rows(name: str, metric: str, n: int = 15) -> List[Dict[str, str]]:
  """Returns the top-n rows of a CSV by a numeric metric.

  Args:
    name (str): Report name.
    metric (str): Column to sort by.
    n (int): Number of rows.

  Returns:
    List[Dict[str, str]]: Top rows.
  """
  rows = list(read_csv(name))
  return sorted(rows, key=lambda r: -float(r[metric] or 0))[:n]


def build_markdown() -> str:
  """Builds the markdown summary.

  Returns:
    str: Markdown text.
  """
  lines = ['# jakegarrison.me analytics summary', '']
  lines += ['## Name searches by landing page (Search Console)', '',
            '| Page | Clicks | Impressions | Avg position |',
            '|---|---:|---:|---:|']
  for r in name_query_by_page()[:15]:
    lines.append(f"| {r['page']} | {r['clicks']:.0f} | "
                 f"{r['impressions']:.0f} | {r['position']:.1f} |")
  lines += ['', '## Traffic by year (GA4)', '',
            '| Year | Users | Sessions | Views |', '|---|---:|---:|---:|']
  for year, m in yearly_traffic().items():
    lines.append(f"| {year} | {m['users']:.0f} | {m['sessions']:.0f} | "
                 f"{m['views']:.0f} |")
  sections = (
      ('Top sources (GA4)', 'ga4_source', 'sessionSourceMedium', 'sessions'),
      ('Top events (GA4)', 'ga4_events', 'eventName', 'eventCount'),
      ('Section views (GA4)', 'ga4_sections', 'customEvent:section',
       'eventCount'),
      ('Top queries (Search Console)', 'gsc_query_page', 'query',
       'impressions'),
  )
  for title, name, key, metric in sections:
    lines += ['', f'## {title}', '', f'| {key} | {metric} |', '|---|---:|']
    for r in top_rows(name, metric):
      lines.append(f'| {r[key]} | {float(r[metric]):.0f} |')
  return '\n'.join(lines) + '\n'


def main() -> None:
  """CLI entry point."""
  logging.basicConfig(level=logging.INFO, format='%(message)s')
  os.makedirs(pull.OUT_DIR, exist_ok=True)
  with open(REPORT_PATH, 'w', encoding='utf-8') as f:
    f.write(build_markdown())
  logger.info('Wrote %s', REPORT_PATH)


if __name__ == '__main__':
  main()
