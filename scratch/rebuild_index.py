"""Script to programmatically rebuild index.html using the PageBuilder library."""

import os
import subprocess
from processing.builder import PageBuilder

BASE_DIR = '/Users/jakegarrison/Downloads/projects/website'
INDEX_PATH = os.path.join(BASE_DIR, 'index.html')


def rebuild() -> None:
  # 1. Read original tabbed baseline version from git commit 0b14894
  cmd = ['git', 'show', '0b148940550d42e3d1a93339ad5fa3be3f840486:index.html']
  git_content = subprocess.check_output(cmd, cwd=BASE_DIR).decode('utf-8')

  # 2. Compile index.html by chaining layout builders in PageBuilder
  (PageBuilder.from_string(git_content)
   .rebuild_projects_categories()
   .rebuild_publications_and_patents()
   .reorder_nav_tabs()
   .reorder_sections()
   .restructure_resume_layout()
   .add_google_health_products()
   .replace_offline_links_with_archives()
   .add_year_labels_to_assets()
   .enable_lazy_loading()
   .normalize_headers()
   .save(INDEX_PATH))

  print("Successfully rebuilt and formatted tabbed index.html.")


if __name__ == '__main__':
  rebuild()
