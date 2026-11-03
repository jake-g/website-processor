"""Mines topic tags from the site and synced profile outputs.

Counts each tag in config.TOPIC_TAGS per source (site sections, Scholar,
GitHub, blogs, patents) and lists frequent multi-word phrases that are not
yet covered by a tag, to suggest new vocabulary.

Usage:
  PYTHONPATH=.. python3 -m processing.tags
"""

import collections
import json
import logging
import os
import re
from typing import Dict, List, Tuple

from bs4 import BeautifulSoup

from processing import config
from processing import topics

logger = logging.getLogger(__name__)

# Site sections keyed by their element id in index.html.
SITE_SECTIONS = ('about', 'resume', 'projects', 'blogs', 'papers', 'contact')
# Your own work only (blogs_discovered.md is other people's posts).
OUTPUT_SOURCES = ('publications.md', 'github_projects.md', 'blogs.md',
                  'patents.md')
TAGS_MD = os.path.join(config.OUTPUTS_DIR, 'tags.md')
TAGS_JSON = os.path.join(config.OUTPUTS_DIR, 'tags.json')

_STOP = set(
    """a an and are as at be by for from has have in into is it its of on
or that the this to using via was were with we our you your new how can
based towards toward learning model models data paper read blog code pdf
arxiv github link view description provided recent commits language
python preprint scholar patent us filed pending no mixed""".split())


def site_section_texts(html: str) -> Dict[str, str]:
  """Returns visible text per site section.

  Args:
    html (str): index.html contents.

  Returns:
    Dict[str, str]: Section id -> plain text. Papers and patents live inside
    the blogs container, so 'papers' covers from the Papers heading on.
  """
  soup = BeautifulSoup(html, 'html.parser')
  for tag in soup(['script', 'style', 'head']):
    tag.decompose()
  texts = {}
  for sid in SITE_SECTIONS:
    el = soup.find(id=sid)
    if el is None:
      continue
    if el.name.startswith('h'):  # Heading anchor: take following siblings.
      parts = [el.get_text(' ')
              ] + [s.get_text(' ') for s in el.find_next_siblings()]
      texts[sid] = ' '.join(parts)
    else:
      texts[sid] = el.get_text(' ')
  if 'papers' in texts and 'blogs' in texts:
    texts['blogs'] = texts['blogs'].replace(texts['papers'], ' ')
  return {k: re.sub(r'\s+', ' ', v) for k, v in texts.items()}


def output_texts() -> Dict[str, str]:
  """Returns text of synced profile outputs that exist."""
  texts = {}
  for name in OUTPUT_SOURCES:
    path = os.path.join(config.OUTPUTS_DIR, name)
    if os.path.exists(path):
      with open(path, 'r', encoding='utf-8') as f:
        texts[name] = strip_markup(f.read())
  return texts


def strip_markup(text: str) -> str:
  """Keeps Markdown link text and drops URLs so they don't skew counts."""
  text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
  return re.sub(r'https?://\S+', ' ', text)


def candidate_phrases(text: str, top_n: int = 25) -> List[Tuple[str, int]]:
  """Frequent 2-3 word phrases not already matched by a tag.

  Args:
    text (str): Combined text.
    top_n (int): Number of phrases to return.

  Returns:
    List[Tuple[str, int]]: (phrase, count), most frequent first.
  """
  words = re.findall(r"[a-z][a-z0-9\-]+", text.lower())
  counter = collections.Counter()
  for n in (2, 3):
    for i in range(len(words) - n + 1):
      gram = words[i:i + n]
      if gram[0] in _STOP or gram[-1] in _STOP:
        continue
      counter[' '.join(gram)] += 1
  out = []
  for phrase, count in counter.most_common():
    if count < 3:
      break
    if not topics.count_tags(phrase):
      out.append((phrase, count))
    if len(out) >= top_n:
      break
  return out


def mine() -> dict:
  """Builds the tag report.

  Returns:
    dict: {'by_source': {source: {tag: count}}, 'totals': {tag: count},
    'candidates': [(phrase, count)]}.
  """
  with open(config.HTML_PATH, 'r', encoding='utf-8') as f:
    sources = {f'site:{k}': v for k, v in site_section_texts(f.read()).items()}
  sources.update(output_texts())
  by_source = {name: topics.count_tags(text) for name, text in sources.items()}
  totals = collections.Counter()
  for counts in by_source.values():
    totals.update(counts)
  return {
      'by_source': by_source,
      'totals': dict(totals.most_common()),
      'candidates': candidate_phrases(' '.join(sources.values())),
  }


def to_markdown(report: dict) -> str:
  """Formats the tag report as Markdown tables."""
  srcs = list(report['by_source'])
  lines = [
      '# Topic tags\n', '| Tag | Total | ' + ' | '.join(srcs) + ' |',
      '| --- | ---: |' + ' ---: |' * len(srcs)
  ]
  for tag in sorted(set(config.TOPIC_TAGS) | set(report['totals']),
                    key=lambda t: -report['totals'].get(t, 0)):
    cells = [str(report['by_source'][s].get(tag, '')) for s in srcs]
    lines.append(f"| {tag} | {report['totals'].get(tag, 0)} | " +
                 ' | '.join(cells) + ' |')
  lines += [
      '\n## Untagged frequent phrases (vocabulary ideas)\n',
      '| Phrase | Count |', '| --- | ---: |'
  ]
  lines += [f'| {p} | {c} |' for p, c in report['candidates']]
  return '\n'.join(lines) + '\n'


def main() -> None:
  """CLI entry point."""
  logging.basicConfig(level=logging.INFO, format='%(message)s')
  report = mine()
  os.makedirs(config.OUTPUTS_DIR, exist_ok=True)
  with open(TAGS_JSON, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2)
  with open(TAGS_MD, 'w', encoding='utf-8') as f:
    f.write(to_markdown(report))
  logger.info('Wrote %s and %s', TAGS_MD, TAGS_JSON)


if __name__ == '__main__':
  main()
