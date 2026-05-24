"""Unit tests for the fetchers library."""

import json
import os
import unittest
from unittest.mock import MagicMock
from unittest.mock import patch
from processing.fetchers import ScholarFetcher
from processing.fetchers import GithubFetcher
from processing.fetchers import PatentsFetcher
from processing.fetchers import LinkedinFetcher


class TestFetchers(unittest.TestCase):
  """Tests for all profiles fetcher classes."""

  def setUp(self) -> None:
    self.temp_pub = 'temp_test_publications.md'
    self.temp_git = 'temp_test_github_projects.md'
    self.temp_pat = 'temp_test_patents.md'
    self.temp_lnk_in = 'temp_test_linkedin_raw.txt'
    self.temp_lnk_out = 'temp_test_linkedin_experience.md'
    self.temp_blg = 'temp_test_blogs.md'

  def tearDown(self) -> None:
    for path in (self.temp_pub, self.temp_git, self.temp_pat, self.temp_lnk_in,
                 self.temp_lnk_out, self.temp_blg):
      if os.path.exists(path):
        os.remove(path)

  @patch('urllib.request.urlopen')
  def test_scholar_fetcher(self, mock_urlopen: MagicMock) -> None:
    """Verifies ScholarFetcher parses Google Scholar rows correctly."""
    mock_html = (
        '<html><body><table>'
        '<tr class="gsc_a_tr">'
        '<td class="gsc_a_t">'
        '<a class="gsc_a_at" href="/citations?view_op=view_citation&citation_for_view=kXNcQegAAAAJ:1">Test Paper</a>'
        '<div class="gs_gray">Author A</div>'
        '<div class="gs_gray">Venue B</div>'
        '</td>'
        '<td><span class="gsc_a_y">2026</span></td>'
        '</tr>'
        '</table></body></html>')

    def mock_urlopen_side_effect(request, *args, **kwargs):
      url = request.full_url if hasattr(request, 'full_url') else str(request)
      resp = MagicMock()
      if 'crossref.org' in url:
        resp.read.return_value = b'{"message": {"items": []}}'
      else:
        resp.read.return_value = mock_html.encode('utf-8')
      resp.__enter__.return_value = resp
      return resp

    mock_urlopen.side_effect = mock_urlopen_side_effect

    fetcher = ScholarFetcher('dummy_id')
    fetcher.fetch_to_markdown(self.temp_pub)

    self.assertTrue(os.path.exists(self.temp_pub))
    with open(self.temp_pub, 'r', encoding='utf-8') as f:
      content = f.read()
    self.assertIn('2026', content)
    self.assertIn('Test Paper', content)

  @patch('urllib.request.urlopen')
  def test_github_fetcher(self, mock_urlopen: MagicMock) -> None:
    """Verifies GithubFetcher formats repository details and commits logs."""
    mock_repos_json = [{
        'name': 'test-repo',
        'fork': False,
        'description': 'Description',
        'html_url': 'https://github.com/dummy/test-repo',
        'updated_at': '2026-05-23T12:00:00Z',
        'language': 'Python',
        'stargazers_count': 5
    }]
    mock_commits_json = [{
        'sha': '1234567890abcdef',
        'commit': {
            'message': 'Mock commit',
            'author': {
                'date': '2026-05-23T11:00:00Z'
            }
        }
    }]
    mock_repos_resp = MagicMock()
    mock_repos_resp.read.return_value = json.dumps(mock_repos_json).encode(
        'utf-8')
    mock_commits_resp = MagicMock()
    mock_commits_resp.read.return_value = json.dumps(mock_commits_json).encode(
        'utf-8')

    mock_urlopen.return_value.__enter__.side_effect = [
        mock_repos_resp, mock_commits_resp
    ]

    fetcher = GithubFetcher('dummy_user')
    fetcher.fetch_to_markdown(self.temp_git, limit_repos=1)

    self.assertTrue(os.path.exists(self.temp_git))
    with open(self.temp_git, 'r', encoding='utf-8') as f:
      content = f.read()
    self.assertIn('test-repo', content)
    self.assertIn('Mock commit', content)

  @patch('urllib.request.urlopen')
  def test_patents_fetcher_fallback(self, mock_urlopen: MagicMock) -> None:
    """Verifies PatentsFetcher fallback when static HTML results are not matched."""
    mock_html = '<html><body>No static results found</body></html>'
    mock_response = MagicMock()
    mock_response.read.return_value = mock_html.encode('utf-8')
    mock_urlopen.return_value.__enter__.return_value = mock_response

    fetcher = PatentsFetcher()
    fetcher.fetch_to_markdown(self.temp_pat)

    self.assertTrue(os.path.exists(self.temp_pat))
    with open(self.temp_pat, 'r', encoding='utf-8') as f:
      content = f.read()
    self.assertIn('US Patent 11,862,188', content)

  @patch('processing.fetchers.LinkedinFetcher.fetch_from_web')
  def test_linkedin_fetcher(self, mock_fetch_web: MagicMock) -> None:
    """Verifies LinkedinFetcher converts raw copy-pasted text into markdown."""
    mock_fetch_web.return_value = None
    raw_text = ('Experience\n'
                'Research Engineer\n'
                'Google · Full-time\n'
                'Oct 2017 - Present · 8 yrs\n'
                'Seattle Area\n'
                'Specializing in health sensing AI.')
    with open(self.temp_lnk_in, 'w', encoding='utf-8') as f:
      f.write(raw_text)

    fetcher = LinkedinFetcher()
    fetcher.fetch_to_markdown(self.temp_lnk_in, self.temp_lnk_out)

    self.assertTrue(os.path.exists(self.temp_lnk_out))
    with open(self.temp_lnk_out, 'r', encoding='utf-8') as f:
      content = f.read()
    self.assertIn('Research Engineer', content)
    self.assertIn('Google · Full-time', content)

  def test_blog_fetcher(self) -> None:
    """Verifies BlogFetcher writes blog posts table to Markdown."""
    from processing.fetchers import BlogFetcher
    fetcher = BlogFetcher()
    fetcher.fetch_to_markdown(self.temp_blg)

    self.assertTrue(os.path.exists(self.temp_blg))
    with open(self.temp_blg, 'r', encoding='utf-8') as f:
      content = f.read()
    self.assertIn('Accelerating scientific discovery', content)
    self.assertIn('SensorLM: Learning the language', content)


if __name__ == '__main__':
  unittest.main()
