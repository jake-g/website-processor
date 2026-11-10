"""Unit tests for processing/llms_txt.py."""

import os
import re
import tempfile
import unittest

from processing import config
from processing import llms_txt

_SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta name="description" content="Jake Garrison, AI researcher.">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "ProfilePage",
    "mainEntity": {
      "@type": "Person",
      "name": "Jake Garrison",
      "jobTitle": "AI Research Engineer",
      "worksFor": {"name": "Google"},
      "alumniOf": {"name": "University of Washington"},
      "address": {"addressLocality": "Seattle", "addressRegion": "WA"},
      "knowsAbout": ["Health agents", "Foundation models"],
      "sameAs": ["https://github.com/jake-g"]
    }
  }
  </script>
</head>
<body>
  <div id="about"><p><i>I work on health agents.</i></p></div>
  <div id="resume">
    <ul id="education-list">
      <li><details class="resume-item">
        <summary><h5>UW M.S.</h5><span class="label">2016-2018</span></summary>
        <div class="resume-body"><p>M.S. ECE</p><ul><li>UbiComp</li></ul></div>
      </details></li>
    </ul>
    <ul id="experience-list">
      <li><details class="resume-item">
        <summary>
          <h5>Google Health</h5><span class="label">2017-Present</span>
        </summary>
        <div class="resume-body">
          <p>
            <a href="https://research.google/people/jake-garrison/">Profile</a>
          </p>
          <p>Health AI research</p>
          <ul><li>Trained HeAR and SensorFM</li></ul>
        </div>
      </details></li>
    </ul>
    <div class="robots-only">
      <h4>Skills</h4><ul><li>JAX, PyTorch</li></ul>
      <h4>Interests</h4><ul><li>Music synthesis</li></ul>
      <h4>Keywords</h4><p>HeAR, SensorFM, ERA</p>
    </div>
    <details id="accomplishments">
      <h4>Awards</h4><ul><li>Best Hack (2015)</li></ul>
    </details>
    <div class="button"><div><div>
      <a href="doc/Garrison_Jake_Resume.pdf">Download Resume (2018)</a>
    </div></div></div>
  </div>
  <div id="projects">
    <h4>Artificial Intelligence (AI/ML)</h4>
    <div class="g1">
      <h6>Codegen Classroom <span class="pub-year">(2026)</span></h6>
      <p class="card-links">
        <a href="https://github.com/jake-g/codegen-classroom">GitHub</a>
      </p>
    </div>
    <h4>Automation</h4>
    <div class="g1">
      <h6>Private Bot <span class="pub-year">(2017)</span></h6>
      <p class="card-links"><span>Contact for info</span></p>
    </div>
  </div>
  <div id="blogs">
    <h4>Blogs</h4>
    <div class="g1">
      <h6>PHA Blog <span class="pub-year">(10/2026)</span></h6>
      <p class="card-links">
        <a href="https://research.google/blog/pha/">Blog</a>
      </p>
    </div>
    <div id="publications">
      <h4>Papers</h4>
      <div class="g1">
        <h6>HeAR <span class="pub-year">(03/2024)</span></h6>
        <p class="card-links">
          <a href="https://arxiv.org/abs/2403.02522">Paper (arXiv)</a>
          <a href="doc/HeAR.pdf">Slides</a>
        </p>
      </div>
      <h4>Patents</h4>
      <p style="font-style: italic;">Note: 5 pending.</p>
      <div class="g1">
        <h6>Health Data Summary <span class="pub-year">(06/2026)</span></h6>
        <p class="card-links">
          <a href="https://patents.google.com/patent/US1">Patent</a>
        </p>
      </div>
      <h4>Presentations</h4>
      <div class="g1">
        <h6>Embedded AI</h6>
        <p class="card-links"><a href="doc/slides.pdf">Slides</a></p>
      </div>
    </div>
  </div>
  <div id="academic-writeups">
    <h4>Academic Reports</h4>
    <div class="g1">
      <h6>Urban Parking <span class="pub-year">(2016)</span></h6>
      <p class="card-links"><a href="doc/parking.pdf">Report</a></p>
    </div>
  </div>
  <div id="contact">
    <a href="mailto:test@example.com">test@</a>
  </div>
</body>
</html>
"""


class TestLlmsTxt(unittest.TestCase):
  """Tests llmstxt.org v2 generation and live site synchronization."""

  def test_generate_from_synthetic_html(self) -> None:
    """Verifies H1, blockquote, intro prose, and H2 link list ordering."""
    md = llms_txt.generate_llms_txt(_SAMPLE_HTML,
                                    base_url='https://example.com',
                                    outputs_dir=None)
    lines = md.splitlines()
    self.assertEqual(lines[0], '# Jake Garrison')
    self.assertEqual(lines[2], '> Jake Garrison, AI researcher.')
    self.assertIn('I work on health agents.', md)
    self.assertIn('**Topic Index:** HeAR, SensorFM, ERA', md)

    # No headings may appear between line 1 and the first H2 section.
    first_h2 = next(i for i, line in enumerate(lines) if line.startswith('## '))
    for line in lines[1:first_h2]:
      self.assertFalse(line.startswith('#'), msg=f'Unexpected heading: {line}')

    # Every bullet inside H2 sections must start with `- [Title](https://...)`.
    link_item_re = re.compile(r'^- \[[^\]]+\]\(https?://[^)]+\)')
    for line in lines[first_h2:]:
      if not line or line.startswith('## '):
        continue
      self.assertRegex(line, link_item_re)
    self.assertNotIn('mailto:', md)

    # Verify relative doc/ paths become canonical absolute URLs.
    self.assertIn('[Slides](https://example.com/doc/HeAR.pdf)', md)
    self.assertIn('## Optional', md)
    self.assertIn(
        '[Private Bot](https://example.com/#contact): '
        '[Automation] — (2017) — Contact for info',
        md,
    )

  def test_write_llms_txt_roundtrip(self) -> None:
    """Verifies file writing helper produces non-empty output."""
    with tempfile.TemporaryDirectory() as tmp:
      html_path = os.path.join(tmp, 'index.html')
      out_path = os.path.join(tmp, 'llms.txt')
      with open(html_path, 'w', encoding='utf-8') as f:
        f.write(_SAMPLE_HTML)
      llms_txt.write_llms_txt(
          html_path=html_path,
          output_path=out_path,
          base_url='https://example.com',
      )
      self.assertTrue(os.path.isfile(out_path))
      with open(out_path, 'r', encoding='utf-8') as f:
        self.assertTrue(f.read().startswith('# Jake Garrison\n'))

  def test_repository_llms_txt_follows_v2_spec(self) -> None:
    """Guards that repository index.html generates a valid v2 /llms.txt."""
    with open(config.HTML_PATH, 'r', encoding='utf-8') as f:
      md = llms_txt.generate_llms_txt(f.read())
    self.assertTrue(md.startswith('# Jake Garrison\n\n> '))
    self.assertNotIn('mailto:', md)
    for section in (
        '## Profiles',
        '## Publications',
        '## Patents',
        '## Projects — Artificial Intelligence (AI/ML)',
        '## Research Blogs & Product Releases',
        '## Lectures & Technical Presentations',
        '## Optional',
    ):
      self.assertIn(section, md)


if __name__ == '__main__':
  unittest.main()
