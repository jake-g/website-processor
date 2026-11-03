"""Shared topic matching used by blog discovery and tag mining."""

import functools
import re
from typing import Dict, Mapping, Sequence

from processing import config


@functools.lru_cache(maxsize=None)
def _compiled(tags_key: tuple) -> Dict[str, re.Pattern]:
  """Compiles one alternation regex per tag (cached by vocabulary content)."""
  return {
      tag: re.compile(r'\b(?:' + '|'.join(aliases) + r')\b', re.IGNORECASE)
      for tag, aliases in tags_key
  }


def _key(tags: Mapping[str, Sequence[str]]) -> tuple:
  return tuple((t, tuple(a)) for t, a in tags.items())


def count_tags(text: str,
               tags: Mapping[str, Sequence[str]] = None) -> Dict[str, int]:
  """Counts occurrences of each topic tag in text.

  Args:
    text (str): Plain text to scan.
    tags (Mapping[str, Sequence[str]]): Tag -> regex aliases. Defaults to
      config.TOPIC_TAGS.

  Returns:
    Dict[str, int]: Tag -> match count, only tags with at least one match.
  """
  patterns = _compiled(_key(tags or config.TOPIC_TAGS))
  counts = {tag: len(p.findall(text)) for tag, p in patterns.items()}
  return {t: c for t, c in counts.items() if c}


def mentions_author(text: str, names: Sequence[str] = None) -> bool:
  """Returns True if any author name variant appears in text."""
  names = names or config.AUTHOR_NAMES
  return any(re.search(re.escape(n), text, re.IGNORECASE) for n in names)
