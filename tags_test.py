"""Tests for topic matching, tag mining, and research blog parsing."""

import unittest

from processing import fetchers
from processing import tags
from processing import topics

_VOCAB = {
    'self-improving ai': [r'self-improving', r'rsi'],
    'health agents': [r'health agents?'],
}


class TopicsTest(unittest.TestCase):

  def test_count_tags_word_bounded_and_case_insensitive(self):
    text = 'Self-improving agents; RSI loop. Health agent. versions rsix'
    self.assertEqual(topics.count_tags(text, _VOCAB), {
        'self-improving ai': 2,
        'health agents': 1
    })

  def test_mentions_author(self):
    self.assertTrue(topics.mentions_author('Thanks to Jake Garrison.'))
    self.assertFalse(topics.mentions_author('Thanks to Jake.'))


class TagsTest(unittest.TestCase):

  def test_site_section_texts_splits_papers_from_blogs(self):
    html = ('<div id="blogs"><p>blog post</p><h4 id="papers">Papers</h4>'
            '<div>paper one</div></div><div id="projects">proj</div>')
    texts = tags.site_section_texts(html)
    self.assertIn('paper one', texts['papers'])
    self.assertNotIn('paper one', texts['blogs'])
    self.assertIn('blog post', texts['blogs'])
    self.assertEqual(texts['projects'].strip(), 'proj')

  def test_strip_markup_keeps_link_text(self):
    self.assertEqual(
        tags.strip_markup('[Read Blog](https://x.y/z) see https://a.b').split(),
        ['Read', 'Blog', 'see'])

  def test_candidate_phrases_skips_stopwords(self):
    text = 'sleep sensing ' * 3 + 'of the ' * 5
    phrases = dict(tags.candidate_phrases(text))
    self.assertNotIn('of the', phrases)


class ResearchBlogFetcherTest(unittest.TestCase):

  def test_parse_rss_and_scan(self):
    f = fetchers.ResearchBlogFetcher('rss', 'cache.json', 'index.html')
    rss = ('<rss><channel><item><title>T</title>'
           '<guid>https://research.google/blog/t/</guid>'
           '<pubDate>Tue, 27 Oct 2026 17:35:00 +0000</pubDate>'
           '<category>Health</category></item></channel></rss>')
    items = f.parse_rss(rss)
    self.assertEqual(items[0]['url'], 'https://research.google/blog/t/')
    self.assertEqual(items[0]['date'], '2026-10-27')
    self.assertEqual(items[0]['categories'], ['Health'])
    scan = f.scan_post('<html><body><p>Wearable foundation models. '
                       'Acknowledgements: Jake Garrison</p></body></html>')
    self.assertTrue(scan['mentions_author'])
    self.assertIn('foundation models', scan['tags'])


if __name__ == '__main__':
  unittest.main()
