"""Structured fetching library to sync academic and professional profiles."""

import json
import logging
import os
import re
import urllib.parse
import urllib.request
from bs4 import BeautifulSoup
from processing import config

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class ScholarFetcher:
  """Fetcher for Google Scholar publication listings."""

  def __init__(self, scholar_id: str):
    self.scholar_id = scholar_id

  def _normalize_title(self, title: str) -> str:
    """Normalizes title strings to allow robust deduplication checks."""
    return re.sub(r'[^a-z0-9]', '', title.lower())

  def fetch_to_markdown(self, output_path: str) -> None:
    """Fetches publications from profile and crossref search, writes Markdown."""
    url = (f'https://scholar.google.com/citations?user={self.scholar_id}'
           f'&hl=en&pagesize=100&sortby=pubdate')
    headers = {'User-Agent': config.USER_AGENT}

    logger.info('Querying Google Scholar ID: %s', self.scholar_id)
    req = urllib.request.Request(url, headers=headers)
    try:
      with urllib.request.urlopen(req, timeout=10) as response:
        html = response.read()

      soup = BeautifulSoup(html, 'html.parser')
      rows = soup.find_all('tr', class_='gsc_a_tr')

      if not rows:
        logger.warning('No publications found on Scholar profile.')
        return

      md_lines = [
          '# Google Scholar Publications\n',
          '| Year | Title | Authors | Venue | Citations | Link |',
          '| --- | --- | --- | --- | --- | --- |'
      ]

      scholar_titles = set()

      for row in rows:
        title_link = row.find('a', class_='gsc_a_at')
        if not title_link:
          continue
        title = title_link.text.strip()
        scholar_titles.add(self._normalize_title(title))

        citation_path = title_link['href']
        citation_url = f'https://scholar.google.com{citation_path}'

        divs = row.find_all('div', class_='gs_gray')
        authors = divs[0].text.strip() if len(divs) > 0 else 'Unknown'
        venue = divs[1].text.strip() if len(divs) > 1 else 'Unknown'

        year_tag = row.find(class_='gsc_a_y')
        year = year_tag.text.strip() if year_tag else 'Unknown'

        citations_tag = row.find('a', class_='gsc_a_ac')
        citations = citations_tag.text.strip(
        ) if citations_tag and citations_tag.text.strip() else '0'

        title_clean = title.replace('|', '\\|')
        authors_clean = authors.replace('|', '\\|')
        venue_clean = venue.replace('|', '\\|')

        md_lines.append(
            f'| {year} | **{title_clean}** | {authors_clean} | '
            f'*{venue_clean}* | {citations} | [Scholar Link]({citation_url}) |')

      # Query Crossref index for other papers matching author variations
      logger.info('Querying Crossref index for author variations...')
      unlinked_papers = []
      for author_query in ('Jacob Garrison', 'Jake Garrison'):
        enc_query = urllib.parse.quote(author_query)
        cr_url = f'https://api.crossref.org/works?query.author={enc_query}&rows=20'
        try:
          cr_req = urllib.request.Request(
              cr_url, headers={'User-Agent': config.USER_AGENT})
          with urllib.request.urlopen(cr_req, timeout=10) as cr_resp:
            data = json.loads(cr_resp.read().decode('utf-8'))
            items = data.get('message', {}).get('items', [])
            for item in items:
              title_list = item.get('title', [])
              if not title_list:
                continue
              p_title = title_list[0]
              norm_title = self._normalize_title(p_title)

              if norm_title in scholar_titles:
                continue

              authors_list = item.get('author', [])
              has_garrison = False
              author_names = []
              for auth in authors_list:
                family = auth.get('family', '')
                given = auth.get('given', '')
                if family:
                  author_names.append(f"{given} {family}".strip())
                  if 'garrison' in family.lower():
                    given_lower = given.lower()
                    # Check if given name matches Jake, Jacob, or J. initials (filtering out other Garrisons)
                    if ('jake' in given_lower or 'jacob' in given_lower or
                        given_lower.startswith('j.') or given_lower == 'j' or
                        given_lower.startswith('j ')):
                      has_garrison = True

              if not has_garrison:
                continue

              p_year = 'Unknown'
              published = item.get('published-print') or item.get(
                  'published-online') or item.get('created')
              if published:
                date_parts = published.get('date-parts', [])
                if date_parts and date_parts[0]:
                  p_year = str(date_parts[0][0])

              p_venue = item.get('container-title', ['Unknown'])[0]
              doi_url = item.get('URL', '')

              unlinked_papers.append({
                  'year': p_year,
                  'title': p_title,
                  'authors': ', '.join(author_names),
                  'venue': p_venue,
                  'url': doi_url
              })
        except Exception as e:  # pylint: disable=broad-except
          logger.warning('Failed to query Crossref for author %s: %s',
                         author_query, e)

      if unlinked_papers:
        seen_unlinked = set()
        dedup_unlinked = []
        for paper in unlinked_papers:
          norm_t = self._normalize_title(paper['title'])
          if norm_t not in seen_unlinked:
            seen_unlinked.add(norm_t)
            dedup_unlinked.append(paper)

        md_lines.append(
            '\n## Publications Found on Web Search (Not on Profile)\n')
        md_lines.append('| Year | Title | Authors | Venue | Link |')
        md_lines.append('| --- | --- | --- | --- | --- |')
        for paper in dedup_unlinked:
          title_clean = paper['title'].replace('|', '\\|')
          authors_clean = paper['authors'].replace('|', '\\|')
          venue_clean = paper['venue'].replace('|', '\\|')
          md_lines.append(
              f"| {paper['year']} | **{title_clean}** | {authors_clean} | "
              f"*{venue_clean}* | [DOI Link]({paper['url']}) |")

      with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines) + '\n')

      logger.info('Successfully wrote publications to %s', output_path)
    except Exception as e:  # pylint: disable=broad-except
      logger.error('Failed to fetch Scholar publications: %s', e)


class GithubFetcher:
  """Fetcher for GitHub repositories and latest commit logs."""

  def __init__(self, username: str):
    self.username = username

  def fetch_to_markdown(self,
                        output_path: str,
                        limit_repos: int = 15,
                        limit_commits: int = 3) -> None:
    """Queries GitHub API and formats repositories into Markdown with commit history."""
    url = f'https://api.github.com/users/{self.username}/repos?sort=updated&per_page=50'
    headers = {'User-Agent': 'Python-urllib'}
    req = urllib.request.Request(url, headers=headers)
    try:
      with urllib.request.urlopen(req, timeout=10) as response:
        repos = json.loads(response.read().decode('utf-8'))

      public_repos = [r for r in repos if not r.get('fork')]
      public_repos = public_repos[:limit_repos]

      md_lines = ['# GitHub Projects\n']
      for repo in public_repos:
        name = repo['name']
        description = repo['description'] or 'No description provided.'
        html_url = repo['html_url']
        language = repo['language'] or 'Mixed'

        md_lines.append(f'## [{name}]({html_url})')
        md_lines.append(f'*   **Language**: {language}')
        md_lines.append(f'*   **Description**: {description}')

        # Fetch latest commits history
        commits_url = f'https://api.github.com/repos/{self.username}/{name}/commits?per_page={limit_commits}'
        commit_req = urllib.request.Request(commits_url, headers=headers)
        try:
          with urllib.request.urlopen(commit_req, timeout=5) as c_response:
            commits = json.loads(c_response.read().decode('utf-8'))
            if commits:
              md_lines.append('*   **Recent Commits**:')
              for c in commits[:limit_commits]:
                sha = c['sha'][:7]
                msg = c['commit']['message'].split('\n')[0]
                date = c['commit']['author']['date'][:10]
                md_lines.append(f'    *   `{sha}` - "{msg}" ({date})')
        except Exception:  # pylint: disable=broad-except
          # Skip if commits call fails (rate limits)
          pass

        md_lines.append('')

      with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

      logger.info('Successfully wrote GitHub details to %s', output_path)
    except Exception as e:  # pylint: disable=broad-except
      logger.error('Failed to fetch GitHub repositories: %s', e)


class PatentsFetcher:
  """Fetcher for Google Patents listing search query indices.

  Note:
      Pending patent applications are kept confidential by the patent office
      (USPTO/PCT) and are not published or indexed until 18 months after their
      filing date. Consequently, any applications filed in the last 18 months
      (or in prep) will not show up in searches and must be manually added to
      the portfolio list.
  """

  def fetch_to_markdown(self, output_path: str) -> None:
    """Compiles patent lists and search links to Markdown."""
    query = (
        'inventor:"Jake Garrison" OR inventor:"Jacob Garrison" OR '
        'inventor:"Jacob H. Garrison" OR inventor:"Jacob Henry Garrison" OR '
        'inventor:"J. Garrison" OR inventor:"J. H. Garrison"')
    encoded_query = urllib.parse.quote(query)
    url = f'https://patents.google.com/?q={encoded_query}&sort=new'

    headers = {'User-Agent': config.USER_AGENT}

    logger.info('Searching patents via Google Patents: %s', url)
    req = urllib.request.Request(url, headers=headers)
    try:
      with urllib.request.urlopen(req, timeout=10) as response:
        html = response.read()

      soup = BeautifulSoup(html, 'html.parser')
      results = soup.find_all('article', class_='result')

      md_lines = [
          '# Patents & Intellectual Property\n',
          '*Auto-generated search results covering "Jacob Garrison", "Jake Garrison", and "Jacob H. Garrison" variations.*\n'
      ]

      if not results:
        logger.warning(
            'Static results not found. Generating search index links.')
        md_lines.append('### Confirmed Patents')
        md_lines.append(
            '- **US Patent 11,862,188**: Method for detecting and classifying coughs '
            'or other non-semantic sounds using audio feature set learned from speech. '
            '([Link](https://patents.google.com/patent/US11862188B2))')
        md_lines.append(
            '- **US Patent 11,627,890**: Contactless cough detection and attribution. '
            '([Link](https://patents.google.com/patent/US11627890B2))')
        md_lines.append(
            '- **US Patent 11,406,281**: Contactless cough detection and attribution. '
            '([Link](https://patents.google.com/patent/US11406281B2))')
        md_lines.append(
            '- **WO Patent 2022035526A1**: Contactless sleep detection. '
            '([Link](https://patents.google.com/patent/WO2022035526A1))')
        md_lines.append('\n### Search Index Queries')
        md_lines.append(f'- [Google Patents Query Search Link]({url})')
      else:
        for res in results:
          title_tag = res.find('span', itemprop='title')
          title = title_tag.text.strip() if title_tag else 'Unknown Title'
          num_tag = res.find('span', itemprop='num')
          num = num_tag.text.strip() if num_tag else 'Unknown Patent Number'

          desc_tag = res.find('div', itemprop='description')
          desc = desc_tag.text.strip() if desc_tag else ''

          patent_url = f'https://patents.google.com/patent/{num}'

          md_lines.append(f'### [{title}]({patent_url})')
          md_lines.append(f'- **Patent ID**: {num}')
          if desc:
            md_lines.append(f'- **Description**: {desc}\n')

      # Append pending patents & IDFs section
      md_lines.append('\n## Pending Patents & IDFs\n')
      md_lines.append(
          '*Note: Pending patent applications are confidential and are not published or searchable '
          'until 18 months after their filing date. There are 6 additional pending utility applications '
          'filed between 2023–2025.*\n')
      md_lines.append('| IDF / File ID | Project / Title | Filing Year | Estimated Pub Date | Status | Notes |')
      md_lines.append('| --- | --- | --- | --- | --- | --- |')
      md_lines.append('| **IDF-Pending-1** | Scaling Wearable Foundation Models | 2024 | Late 2025 / 2026 | Filed / Pending | Associated with wearable foundation model paper. |')
      md_lines.append('| **IDF-Pending-2** | What Are the Odds (Probabilistic Reasoning) | 2024 | Late 2025 / 2026 | Filed / Pending | Associated with LLM probabilistic reasoning paper. |')
      md_lines.append('| **IDF-Pending-3** | Health Acoustic Representations (HeAR) | 2024 | Late 2025 / 2026 | Filed / Pending | Audio representation model patents. |')
      md_lines.append('| **IDF-Pending-4** | *Non-Public Utility Application 4* | 2023-2025 | TBD | Filed / Pending | Active application. |')
      md_lines.append('| **IDF-Pending-5** | *Non-Public Utility Application 5* | 2023-2025 | TBD | Filed / Pending | Active application. |')
      md_lines.append('| **IDF-Pending-6** | *Non-Public Utility Application 6* | 2023-2025 | TBD | Filed / Pending | Active application. |')

      with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines) + '\n')

      logger.info('Successfully wrote patents to %s', output_path)
    except Exception as e:  # pylint: disable=broad-except
      logger.error('Failed to query Google Patents: %s', e)


class LinkedinFetcher:
  """Fetcher for LinkedIn experience: tries web crawl first, falls back to text file."""

  def fetch_from_web(self, profile_id: str) -> str:
    """Attempts to crawl public LinkedIn profile experience section."""
    url = f'https://www.linkedin.com/in/{profile_id}'
    headers = {'User-Agent': config.USER_AGENT}

    logger.info('Attempting to crawl public LinkedIn profile: %s', url)
    req = urllib.request.Request(url, headers=headers)
    try:
      with urllib.request.urlopen(req, timeout=10) as response:
        final_url = response.geturl()
        # If redirected to login wall
        if 'authwall' in final_url or 'login' in final_url:
          logger.warning('LinkedIn authwall redirected. Web crawl blocked.')
          return None
        html = response.read()

      soup = BeautifulSoup(html, 'html.parser')

      # Target experience card elements in public layout
      exp_section = soup.find('section',
                              class_=lambda c: c and 'experience' in c.lower())
      if not exp_section:
        # Fallback to search for ul lists
        exp_section = soup.find(
            'ul', class_=lambda c: c and 'experience' in c.lower())

      if not exp_section:
        return None

      items = exp_section.find_all('li')
      if not items:
        return None

      md_lines = ['# LinkedIn Experience\n']
      for item in items:
        title_tag = item.find(['h3', 'h4'],
                              class_=lambda c: c and 'title' in c.lower())
        title = title_tag.text.strip() if title_tag else ''

        company_tag = item.find(['h4', 'p'],
                                class_=lambda c: c and 'subtitle' in c.lower())
        company = company_tag.text.strip() if company_tag else ''

        duration_tag = item.find(class_=lambda c: c and ('duration' in c.lower(
        ) or 'range' in c.lower()))
        duration = duration_tag.text.strip() if duration_tag else ''

        desc_tag = item.find(class_=lambda c: c and 'description' in c.lower())
        desc = desc_tag.text.strip() if desc_tag else ''

        if title:
          md_lines.append(f'### {title}')
          if company:
            md_lines.append(f'- **Company**: {company}')
          if duration:
            md_lines.append(f'- **Dates**: {duration}')
          if desc:
            md_lines.append(f'\n{desc}\n')
          else:
            md_lines.append('')

      return '\n'.join(md_lines)
    except Exception as e:  # pylint: disable=broad-except
      logger.warning('LinkedIn web crawl failed: %s', e)
      return None

  def fetch_to_markdown(self, raw_txt_path: str, output_path: str) -> None:
    """Fetches experience and writes as Markdown, attempting web crawling first."""
    web_content = self.fetch_from_web('garrisonjake')
    if web_content and '### ' in web_content:
      with open(output_path, 'w', encoding='utf-8') as f:
        f.write(web_content)
      logger.info('Successfully crawled and wrote LinkedIn experience to %s',
                  output_path)
      return

    # Fallback to local text file parsing
    logger.info('Falling back to local copy-paste parsing...')
    if not os.path.exists(raw_txt_path):
      logger.warning(
          '\n[SETUP REQUIRED] linkedin_raw.txt does not exist.\n'
          'For LinkedIn updates, copy-paste your LinkedIn Experience section\n'
          'into %s and run make fetch.', raw_txt_path)
      return

    try:
      with open(raw_txt_path, 'r', encoding='utf-8') as f:
        text = f.read()

      lines = [line.strip() for line in text.split('\n')]
      md_lines = ['# LinkedIn Experience\n']

      i = 0
      n = len(lines)
      date_pattern = re.compile(
          r'([A-Za-z]{3}\s\d{4}|Present|[A-Za-z]{3}\s\d{2}).*?([A-Za-z]{3}\s\d{4}|Present|[A-Za-z]{3}\s\d{2})'
      )

      while i < n:
        line = lines[i]
        if not line or line == 'Experience' or 'logo' in line.lower():
          i += 1
          continue

        is_job = False
        date_idx = -1
        for offset in (1, 2, 3):
          if i + offset < n and date_pattern.search(lines[i + offset]):
            is_job = True
            date_idx = i + offset
            break

        if is_job:
          title = lines[i]
          company_line = lines[i + 1] if date_idx > i + 1 else 'Unknown Company'
          dates = lines[date_idx]
          location = lines[date_idx + 1] if date_idx + 1 < n else ''

          desc_lines = []
          idx = date_idx + 2
          while idx < n:
            next_line = lines[idx]
            if not next_line:
              idx += 1
              continue
            next_is_job = False
            for offset in (1, 2, 3):
              if idx + offset < n and date_pattern.search(lines[idx + offset]):
                next_is_job = True
                break
            if next_is_job or next_line == 'Experience' or 'logo' in next_line.lower(
            ):
              break
            if next_line.startswith('Thumbnail for') or next_line.startswith(
                'Contactless'):
              idx += 1
              continue

            desc_lines.append(next_line)
            idx += 1

          md_lines.append(f'### {title}')
          md_lines.append(f'- **Company**: {company_line}')
          md_lines.append(f'- **Dates**: {dates}')
          if location:
            md_lines.append(f'- **Location**: {location}')
          if desc_lines:
            description = ' '.join(desc_lines)
            md_lines.append(f'\n{description}\n')
          else:
            md_lines.append('')
          i = idx
        else:
          i += 1

      with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_lines))

      logger.info('Successfully parsed LinkedIn data to %s', output_path)
    except Exception as e:  # pylint: disable=broad-except
      logger.error('Failed to parse LinkedIn text file: %s', e)


class BlogFetcher:
  """Fetcher for Google Research Blog posts related to Jake's work."""

  def fetch_to_markdown(self, output_path: str) -> None:
    """Queries or compiles related Google Research Blog posts."""
    md_lines = [
        '# Google Research Blogs\n',
        '| Date | Blog Post Title | Related Project / Paper | Link |',
        '| --- | --- | --- | --- |'
    ]

    blogs = [{
        'date':
            '2026',
        'title':
            'Insulin resistance prediction from wearables and routine blood biomarkers',
        'project':
            'Nature biomarkers discovery paper',
        'url':
            'https://research.google/blog/insulin-resistance-prediction-from-wearables-and-routine-blood-biomarkers/'
    }, {
        'date':
            '2026',
        'title':
            'Empirical Research Assistance (ERA): From Nature publication to catalyzing computational discovery',
        'project':
            'Nature software paper (Empirical Research Assistant)',
        'url':
            'https://research.google/blog/empirical-research-assistance-era-from-nature-publication-to-catalyzing-computational-discovery/'
    }, {
        'date':
            '2026',
        'title':
            'Four ways Google Research scientists have been using Empirical Research Assistance',
        'project':
            'Empirical Research Assistant applications',
        'url':
            'https://research.google/blog/four-ways-google-research-scientists-have-been-using-empirical-research-assistance/'
    }, {
        'date':
            '2025',
        'title':
            'Accelerating scientific discovery with AI-powered empirical software',
        'project':
            'Nature software paper (GIFT-Eval tree search)',
        'url':
            'https://research.google/blog/accelerating-scientific-discovery-with-ai-powered-empirical-software/'
    }, {
        'date':
            '2025',
        'title':
            'SensorLM: Learning the language of wearable sensors',
        'project':
            'SensorLM foundation model',
        'url':
            'https://research.google/blog/sensorlm-learning-the-language-of-wearable-sensors/'
    }, {
        'date':
            '2025',
        'title':
            'LSM-2: Learning from incomplete wearable sensor data',
        'project':
            'LSM wearable foundation models',
        'url':
            'https://research.google/blog/lsm-2-learning-from-incomplete-wearable-sensor-data/'
    }, {
        'date':
            '2024',
        'title':
            'A new AI model to help detect disease from cough sounds',
        'project':
            'HeAR (Health Acoustic Representations) - Product Announcement',
        'url':
            'https://blog.google/technology/health/ai-model-cough-disease-detection/'
    }, {
        'date':
            '2024',
        'title':
            'Helping researchers build audio models for health',
        'project':
            'HeAR (Health Acoustic Representations) - Research Launch',
        'url':
            'https://research.google/blog/helping-researchers-build-audio-models-for-health/'
    }, {
        'date':
            '2024',
        'title':
            'Stephen Curry partners with Fitbit for premium training integrations',
        'project':
            'Stephen Curry Fitbit Premium program',
        'url':
            'https://blog.google/products/fitbit/'
    }, {
        'date':
            '2024',
        'title':
            'Scaling wearable foundation models',
        'project':
            'LSM-1 initiative',
        'url':
            'https://research.google/blog/scaling-wearable-foundation-models/'
    }, {
        'date':
            '2023',
        'title':
            'Aigen raises $12m to scale its fleet of solar-powered robots',
        'project':
            'Aigen Solar Ag-Robots Funding',
        'url':
            'https://agfundernews.com/aigen-raises-12m-to-scale-its-fleet-of-solar-powered-autonomous-robots-to-more-than-20000-acres'
    }, {
        'date':
            '2022',
        'title':
            'Sleeping job: How we built the new Nest Hub\'s Sleep Sensing',
        'project':
            'Nest Hub Sleep Sensing',
        'url':
            'https://blog.google/products/google-nest/sleeping-job-how-we-built-new-nest-hub/'
    }, {
        'date':
            '2022',
        'title':
            'Contactless sleep sensing in Nest Hub',
        'project':
            'Nest Hub sleep tracking algos',
        'url':
            'https://research.google/blog/contactless-sleep-sensing-in-nest-hub/'
    }, {
        'date':
            '2022',
        'title':
            'Enhanced sleep sensing in Nest Hub',
        'project':
            'Nest Hub respiration algorithms',
        'url':
            'https://research.google/blog/enhanced-sleep-sensing-in-nest-hub/'
    }, {
        'date':
            '2021',
        'title':
            'FRILL: On-device speech representations using TensorFlow Lite',
        'project':
            'FRILL / TRILL audio embeddings',
        'url':
            'https://research.google/blog/frill-on-device-speech-representations-using-tensorflow-lite/'
    }, {
        'date':
            '2020',
        'title':
            'Important household sounds become more accessible',
        'project':
            'Nest & Android Baby Cry / Dog Bark Alerts',
        'url':
            'https://blog.google/products-and-platforms/platforms/android/new-sound-notifications-on-android/'
    }, {
        'date':
            '2019',
        'title':
            'Keep an eye (and ear) on your home with the new Nest Aware',
        'project':
            'Nest Aware Event-Based Sound Detection',
        'url':
            'https://blog.google/products-and-platforms/devices/google-nest/nest-aware/'
    }, {
        'date':
            '2017',
        'title':
            'Exclusive: Google buys Seattle health monitoring startup Senosis',
        'project':
            'Senosis Health Acquisition',
        'url':
            'https://www.geekwire.com/2017/exclusive-google-buys-seattle-health-monitoring-startup-senosis-bolstering-digital-health-push/'
    }, {
        'date': '2017',
        'title': 'Convert Wikipedia to a Presentation Automatically',
        'project': 'Haiku Deck Zuru Slide Automation',
        'url': 'https://blog.haikudeck.com/wikipedia-presentation/'
    }, {
        'date':
            '2014',
        'title':
            'This is Tesla\'s D: an all-wheel-drive Model S with eyes on the road',
        'project':
            'Tesla Dual Motor & Autopilot Hardware Launch',
        'url':
            'https://www.theverge.com/2014/10/9/6955357/this-is-tesla-s-d-an-all-wheel-drive-car-with-eyes-on-the-road'
    }]

    for blog in blogs:
      md_lines.append(
          f"| {blog['date']} | **{blog['title']}** | {blog['project']} | "
          f"[Read Blog]({blog['url']}) |")

    query = '"Jake+Garrison"+OR+"Jacob+Garrison"+site:research.google/blog'
    search_url = f"https://www.google.com/search?q={query}"

    md_lines.append('\n### Search Pointers for Live Updates')
    md_lines.append(
        f'- [Google Search: Google Research Blog Posts]({search_url})')

    with open(output_path, 'w', encoding='utf-8') as f:
      f.write('\n'.join(md_lines) + '\n')

    logger.info('Successfully wrote blogs to %s', output_path)


def main() -> None:
  os.makedirs(config.OUTPUTS_DIR, exist_ok=True)

  # Scholar Sync
  scholar = ScholarFetcher(config.SCHOLAR_ID)
  scholar.fetch_to_markdown(os.path.join(config.OUTPUTS_DIR, 'publications.md'))

  # GitHub Sync
  github = GithubFetcher(config.GITHUB_USERNAME)
  github.fetch_to_markdown(
      os.path.join(config.OUTPUTS_DIR, 'github_projects.md'))

  # Patents Sync
  patents = PatentsFetcher()
  patents.fetch_to_markdown(os.path.join(config.OUTPUTS_DIR, 'patents.md'))

  # LinkedIn Sync
  linkedin = LinkedinFetcher()
  linkedin.fetch_to_markdown(
      os.path.join(config.OUTPUTS_DIR, 'linkedin_raw.txt'),
      os.path.join(config.OUTPUTS_DIR, 'linkedin_experience.md'))

  # Blog Posts Sync
  blogs = BlogFetcher()
  blogs.fetch_to_markdown(os.path.join(config.OUTPUTS_DIR, 'blogs.md'))


if __name__ == '__main__':
  main()
