"""Structured asset processing library: CSS minifier and image/PDF compressors."""

import json
import logging
import os
import re
import shutil
import subprocess
import hashlib
from PIL import Image
from processing import config

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class WebMinifier:
  """CSS stylesheet minification engine."""

  def minify_css(self, input_path: str, output_path: str) -> None:
    """Minifies CSS by stripping comments and duplicate whitespaces."""
    try:
      with open(input_path, 'r', encoding='utf-8') as f:
        css = f.read()
      css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
      css = re.sub(r'\s*([\{\}:;,])\s*', r'\1', css)
      css = re.sub(r'\s+', ' ', css).strip()
      with open(output_path, 'w', encoding='utf-8') as f:
        f.write(css)
      logger.info('Minified CSS: %s -> %s', input_path, output_path)
    except Exception as e:  # pylint: disable=broad-except
      logger.error('Failed to minify CSS: %s', e)


def load_global_cache() -> dict:
  """Loads the merged optimization cache from disk."""
  if os.path.exists(config.COMPRESS_CACHE_PATH):
    try:
      with open(config.COMPRESS_CACHE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)
    except Exception as e:  # pylint: disable=broad-except
      logger.warning('Failed to load compress cache: %s', e)
  return {}


def save_global_cache(cache: dict) -> None:
  """Saves the merged optimization cache to disk."""
  try:
    os.makedirs(os.path.dirname(config.COMPRESS_CACHE_PATH), exist_ok=True)
    with open(config.COMPRESS_CACHE_PATH, 'w', encoding='utf-8') as f:
      json.dump(cache, f, indent=2)
  except Exception as e:  # pylint: disable=broad-except
    logger.error('Failed to save compress cache: %s', e)


class ImageCompressor:
  """In-place compressor for large JPEGs and PNGs."""

  def __init__(self, image_dir: str):
    self.image_dir = image_dir

  def _load_cache(self) -> dict:
    return load_global_cache().get('images', {})

  def _save_cache(self, cache: dict) -> None:
    full_cache = load_global_cache()
    full_cache['images'] = cache
    save_global_cache(full_cache)

  def _get_file_hash(self, file_path: str) -> str:
    hash_md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
      for chunk in iter(lambda: f.read(4096), b''):
        hash_md5.update(chunk)
    return hash_md5.hexdigest()

  def _compress_file(self, file_path: str, quality: int = 80) -> bool:
    try:
      ext = os.path.splitext(file_path)[1].lower()
      with Image.open(file_path) as img:
        if ext in ('.jpg', '.jpeg') and img.mode == 'RGBA':
          img = img.convert('RGB')
        if ext in ('.jpg', '.jpeg'):
          img.save(file_path, 'JPEG', optimize=True, quality=quality)
        elif ext == '.png':
          img.save(file_path, 'PNG', optimize=True)
      return True
    except Exception as e:  # pylint: disable=broad-except
      logger.error('Failed to compress image file %s: %s', file_path, e)
      return False

  def run(self) -> None:
    """Optimizes new large images in-place and caches statistics."""
    if not os.path.exists(self.image_dir):
      logger.error('Images directory %s does not exist', self.image_dir)
      return

    cache = self._load_cache()
    updated_cache = {}

    logger.info('Scanning images for optimization (Threshold: >250KB)...')
    for root, _, files in os.walk(self.image_dir):
      for file in files:
        file_path = os.path.join(root, file)
        ext = os.path.splitext(file)[1].lower()
        if ext not in ('.jpg', '.jpeg', '.png'):
          continue

        size = os.path.getsize(file_path)
        rel_path = os.path.relpath(file_path, self.image_dir)
        mtime = os.path.getmtime(file_path)

        is_cached = False
        if rel_path in cache:
          cached_entry = cache[rel_path]
          if cached_entry.get('mtime') == mtime and cached_entry.get(
              'size') == size:
            is_cached = True
            updated_cache[rel_path] = cached_entry

        if is_cached:
          continue

        if size > config.MAX_IMAGE_SIZE_BYTES:
          logger.info('Oversized asset detected: %s (%.2f KB)', rel_path,
                      size / 1024)
          success = self._compress_file(file_path,
                                        quality=config.DEFAULT_JPEG_QUALITY)
          if success:
            new_size = os.path.getsize(file_path)
            new_mtime = os.path.getmtime(file_path)
            updated_cache[rel_path] = {
                'size': new_size,
                'mtime': new_mtime,
                'hash': self._get_file_hash(file_path)
            }
          else:
            updated_cache[rel_path] = {
                'size': size,
                'mtime': mtime,
                'hash': self._get_file_hash(file_path)
            }
        else:
          updated_cache[rel_path] = {
              'size': size,
              'mtime': mtime,
              'hash': self._get_file_hash(file_path)
          }

    self._save_cache(updated_cache)
    logger.info('Image scan and optimization completed.')


class PdfCompressor:
  """PDF document sizing checking and Ghostscript compressor."""

  def __init__(self, doc_dir: str):
    self.doc_dir = doc_dir

  def _load_cache(self) -> dict:
    return load_global_cache().get('pdfs', {})

  def _save_cache(self, cache: dict) -> None:
    full_cache = load_global_cache()
    full_cache['pdfs'] = cache
    save_global_cache(full_cache)

  def _is_gs_available(self) -> bool:
    return shutil.which('gs') is not None

  def _compress_file(self, input_path: str, output_path: str) -> bool:
    cmd = [
        'gs', '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
        '-dPDFSETTINGS=/screen', '-dNOPAUSE', '-dQUIET', '-dBATCH',
        f'-sOutputFile={output_path}', input_path
    ]
    try:
      result = subprocess.run(cmd, capture_output=True, text=True, check=True)
      return result.returncode == 0
    except Exception as e:  # pylint: disable=broad-except
      logger.error('Ghostscript compression failed: %s', e)
      return False

  def run(self) -> None:
    """Checks and compresses large PDFs using Ghostscript."""
    if not os.path.exists(self.doc_dir):
      logger.error('Documents directory %s does not exist', self.doc_dir)
      return

    cache = self._load_cache()
    updated_cache = {}

    gs_available = self._is_gs_available()
    if not gs_available:
      logger.warning(
          '\n[WARNING] Ghostscript ("gs") is not installed on this system.\n'
          'To enable PDF compression, please install it (e.g., "brew install ghostscript").'
      )

    logger.info('Scanning PDFs for optimization (Threshold: >1.5MB)...')
    for root, _, files in os.walk(self.doc_dir):
      for file in files:
        if not file.lower().endswith('.pdf'):
          continue

        file_path = os.path.join(root, file)
        size = os.path.getsize(file_path)
        rel_path = os.path.relpath(file_path, self.doc_dir)
        mtime = os.path.getmtime(file_path)

        is_cached = False
        if rel_path in cache:
          cached_entry = cache[rel_path]
          if cached_entry.get('mtime') == mtime and cached_entry.get(
              'size') == size:
            is_cached = True
            updated_cache[rel_path] = cached_entry

        if is_cached:
          continue

        if size > config.MAX_PDF_SIZE_BYTES:
          logger.info('Oversized PDF detected: %s (%.2f MB)', rel_path,
                      size / (1024 * 1024))
          if gs_available:
            temp_path = file_path + '.tmp'
            success = self._compress_file(file_path, temp_path)
            if success:
              orig_size = size
              shutil.move(temp_path, file_path)
              new_size = os.path.getsize(file_path)
              new_mtime = os.path.getmtime(file_path)
              logger.info('Compressed %s: %.2f MB -> %.2f MB', file,
                          orig_size / (1024 * 1024), new_size / (1024 * 1024))
              updated_cache[rel_path] = {
                  'size': new_size,
                  'mtime': new_mtime,
                  'status': 'compressed'
              }
            else:
              if os.path.exists(temp_path):
                os.remove(temp_path)
              updated_cache[rel_path] = {
                  'size': size,
                  'mtime': mtime,
                  'status': 'compression_failed'
              }
          else:
            logger.warning(
                '[WARNING] Cannot compress %s. Install Ghostscript to shrink it.',
                file)
            updated_cache[rel_path] = {
                'size': size,
                'mtime': mtime,
                'status': 'ghostscript_missing'
            }
        else:
          updated_cache[rel_path] = {
              'size': size,
              'mtime': mtime,
              'status': 'skipped_under_size'
          }

    self._save_cache(updated_cache)
    logger.info('PDF scan completed.')


def check_asset_sizes(image_dir: str, doc_dir: str) -> None:
  """Scans folders and logs warnings for assets exceeding size rules."""
  logger.info('\nChecking asset sizes...')
  # Check image sizes (max 250KB recommended)
  if os.path.exists(image_dir):
    for root, _, files in os.walk(image_dir):
      for file in files:
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
          path = os.path.join(root, file)
          size = os.path.getsize(path)
          if size > config.MAX_IMAGE_SIZE_BYTES:
            logger.warning(
                '[WARNING] Image file is larger than average: %s (%.2f KB > 250 KB)',
                file, size / 1024)

  # Check PDF sizes (max 1.5MB recommended)
  if os.path.exists(doc_dir):
    for root, _, files in os.walk(doc_dir):
      for file in files:
        if file.lower().endswith('.pdf'):
          path = os.path.join(root, file)
          size = os.path.getsize(path)
          if size > config.MAX_PDF_SIZE_BYTES:
            logger.warning(
                '[WARNING] PDF file is larger than average: %s (%.2f MB > 1.5 MB)',
                file, size / (1024 * 1024))


def main() -> None:
  # Minify CSS
  minifier = WebMinifier()
  minifier.minify_css(config.CSS_PATH, config.MIN_CSS_PATH)

  # Run Compressors
  img_comp = ImageCompressor(config.IMAGE_DIR)
  img_comp.run()

  pdf_comp = PdfCompressor(config.DOC_DIR)
  pdf_comp.run()

  # Print warning check logs
  check_asset_sizes(config.IMAGE_DIR, config.DOC_DIR)


if __name__ == '__main__':
  main()
