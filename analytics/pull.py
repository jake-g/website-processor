"""Pulls Google Analytics 4 and Search Console data for jakegarrison.me.

Raw exports land in ``processing/outputs/analytics/`` which is gitignored,
because ``processing/`` is served publicly by GitHub Pages.

Auth (pick one):
  1. Service account JSON at ``processing/analytics/secrets/sa.json``
     (gitignored). Add its email as a Viewer on the GA4 property and as a
     user on the Search Console property.
  2. Application Default Credentials from your personal account:
       gcloud auth application-default login --scopes=\
https://www.googleapis.com/auth/analytics.readonly,\
https://www.googleapis.com/auth/webmasters.readonly,\
https://www.googleapis.com/auth/cloud-platform

Usage:
  PYTHONPATH=.. python3 -m processing.analytics.pull [--start 2020-01-01]
"""

import argparse
import csv
import datetime
import logging
import os
from typing import Any, Dict, Iterable, List, Sequence

from processing import config

logger = logging.getLogger(__name__)

SCOPES = (
    'https://www.googleapis.com/auth/analytics.readonly',
    'https://www.googleapis.com/auth/webmasters.readonly',
)
SECRETS_DIR = os.path.join(os.path.dirname(__file__), 'secrets')
SERVICE_ACCOUNT_PATH = os.path.join(SECRETS_DIR, 'sa.json')
OUT_DIR = os.path.join(config.OUTPUTS_DIR, 'analytics')

# GA4 numeric property ID (Admin > Property settings), NOT the G- tag.
GA4_PROPERTY_ID = os.environ.get('GA4_PROPERTY_ID', '404174353')
# Search Console property ('sc-domain:...' or 'https://.../'); auto-detected
# from the properties the credentials can see when unset.
GSC_SITE_URL = os.environ.get('GSC_SITE_URL', '')
GSC_DOMAIN = 'jakegarrison.me'

# (name, dimensions, metrics) for GA4 reports.
GA4_REPORTS = (
    ('ga4_daily', ['date'],
     ['activeUsers', 'sessions', 'screenPageViews', 'engagementRate']),
    ('ga4_source', ['sessionSourceMedium'],
     ['sessions', 'activeUsers', 'engagementRate']),
    ('ga4_pages', ['pagePath'], ['screenPageViews', 'activeUsers']),
    ('ga4_events', ['eventName', 'linkUrl'], ['eventCount']),
    ('ga4_geo', ['country', 'city'], ['activeUsers']),
    ('ga4_device', ['deviceCategory'], ['activeUsers', 'sessions']),
    # Needs event-scoped custom dimension "section" registered in GA4.
    ('ga4_sections', ['customEvent:section'], ['eventCount']),
)

# (name, dimensions) for Search Console reports.
GSC_REPORTS = (
    ('gsc_query_page', ['query', 'page']),
    ('gsc_page', ['page']),
    ('gsc_page_daily', ['date', 'page']),
)


def get_credentials() -> Any:
  """Returns Google credentials from a service account or ADC.

  Returns:
    google.auth.credentials.Credentials: Credentials with read scopes.
  """
  if os.path.exists(SERVICE_ACCOUNT_PATH):
    from google.oauth2 import service_account  # pylint: disable=g-import-not-at-top
    logger.info('Using service account %s', SERVICE_ACCOUNT_PATH)
    return service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_PATH, scopes=SCOPES)
  import google.auth  # pylint: disable=g-import-not-at-top
  logger.info('Using application default credentials')
  creds, _ = google.auth.default(scopes=SCOPES)
  return creds


def write_csv(name: str, header: Sequence[str],
              rows: Iterable[Sequence[Any]]) -> str:
  """Writes rows to ``OUT_DIR/<name>.csv``.

  Args:
    name (str): Report name (file stem).
    header (Sequence[str]): Column names.
    rows (Iterable[Sequence[Any]]): Row values.

  Returns:
    str: Path of the written file.
  """
  os.makedirs(OUT_DIR, exist_ok=True)
  path = os.path.join(OUT_DIR, f'{name}.csv')
  count = 0
  with open(path, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    for row in rows:
      writer.writerow(row)
      count += 1
  logger.info('Wrote %d rows -> %s', count, path)
  return path


def pull_ga4(creds: Any, start: str, end: str) -> None:
  """Exports GA4 reports to CSV.

  Args:
    creds (Any): Google credentials.
    start (str): Start date YYYY-MM-DD.
    end (str): End date YYYY-MM-DD.

  Raises:
    ValueError: If GA4_PROPERTY_ID is not configured.
  """
  if not GA4_PROPERTY_ID:
    raise ValueError('Set GA4_PROPERTY_ID (numeric) env var.')
  # pylint: disable=g-import-not-at-top
  from google.analytics.data_v1beta import BetaAnalyticsDataClient
  from google.analytics.data_v1beta import types
  from google.api_core import exceptions
  # pylint: enable=g-import-not-at-top
  client = BetaAnalyticsDataClient(credentials=creds)
  for name, dims, mets in GA4_REPORTS:
    try:
      rows = _run_ga4_report(client, types, dims, mets, start, end)
    except exceptions.InvalidArgument as e:
      logger.warning('Skipping %s: %s', name, e.message)
      continue
    write_csv(name, dims + mets, rows)


def _run_ga4_report(client: Any, types: Any, dims: List[str],
                    mets: List[str], start: str, end: str) -> List[List[str]]:
  """Runs one paginated GA4 report.

  Args:
    client (Any): BetaAnalyticsDataClient.
    types (Any): The data_v1beta types module.
    dims (List[str]): Dimension names.
    mets (List[str]): Metric names.
    start (str): Start date YYYY-MM-DD.
    end (str): End date YYYY-MM-DD.

  Returns:
    List[List[str]]: Rows of dimension then metric values.
  """
  rows: List[List[str]] = []
  offset = 0
  while True:
    resp = client.run_report(types.RunReportRequest(
        property=f'properties/{GA4_PROPERTY_ID}',
        dimensions=[types.Dimension(name=d) for d in dims],
        metrics=[types.Metric(name=m) for m in mets],
        date_ranges=[types.DateRange(start_date=start, end_date=end)],
        limit=100000, offset=offset))
    for r in resp.rows:
      rows.append([v.value for v in r.dimension_values] +
                  [v.value for v in r.metric_values])
    offset += len(resp.rows)
    if not resp.rows or offset >= resp.row_count:
      return rows


def detect_gsc_site(service: Any) -> str:
  """Picks the Search Console property for GSC_DOMAIN, preferring Domain.

  Args:
    service (Any): Search Console API client.

  Returns:
    str: Property identifier.

  Raises:
    ValueError: If no matching property is shared with the credentials.
  """
  sites = [e['siteUrl'] for e in
           service.sites().list().execute().get('siteEntry', [])]
  matches = sorted((s for s in sites if GSC_DOMAIN in s),
                   key=lambda s: not s.startswith('sc-domain:'))
  if not matches:
    raise ValueError(f'No Search Console property for {GSC_DOMAIN} is '
                     f'shared with these credentials (saw {sites}).')
  return matches[0]


def pull_gsc(creds: Any, start: str, end: str) -> None:
  """Exports Search Console performance reports to CSV.

  Search Console only retains ~16 months of data.

  Args:
    creds (Any): Google credentials.
    start (str): Start date YYYY-MM-DD.
    end (str): End date YYYY-MM-DD.
  """
  from googleapiclient.discovery import build  # pylint: disable=g-import-not-at-top
  service = build('searchconsole', 'v1', credentials=creds,
                  cache_discovery=False)
  site_url = GSC_SITE_URL or detect_gsc_site(service)
  logger.info('Search Console property: %s', site_url)
  metrics = ['clicks', 'impressions', 'ctr', 'position']
  for name, dims in GSC_REPORTS:
    rows: List[List[Any]] = []
    start_row = 0
    while True:
      body: Dict[str, Any] = {
          'startDate': start, 'endDate': end, 'dimensions': dims,
          'rowLimit': 25000, 'startRow': start_row}
      resp = service.searchanalytics().query(
          siteUrl=site_url, body=body).execute()
      batch = resp.get('rows', [])
      for r in batch:
        rows.append(list(r['keys']) + [r.get(m) for m in metrics])
      start_row += len(batch)
      if len(batch) < 25000:
        break
    write_csv(name, dims + metrics, rows)


def main() -> None:
  """CLI entry point."""
  logging.basicConfig(level=logging.INFO, format='%(message)s')
  today = datetime.date.today()
  parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  parser.add_argument('--start', default='2015-08-14',
                      help='GA4 start date (GA4 clamps to property start).')
  parser.add_argument('--end', default=today.isoformat())
  parser.add_argument('--only', choices=('ga4', 'gsc'), default=None)
  args = parser.parse_args()

  creds = get_credentials()
  if args.only in (None, 'ga4'):
    pull_ga4(creds, args.start, args.end)
  if args.only in (None, 'gsc'):
    gsc_start = max(datetime.date.fromisoformat(args.start),
                    today - datetime.timedelta(days=486))
    pull_gsc(creds, gsc_start.isoformat(), args.end)


if __name__ == '__main__':
  main()
