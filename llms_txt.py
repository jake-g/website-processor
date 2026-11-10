"""Generates /llms.txt from index.html following the llmstxt.org v2 spec.

Extracts structured profile metadata, biography, education, work experience,
skills, keywords, awards, publications, patents, blogs, lectures, and
engineering projects directly from index.html—enriched with venue, author,
citation, patent, GitHub language, and topic metadata from processing/outputs/—
so /llms.txt stays automatically synchronized as the site evolves.

Usage:
  PYTHONPATH=.. python3 -m processing.llms_txt
"""

from html import unescape
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from processing import config

logger = logging.getLogger(__name__)

_COMMENT_RE = re.compile(r'<!--.*?-->', flags=re.DOTALL)
_TAG_RE = re.compile(r'<[^>]+>')
_WS_RE = re.compile(r'\s+')
_ANCHOR_RE = re.compile(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                        flags=re.DOTALL)
_ALNUM_RE = re.compile(r'[^a-z0-9]+')


def _strip_comments(html: str) -> str:
  """Removes HTML comments from markup."""
  return _COMMENT_RE.sub('', html)


def _clean_text(fragment: str) -> str:
  """Strips HTML tags, unescapes entities, and normalizes whitespace."""
  text = _TAG_RE.sub(' ', fragment)
  return _WS_RE.sub(' ', unescape(text)).strip()


def _norm_key(title: str) -> str:
  """Normalizes a title string for fuzzy matching across synced sources."""
  lowered = title.lower()
  lowered = re.sub(r'\([^)]*\)', ' ', lowered)
  return _ALNUM_RE.sub(' ', lowered).strip()


def _ensure_period(text: str) -> str:
  """Ensures a non-empty prose string ends with terminal punctuation."""
  stripped = text.strip()
  if not stripped:
    return ''
  if stripped[-1] in '.!?':
    return stripped
  return f'{stripped}.'


def _abs_url(href: str, base_url: str = config.SITE_URL) -> str:
  """Converts relative site paths to canonical absolute URLs.

  Args:
    href (str): Raw href value from HTML.
    base_url (str): Canonical origin without trailing slash.

  Returns:
    str: Absolute URL.
  """
  href = href.strip()
  if href.startswith(('http://', 'https://', 'mailto:')):
    return href
  root = base_url.rstrip('/')
  if href.startswith('#'):
    return f'{root}/{href}'
  return f"{root}/{href.lstrip('/')}"


def _inline_markdown(fragment: str, base_url: str = config.SITE_URL) -> str:
  """Converts inline <a> tags to Markdown links and strips remaining HTML."""

  def _repl(match: re.Match[str]) -> str:
    raw_href = match.group(1).strip()
    url = _abs_url(raw_href, base_url)
    label = _clean_text(match.group(2))
    if not label:
      return ''
    if raw_href.startswith('#'):
      return label
    return f'[{label}]({url})'

  converted = _ANCHOR_RE.sub(_repl, fragment)
  text = _clean_text(converted)
  return re.sub(r'\s+([,.;:])', r'\1', text)


def _slice_between(
    html: str,
    start_marker: str,
    end_markers: Tuple[str, ...],
    start_pos: int = 0,
) -> str:
  """Returns the substring starting at start_marker up to first end_marker."""
  idx = html.find(start_marker, start_pos)
  if idx == -1:
    return ''
  end_positions = [
      html.find(m, idx + len(start_marker))
      for m in end_markers
      if html.find(m, idx + len(start_marker)) != -1
  ]
  end_idx = min(end_positions) if end_positions else len(html)
  return html[idx:end_idx]


def load_scholar_enrichment(
    outputs_dir: Optional[str] = config.OUTPUTS_DIR,
) -> Dict[str, Dict[str, Any]]:
  """Loads venue, author, and citation metadata from outputs/publications.md.

  Args:
    outputs_dir (Optional[str]): Path to processing/outputs directory.

  Returns:
    Dict[str, Dict[str, Any]]: Normalized title -> {authors, venue, citations}.
  """
  if not outputs_dir:
    return {}
  pub_path = os.path.join(outputs_dir, 'publications.md')
  if not os.path.isfile(pub_path):
    return {}

  enrichment: Dict[str, Dict[str, Any]] = {}
  try:
    with open(pub_path, 'r', encoding='utf-8') as f:
      for line in f:
        if not line.startswith('|') or '---' in line or '| Title |' in line:
          continue
        cols = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cols) < 5:
          continue
        raw_title = cols[1].replace('**', '').strip()
        authors = cols[2].strip()
        venue = cols[3].replace('*', '').replace('\xa0', ' ').strip()
        citations = int(cols[4]) if cols[4].isdigit() else 0
        key = _norm_key(raw_title)
        if key and key not in enrichment:
          enrichment[key] = {
              'authors': authors,
              'venue': venue,
              'citations': citations,
          }
  except OSError as exc:
    logger.warning('Could not read %s: %s', pub_path, exc)
  return enrichment


def load_blog_enrichment(
    outputs_dir: Optional[str] = config.OUTPUTS_DIR,) -> Dict[str, str]:
  """Loads blog topic descriptions keyed by URL from outputs/blogs.md."""
  if not outputs_dir:
    return {}
  blogs_path = os.path.join(outputs_dir, 'blogs.md')
  if not os.path.isfile(blogs_path):
    return {}

  by_url: Dict[str, str] = {}
  try:
    with open(blogs_path, 'r', encoding='utf-8') as f:
      for line in f:
        if not line.startswith('|') or '---' in line or 'Blog Post' in line:
          continue
        cols = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cols) < 4:
          continue
        topic = cols[2].strip()
        url_m = re.search(r'\((https?://[^)]+)\)', cols[3])
        if url_m and topic:
          by_url[url_m.group(1).strip()] = topic
  except OSError as exc:
    logger.warning('Could not read %s: %s', blogs_path, exc)
  return by_url


def load_patent_enrichment(
    outputs_dir: Optional[str] = config.OUTPUTS_DIR,
) -> Dict[str, Dict[str, str]]:
  """Loads patent numbers and abstracts keyed by URL from outputs/patents.md."""
  if not outputs_dir:
    return {}
  pat_path = os.path.join(outputs_dir, 'patents.md')
  if not os.path.isfile(pat_path):
    return {}

  by_url: Dict[str, Dict[str, str]] = {}
  current_url = ''
  try:
    with open(pat_path, 'r', encoding='utf-8') as f:
      for line in f:
        stripped = line.strip()
        if stripped.startswith('- **'):
          num_m = re.match(r'-\s+\*\*([^*]+)\*\*:', stripped)
          url_m = re.search(r'\((https?://patents\.google\.com/[^)]+)\)', line)
          if num_m and url_m:
            current_url = url_m.group(1).strip()
            by_url[current_url] = {'number': num_m.group(1).strip()}
        elif stripped.startswith('- *Abstract*:') and current_url:
          abstract = stripped.replace('- *Abstract*:', '').strip()
          first_sent = abstract.split('. ')[0].strip().rstrip('.') + '.'
          by_url[current_url]['abstract'] = first_sent
  except OSError as exc:
    logger.warning('Could not read %s: %s', pat_path, exc)
  return by_url


def load_github_enrichment(
    outputs_dir: Optional[str] = config.OUTPUTS_DIR,
) -> Dict[str, Dict[str, str]]:
  """Loads repo language and description from outputs/github_projects.md."""
  if not outputs_dir:
    return {}
  gh_path = os.path.join(outputs_dir, 'github_projects.md')
  if not os.path.isfile(gh_path):
    return {}

  by_url: Dict[str, Dict[str, str]] = {}
  current_url = ''
  try:
    with open(gh_path, 'r', encoding='utf-8') as f:
      for line in f:
        stripped = line.strip()
        if stripped.startswith('## ['):
          url_m = re.search(r'\((https?://github\.com/[^)]+)\)', stripped)
          if url_m:
            current_url = url_m.group(1).rstrip('/')
            by_url[current_url] = {}
        elif current_url and '**Language**:' in stripped:
          lang = stripped.split('**Language**:', 1)[1].strip()
          if lang and lang.lower() != 'unknown':
            by_url[current_url]['language'] = lang
        elif current_url and '**Description**:' in stripped:
          desc = stripped.split('**Description**:', 1)[1].strip()
          if desc and desc.lower() not in ('no description provided.',
                                           'my fork'):
            by_url[current_url]['description'] = desc
  except OSError as exc:
    logger.warning('Could not read %s: %s', gh_path, exc)
  return by_url


def _match_scholar(
    card_title: str,
    scholar_map: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
  """Matches a site publication title against Scholar metadata."""
  if not scholar_map:
    return None
  key = _norm_key(card_title)
  if key in scholar_map:
    return scholar_map[key]
  prefix = key.split()[0] if key else ''
  for s_key, meta in scholar_map.items():
    if key in s_key or s_key in key:
      return meta
    if len(prefix) >= 6 and s_key.startswith(prefix):
      return meta
  return None


def parse_metadata(html: str) -> Dict[str, Any]:
  """Extracts person metadata from meta tags and JSON-LD ProfilePage schema.

  Args:
    html (str): Comment-stripped HTML content.

  Returns:
    Dict[str, Any]: Parsed name, description, job_title, works_for, alumni_of,
    location, knows_about, and same_as links.
  """
  desc_match = re.search(
      r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']',
      html,
      flags=re.IGNORECASE | re.DOTALL,
  )
  description = _clean_text(desc_match.group(1)) if desc_match else ''

  ld_match = re.search(
      r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
      html,
      flags=re.IGNORECASE | re.DOTALL,
  )
  entity: Dict[str, Any] = {}
  if ld_match:
    try:
      data = json.loads(ld_match.group(1))
      entity = data.get('mainEntity', data)
    except json.JSONDecodeError as exc:
      logger.warning('Failed to parse JSON-LD metadata: %s', exc)

  addr = entity.get('address', {})
  locality = addr.get('addressLocality', '')
  region = addr.get('addressRegion', '')
  location = ', '.join(part for part in (locality, region) if part)

  return {
      'name': entity.get('name', 'Jake Garrison'),
      'description': description,
      'job_title': entity.get('jobTitle', ''),
      'works_for': entity.get('worksFor', {}).get('name', ''),
      'alumni_of': entity.get('alumniOf', {}).get('name', ''),
      'location': location,
      'knows_about': entity.get('knowsAbout', []),
      'same_as': entity.get('sameAs', []),
  }


def parse_about(html: str) -> str:
  """Extracts the primary biography text from the #about section."""
  sec = _slice_between(html, 'id="about"', ('id="resume"',))
  paragraphs = [
      _clean_text(m.group(1))
      for m in re.finditer(r'<p[^>]*>(.*?)</p>', sec, flags=re.DOTALL)
  ]
  return ' '.join(p for p in paragraphs if p)


def _parse_resume_list(list_html: str,
                       base_url: str = config.SITE_URL) -> List[Dict[str, Any]]:
  """Parses <details class="resume-item"> entries inside a resume <ul>."""
  items: List[Dict[str, Any]] = []
  pattern = re.compile(
      r'<details[^>]*class=["\'][^"\']*resume-item[^"\']*["\'][^>]*>'
      r'(.*?)</details>',
      flags=re.DOTALL,
  )
  for match in pattern.finditer(list_html):
    block = match.group(1)
    h5_m = re.search(r'<h5[^>]*>(.*?)</h5>', block, flags=re.DOTALL)
    if not h5_m:
      continue
    title = _clean_text(h5_m.group(1))
    span_m = re.search(
        r'<span\s+class=["\']label[^"\']*["\'][^>]*>(.*?)</span>',
        block,
        flags=re.DOTALL,
    )
    period = _clean_text(span_m.group(1)) if span_m else ''

    body_m = re.search(
        r'<div\s+class=["\']resume-body["\'][^>]*>(.*?)</div>',
        block,
        flags=re.DOTALL,
    )
    body = body_m.group(1) if body_m else ''

    prose_parts: List[str] = []
    extra_links: List[Tuple[str, str]] = []
    for p_m in re.finditer(r'<p[^>]*>(.*?)</p>', body, flags=re.DOTALL):
      p_raw = p_m.group(1)
      anchors = list(_ANCHOR_RE.finditer(p_raw))
      non_anchor = _clean_text(_ANCHOR_RE.sub('', p_raw))
      if anchors and not non_anchor:
        for a_m in anchors:
          href = a_m.group(1).strip()
          lbl = _clean_text(a_m.group(2))
          if href and not href.startswith('#') and lbl:
            extra_links.append((lbl, _abs_url(href, base_url)))
      else:
        cleaned = _inline_markdown(p_raw, base_url)
        if cleaned:
          prose_parts.append(cleaned)

    bullets = [
        _inline_markdown(li_m.group(1), base_url).rstrip('.')
        for li_m in re.finditer(r'<li[^>]*>(.*?)</li>', body, flags=re.DOTALL)
    ]
    items.append({
        'title': title,
        'period': period,
        'summary': ' — '.join(prose_parts),
        'bullets': [b for b in bullets if b],
        'links': extra_links,
    })
  return items


def _format_resume_entry(item: Dict[str, Any]) -> str:
  """Formats a parsed education or experience item as a readable bullet."""
  period = f" ({item['period']})" if item['period'] else ''
  segments: List[str] = []
  if item['summary']:
    segments.append(_ensure_period(item['summary']))
  if item['bullets']:
    segments.append(_ensure_period('; '.join(item['bullets'])))
  if item['links']:
    link_md = ', '.join(f'[{lbl}]({url})' for lbl, url in item['links'])
    segments.append(f'Links: {link_md}.')
  body = ' '.join(segments)
  return f"- **{item['title']}{period}:** {body}"


def parse_resume(html: str, base_url: str = config.SITE_URL) -> Dict[str, Any]:
  """Extracts education, experience, skills, keywords, awards, and downloads."""
  resume_sec = _slice_between(html, 'id="resume"', ('id="projects"',))
  edu_sec = _slice_between(resume_sec, 'id="education-list"',
                           ('id="experience-list"',))
  exp_sec = _slice_between(
      resume_sec,
      'id="experience-list"',
      ('class="robots-only"', 'id="accomplishments"', 'class="button"'),
  )
  robots_sec = _slice_between(resume_sec, 'class="robots-only"',
                              ('id="accomplishments"',))
  acc_sec = _slice_between(resume_sec, 'id="accomplishments"',
                           ('class="button"',))

  skills: List[str] = []
  interests: List[str] = []
  keywords = ''
  if robots_sec:
    skills_part = _slice_between(robots_sec, '<h4>Skills</h4>', ('<h4>',))
    skills = [
        _clean_text(m.group(1)) for m in re.finditer(
            r'<li[^>]*>(.*?)</li>', skills_part, flags=re.DOTALL)
    ]
    interests_part = _slice_between(robots_sec, '<h4>Interests</h4>', ('<h4>',))
    interests = [
        _clean_text(m.group(1)) for m in re.finditer(
            r'<li[^>]*>(.*?)</li>', interests_part, flags=re.DOTALL)
    ]
    kw_part = _slice_between(robots_sec, '<h4>Keywords</h4>', ('</div>',))
    kw_m = re.search(r'<p[^>]*>(.*?)</p>', kw_part, flags=re.DOTALL)
    if kw_m:
      keywords = _clean_text(kw_m.group(1))

  awards: List[str] = []
  if acc_sec:
    awards_part = _slice_between(acc_sec, '<h4>Awards</h4>', ('<h4>',))
    awards = [
        _clean_text(m.group(1)) for m in re.finditer(
            r'<li[^>]*>(.*?)</li>', awards_part, flags=re.DOTALL)
    ]

  downloads: List[Tuple[str, str]] = []
  for btn_m in re.finditer(
      r'<div\s+class=["\']button["\'][^>]*>(.*?)</div>\s*</div>\s*</div>',
      resume_sec,
      flags=re.DOTALL,
  ):
    for a_m in _ANCHOR_RE.finditer(btn_m.group(1)):
      downloads.append(
          (_clean_text(a_m.group(2)), _abs_url(a_m.group(1), base_url)))

  return {
      'education': _parse_resume_list(edu_sec, base_url),
      'experience': _parse_resume_list(exp_sec, base_url),
      'skills': [s for s in skills if s],
      'interests': [i for i in interests if i],
      'keywords': keywords,
      'awards': [a for a in awards if a],
      'downloads': downloads,
  }


def parse_card_groups(
    section_html: str,
    default_heading: str,
    base_url: str = config.SITE_URL,
) -> List[Tuple[str, Optional[str], List[Dict[str, Any]]]]:
  """Parses <h4>-delimited groups of .g1 cards from a page section.

  Args:
    section_html (str): HTML slice for a container section.
    default_heading (str): Fallback category heading when none precedes cards.
    base_url (str): Canonical site URL.

  Returns:
    List[Tuple[str, Optional[str], List[Dict[str, Any]]]]: Tuples of
    (category_title, optional_italic_note, list_of_cards).
  """
  tokens = re.split(r'(<h4[^>]*>.*?</h4>)', section_html, flags=re.DOTALL)
  groups: List[Tuple[str, Optional[str], List[Dict[str, Any]]]] = []
  current_cat = default_heading

  for tok in tokens:
    if tok.startswith('<h4'):
      current_cat = _clean_text(tok)
      continue

    raw_parts = tok.split('<div class="g1">')
    preamble = raw_parts[0]
    card_chunks = raw_parts[1:]
    if not card_chunks:
      continue

    note_match = re.search(
        r'<p[^>]*style=["\'][^"\']*italic[^"\']*["\'][^>]*>(.*?)</p>',
        preamble,
        flags=re.DOTALL,
    )
    note = _clean_text(note_match.group(1)) if note_match else None

    cards: List[Dict[str, Any]] = []
    for chunk in card_chunks:
      h6_m = re.search(r'<h6[^>]*>(.*?)</h6>', chunk, flags=re.DOTALL)
      if not h6_m:
        continue
      h6_raw = h6_m.group(1)
      year_m = re.search(
          r'<span[^>]*class=["\']pub-year["\'][^>]*>(.*?)</span>',
          h6_raw,
          flags=re.DOTALL,
      )
      year = _clean_text(year_m.group(1)) if year_m else ''
      title_html = re.sub(
          r'<span[^>]*class=["\'](?:pub-year|vibe-tag)["\'][^>]*>.*?</span>',
          '',
          h6_raw,
          flags=re.DOTALL,
      )
      title = _clean_text(title_html)

      links_p = re.search(
          r'<p[^>]*class=["\']card-links["\'][^>]*>(.*?)</p>',
          chunk,
          flags=re.DOTALL,
      )
      links: List[Tuple[str, str]] = []
      fallback_note = ''
      if links_p:
        for a_m in _ANCHOR_RE.finditer(links_p.group(1)):
          lbl = _clean_text(a_m.group(2))
          url = _abs_url(a_m.group(1), base_url)
          if lbl:
            links.append((lbl, url))
        if not links:
          fallback_note = _clean_text(links_p.group(1))

      cards.append({
          'title': title,
          'year': year,
          'links': links,
          'fallback_note': fallback_note,
      })

    if cards:
      groups.append((current_cat, note, cards))
  return groups


def _enrich_project_detail(card: Dict[str, Any],
                           gh_map: Dict[str, Dict[str, str]]) -> str:
  """Builds concise language/description detail for GitHub-backed projects."""
  if not card['links']:
    return ''
  primary_label, primary_url = card['links'][0]
  gh_meta = gh_map.get(primary_url.rstrip('/'), {})
  parts = [primary_label]
  if gh_meta.get('language'):
    parts[0] = f"{primary_label} ({gh_meta['language']})"
  if gh_meta.get('description'):
    parts.append(gh_meta['description'])
  return ' — '.join(parts)


def _format_card_bullet(
    card: Dict[str, Any],
    category_prefix: str = '',
    detail_text: str = '',
    extra_suffix: str = '',
    base_url: str = config.SITE_URL,
) -> str:
  """Formats a card as an llmstxt.org v2 `- [Title](URL): details` item."""
  links: List[Tuple[str, str]] = card['links']
  if links:
    primary_label, primary_url = links[0]
    secondary = [f'[{lbl}]({url})' for lbl, url in links[1:]]
  else:
    primary_label = card['fallback_note'] or 'Contact'
    primary_url = f"{base_url.rstrip('/')}/#contact"
    secondary = []

  notes_parts: List[str] = []
  if category_prefix:
    notes_parts.append(f'[{category_prefix}]')
  if card['year']:
    notes_parts.append(card['year'])
  if detail_text:
    notes_parts.append(detail_text)
  elif primary_label:
    notes_parts.append(primary_label)
  if secondary:
    notes_parts.append('Links: ' + ', '.join(secondary))
  if extra_suffix:
    notes_parts.append(extra_suffix)

  notes_str = ' — '.join(notes_parts)
  if notes_str:
    return f"- [{card['title']}]({primary_url}): {notes_str}"
  return f"- [{card['title']}]({primary_url})"


def generate_llms_txt(
    html: str,
    base_url: str = config.SITE_URL,
    outputs_dir: Optional[str] = config.OUTPUTS_DIR,
) -> str:
  """Generates a complete llmstxt.org v2 Markdown document from index.html.

  The v2 specification orders sections strictly as:
    1. H1 project/person title
    2. Blockquote summary
    3. Non-heading Markdown paragraphs/lists with detailed context
    4. H2 (`##`) sections containing `- [Name](URL): notes` link lists
    5. Optional `## Optional` section at the end for secondary resources

  Args:
    html (str): Raw HTML contents of index.html.
    base_url (str): Canonical site URL without trailing slash.
    outputs_dir (Optional[str]): Optional processing/outputs directory for
      Scholar, patent, GitHub, and blog enrichment.

  Returns:
    str: Formatted llms.txt Markdown string ending with a single newline.
  """
  clean = _strip_comments(html)
  meta = parse_metadata(clean)
  about = parse_about(clean)
  resume = parse_resume(clean, base_url)
  scholar_map = load_scholar_enrichment(outputs_dir)
  blog_map = load_blog_enrichment(outputs_dir)
  patent_map = load_patent_enrichment(outputs_dir)
  gh_map = load_github_enrichment(outputs_dir)

  lines: List[str] = [f"# {meta['name']}", '']

  summary = meta['description'] or (
      f"{meta['job_title']} at {meta['works_for']}.")
  lines.extend([f'> {summary}', ''])

  if about:
    lines.extend([about, ''])

  identity_parts = [
      f"**Author Names:** {meta['name']} (also published as Jacob Garrison "
      'and Jacob H. Garrison).'
  ]
  if meta['job_title'] and meta['works_for']:
    identity_parts.append(
        f"**Current Role:** {meta['job_title']} at {meta['works_for']}.")
  if meta['alumni_of']:
    identity_parts.append(
        f"**Alma Mater:** {meta['alumni_of']} (M.S. & B.S. ECE/EE).")
  if meta['location']:
    identity_parts.append(f"**Location:** {meta['location']}.")
  lines.extend([' '.join(identity_parts), ''])

  if meta['knows_about']:
    domains = ', '.join(meta['knows_about'])
    lines.extend([f'**Research & Technical Domains:** {domains}.', ''])

  if resume['education']:
    lines.append('**Education & Academic Teaching:**')
    for item in resume['education']:
      lines.append(_format_resume_entry(item))
    lines.append('')

  if resume['experience']:
    lines.append('**Work Experience:**')
    for item in resume['experience']:
      lines.append(_format_resume_entry(item))
    lines.append('')

  if resume['skills']:
    lines.append('**Skills & Engineering Stack:**')
    for skill in resume['skills']:
      lines.append(f'- {skill}')
    lines.append('')

  if resume['awards']:
    lines.append('**Selected Awards:** ' + '; '.join(resume['awards']) + '.')
    lines.append('')

  if resume['interests']:
    lines.append('**Interests:** ' + '; '.join(resume['interests']) + '.')
    lines.append('')

  if resume['keywords']:
    lines.extend([f"**Topic Index:** {resume['keywords']}", ''])

  # Collect canonical profile links without duplicates.
  root_url = f"{base_url.rstrip('/')}/"
  profile_entries: List[Tuple[str, str, str]] = [
      ('Personal Website', root_url, 'Canonical homepage and portfolio'),
  ]
  seen_urls = {root_url}

  for exp in resume['experience']:
    for _, url in exp['links']:
      if url in seen_urls:
        continue
      if 'research.google/people/' in url:
        profile_entries.append(
            ('Google Research Profile', url, 'Official Google Research page'))
        seen_urls.add(url)
      elif 'patents.google.com' in url:
        profile_entries.append(('Google Patents Search', url,
                                'Granted and pending Google patents'))
        seen_urls.add(url)

  for url in meta['same_as']:
    if url in seen_urls:
      continue
    seen_urls.add(url)
    if 'scholar.google' in url:
      profile_entries.append(
          ('Google Scholar', url, 'Citation metrics and full bibliography'))
    elif 'github.com' in url:
      profile_entries.append(
          ('GitHub (@jake-g)', url, 'Open-source repositories and AI code'))
    elif 'linkedin.com' in url:
      profile_entries.append(
          ('LinkedIn', url, 'Professional profile and career history'))
    else:
      profile_entries.append(('Profile', url, ''))

  lines.extend(['## Profiles', ''])
  for title, url, note in profile_entries:
    suffix = f': {note}' if note else ''
    lines.append(f'- [{title}]({url}){suffix}')
  lines.append('')

  pub_sec = _slice_between(clean, 'id="publications"',
                           ('id="school"', 'id="academic-writeups"'))
  pub_groups = parse_card_groups(pub_sec, 'Publications', base_url)

  blogs_sec = _slice_between(clean, 'id="blogs"',
                             ('id="publications"', 'id="school"'))
  blog_groups = parse_card_groups(blogs_sec, 'Blogs', base_url)

  proj_sec = _slice_between(clean, 'id="projects"', ('id="blogs"',))
  proj_groups = parse_card_groups(proj_sec, 'Projects', base_url)

  acad_sec = _slice_between(clean, 'id="academic-writeups"', ('id="contact"',))
  acad_groups = parse_card_groups(acad_sec, 'Academic', base_url)

  presentations_cards: List[Dict[str, Any]] = []
  for cat, note, cards in pub_groups:
    cat_lower = cat.lower()
    if 'paper' in cat_lower:
      lines.extend(['## Publications', ''])
      for card in cards:
        s_meta = _match_scholar(card['title'], scholar_map)
        detail_bits: List[str] = []
        if s_meta and s_meta['venue']:
          detail_bits.append(s_meta['venue'])
        elif card['links']:
          detail_bits.append(card['links'][0][0])
        if s_meta:
          if s_meta['authors']:
            detail_bits.append(f"Authors: {s_meta['authors']}")
          if s_meta['citations'] > 0:
            detail_bits.append(f"{s_meta['citations']} citations")
        lines.append(
            _format_card_bullet(
                card,
                detail_text='; '.join(detail_bits),
                base_url=base_url,
            ))
      lines.append('')
    elif 'patent' in cat_lower:
      lines.extend(['## Patents', ''])
      for idx, card in enumerate(cards):
        primary_url = card['links'][0][1] if card['links'] else ''
        p_meta = patent_map.get(primary_url, {})
        p_bits = [
            b for b in (p_meta.get('number', ''), p_meta.get('abstract', ''))
            if b
        ]
        extra = note if (idx == 0 and note) else ''
        lines.append(
            _format_card_bullet(
                card,
                detail_text=' — '.join(p_bits),
                extra_suffix=extra,
                base_url=base_url,
            ))
      lines.append('')
    elif 'presentation' in cat_lower:
      presentations_cards.extend(cards)

  optional_bullets: List[str] = []
  for cat, _, cards in proj_groups:
    if 'artificial intelligence' in cat.lower() or 'ai/ml' in cat.lower():
      lines.extend([f'## Projects — {cat}', ''])
      for card in cards:
        detail = _enrich_project_detail(card, gh_map)
        lines.append(
            _format_card_bullet(card, detail_text=detail, base_url=base_url))
      lines.append('')
    else:
      for card in cards:
        detail = _enrich_project_detail(card, gh_map)
        optional_bullets.append(
            _format_card_bullet(
                card,
                category_prefix=cat,
                detail_text=detail,
                base_url=base_url,
            ))

  for _, _, cards in blog_groups:
    lines.extend(['## Research Blogs & Product Releases', ''])
    for card in cards:
      topic = ''
      for _, url in card['links']:
        if url in blog_map:
          topic = blog_map[url]
          break
      if topic and card['links']:
        detail = f"{card['links'][0][0]} — {topic}"
      else:
        detail = ''
      lines.append(
          _format_card_bullet(card, detail_text=detail, base_url=base_url))
    lines.append('')

  if presentations_cards:
    lines.extend(['## Lectures & Technical Presentations', ''])
    for card in presentations_cards:
      lines.append(_format_card_bullet(card, base_url=base_url))
    lines.append('')

  for cat, _, cards in acad_groups:
    for card in cards:
      optional_bullets.append(
          _format_card_bullet(card, category_prefix=cat, base_url=base_url))

  for lbl, url in resume['downloads']:
    optional_bullets.append(
        f'- [{lbl}]({url}): Archival PDF snapshot (see above for current work)')

  if optional_bullets:
    lines.extend(['## Optional', ''])
    lines.extend(optional_bullets)
    lines.append('')

  return '\n'.join(lines).rstrip() + '\n'


def write_llms_txt(
    html_path: str = config.HTML_PATH,
    output_path: str = config.LLMS_TXT_PATH,
    base_url: str = config.SITE_URL,
) -> None:
  """Reads index.html and writes the synchronized /llms.txt file.

  Args:
    html_path (str): Path to source index.html.
    output_path (str): Destination path for llms.txt.
    base_url (str): Canonical site URL.
  """
  with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()
  content = generate_llms_txt(html, base_url=base_url)
  with open(output_path, 'w', encoding='utf-8') as f:
    f.write(content)
  logger.info('Generated %s (%d bytes)', output_path, len(content))


def main() -> None:
  """CLI entry point for generating /llms.txt."""
  logging.basicConfig(level=logging.INFO, format='%(message)s')
  write_llms_txt()


if __name__ == '__main__':
  main()
