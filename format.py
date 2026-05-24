"""Utility script to format Python, HTML, CSS, and JS files in the project."""

import logging
import os
import re
import subprocess

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def format_python_files() -> None:
  """Formats Python files in processing/ using a temporary yapf installation."""
  logger.info('Formatting Python files in processing/ using yapf...')
  cmd = (
      'python3 -m venv venv && '
      'venv/bin/pip install -q yapf && '
      'venv/bin/yapf -i --style="{based_on_style: google, indent_width: 2, column_limit: 80}" processing/*.py && '
      'rm -rf venv')
  try:
    subprocess.run(cmd, shell=True, check=True)
    logger.info('✅ Python files formatted successfully.')
  except Exception as e:  # pylint: disable=broad-except
    logger.error('Failed to format Python files: %s', e)


def format_web_file(file_path: str) -> None:
  """Formats HTML, CSS, or JS files by trimming trailing whitespace and normalizing endings.

  Args:
      file_path (str): Path to the web file.
  """
  if not os.path.exists(file_path):
    logger.warning('File %s does not exist. Skipping.', file_path)
    return

  try:
    with open(file_path, 'rb') as f:
      content = f.read().decode('utf-8')

    # 1. Normalize line endings to LF (\n)
    content = content.replace('\r\n', '\n')

    # 2. Trim trailing whitespaces on each line
    lines = [line.rstrip() for line in content.split('\n')]

    # Ensure file ends with exactly one newline
    formatted_content = '\n'.join(lines)
    if not formatted_content.endswith('\n'):
      formatted_content += '\n'

    # Normalize multiple trailing newlines
    formatted_content = re.sub(r'\n+$', '\n', formatted_content)

    with open(file_path, 'wb') as f:
      f.write(formatted_content.encode('utf-8'))

    logger.info('Formatted web file: %s', os.path.basename(file_path))
  except Exception as e:  # pylint: disable=broad-except
    logger.error('Failed to format web file %s: %s', file_path, e)


def main() -> None:
  base_dir = '/Users/jakegarrison/Downloads/projects/website'

  # Format Python scripts
  format_python_files()

  # Format HTML & CSS files in-place
  format_web_file(os.path.join(base_dir, 'index.html'))
  format_web_file(os.path.join(base_dir, 'main.css'))


if __name__ == '__main__':
  main()
