"""Automated image importer, resizer, aspect ratio checker, and compressor."""

import logging
import os
from PIL import Image

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = '/Users/jakegarrison/Downloads/projects/website'
SOURCE_DIR = os.path.join(BASE_DIR, 'new images')
TARGET_DIR = os.path.join(BASE_DIR, 'image')

# Map targets and expected aspect ratios
IMAGE_METADATA = {
    'asthma.png': [
        {
            'target_name': 'asthma.jpg',
            'target_ratio': 0.77,  # Squarish-vertical paper format (1:1.29)
            'description': 'Asthma Pilot Study Paper Preview'
        }
    ],
    'era_blog.png': [
        {
            'target_name': 'era_blog.jpg',
            'target_ratio': 1.11,  # Squarish-horizontal card (10:9)
            'description': 'ERA & GIFT-Eval Blog Card'
        }
    ],
    'era_nature_blog.png': [
        {
            'target_name': 'era_nature_blog.jpg',
            'target_ratio': 1.11,  # Squarish-horizontal card (10:9)
            'description': 'ERA Nature Medicine Blog Card'
        }
    ],
    'health_agent.png': [
        {
            'target_name': 'health_agent.jpg',
            'target_ratio': 0.77,  # Squarish-vertical paper format (1:1.29)
            'description': 'Personal Health Agent Paper Preview'
        }
    ],
    'hear_disease_blog.png': [
        {
            'target_name': 'hear_disease_blog.jpg',
            'target_ratio': 1.11,  # Squarish-horizontal card (10:9)
            'description': 'HeAR Cough Disease Detection Blog Card'
        }
    ],
    'hear_model_card.png': [
        {
            'target_name': 'hear_model_card.jpg',
            'target_ratio': 1.11,  # Squarish-horizontal card (10:9)
            'description': 'HeAR Model Card Developer Docs Card'
        }
    ],
    'insulin_wearables_blog.png': [
        {
            'target_name': 'insulin_wearables_blog.jpg',
            'target_ratio': 1.11,  # Squarish-horizontal card (10:9)
            'description': 'Insulin Resistance Wearables Blog Card'
        }
    ],
    'lsm1.png': [
        {
            'target_name': 'lsm1.jpg',
            'target_ratio': 0.77,  # Squarish-vertical paper format (1:1.29)
            'description': 'Scaling Wearable Foundation Models Paper Preview'
        }
    ],
    'lsm1_blog.png': [
        {
            'target_name': 'lsm1_blog.jpg',
            'target_ratio': 1.11,  # Squarish-horizontal card (10:9)
            'description': 'Scaling Wearable Foundation Models Blog Card'
        }
    ],
    'lsm2.png': [
        {
            'target_name': 'lsm2.jpg',
            'target_ratio': 0.77,  # Squarish-vertical paper format (1:1.29)
            'description': 'LSM-2 Paper Preview'
        }
    ],
    'lsm2_blog.png': [
        {
            'target_name': 'lsm2_blog.jpg',
            'target_ratio': 1.11,  # Squarish-horizontal card (10:9)
            'description': 'LSM-2 Research Blog Card'
        }
    ],
    'sensorlm.png': [
        {
            'target_name': 'sensorlm.jpg',
            'target_ratio': 0.77,  # Squarish-vertical paper format (1:1.29)
            'description': 'SensorLM Paper Preview'
        }
    ],
    'sensorlm_blog.png': [
        {
            'target_name': 'sensorlm_blog.jpg',
            'target_ratio': 1.11,  # Squarish-horizontal card (10:9)
            'description': 'SensorLM Research Blog Card'
        }
    ],
    'probabilistic_reasoning.png': [
        {
            'target_name': 'probabilistic_reasoning.jpg',
            'target_ratio': 0.77,  # Squarish-vertical paper format (1:1.29)
            'description': 'Probabilistic Reasoning Paper Preview'
        }
    ],
    'frill_speech_blog.png': [
        {
            'target_name': 'frill_speech_blog.jpg',
            'target_ratio': 1.11,  # Squarish-horizontal card (10:9)
            'description': 'FRILL On-Device Speech Blog Card'
        }
    ],
    'nest_hub_sleep_blog.png': [
        {
            'target_name': 'nest_hub_sleep_blog.jpg',
            'target_ratio': 1.11,  # Squarish-horizontal card (10:9)
            'description': 'Nest Hub Sleep Sensing Blog Card'
        }
    ],
    'nest_hub_contactless_blog.png': [
        {
            'target_name': 'nest_hub_contactless_blog.jpg',
            'target_ratio': 1.11,  # Squarish-horizontal card (10:9)
            'description': 'Nest Hub Contactless Sleep Blog Card'
        }
    ],
    'nest_hub_enhanced_blog.png': [
        {
            'target_name': 'nest_hub_enhanced_blog.jpg',
            'target_ratio': 1.11,  # Squarish-horizontal card (10:9)
            'description': 'Nest Hub Enhanced Respiration Blog Card'
        }
    ],
    'ableton-parse.png': [
        {
            'target_name': 'ableton-parser.jpg',
            'target_ratio': 1.33,  # Projects format (4:3)
            'description': 'Ableton Live Project Parser Project Card'
        }
    ],
    'esp32-llm-output.png': [
        {
            'target_name': 'esp32-llm-output.jpg',
            'target_ratio': 1.33,
            'description': 'ESP32 LLM Runner Output Screenshot'
        }
    ],
    'esp32-llm.png': [
        {
            'target_name': 'esp32-llm.jpg',
            'target_ratio': 1.33,
            'description': 'ESP32 LLM Runner Hardware Card'
        }
    ],
    'home-scraper-site.jpg': [
        {
            'target_name': 'home-scraper-site.jpg',
            'target_ratio': 1.33,
            'description': 'Home Listings Scraper Web Site Card'
        }
    ],
    'home-scraper.png': [
        {
            'target_name': 'home-scraper.jpg',
            'target_ratio': 1.33,
            'description': 'Home Listings Scraper Database Card'
        }
    ],
    'lastfm-sync.png': [
        {
            'target_name': 'lastfm-sync.jpg',
            'target_ratio': 1.33,
            'description': 'Last.fm Scrobble Sync Card'
        }
    ],
    'market-pipeline.png': [
        {
            'target_name': 'market-pipeline.jpg',
            'target_ratio': 1.33,
            'description': 'Market Data News Pipeline Card'
        }
    ],
    'microcontroller-tutorial.png': [
        {
            'target_name': 'microcontroller-tutorial.jpg',
            'target_ratio': 1.33,
            'description': 'Microcontroller Development Tutorial Card'
        }
    ],
    'mujoco-puppeteer.png': [
        {
            'target_name': 'mujoco-puppeteer.jpg',
            'target_ratio': 1.33,
            'description': 'MuJoCo Controls Simulator Card'
        }
    ],
    'plex-sync.png': [
        {
            'target_name': 'plex-sync.jpg',
            'target_ratio': 1.33,
            'description': 'Plex Playlists Sync Card'
        }
    ],
    'reddit-scraper.png': [
        {
            'target_name': 'reddit-scraper.jpg',
            'target_ratio': 1.33,
            'description': 'Reddit Scraper Card'
        }
    ],
    'tesla_autopilot.png': [
        {
            'target_name': 'tesla_autopilot.jpg',
            'target_ratio': 1.33,
            'description': 'Tesla Autopilot Driver Assist Card'
        }
    ],
    'ytmusic.png': [
        {
            'target_name': 'ytmusic.jpg',
            'target_ratio': 1.33,
            'description': 'YouTube Music Library Aligner Card'
        }
    ],
    'brewing.png': [
        {
            'target_name': 'brewing.jpg',
            'target_ratio': 1.33,
            'description': 'Fermentation Brewing Project Card'
        }
    ],
    'brewing-2.png': [
        {
            'target_name': 'brewing-2.jpg',
            'target_ratio': 1.33,
            'description': 'Fermentation Brewing Setup Image'
        }
    ],
    'embedded_ai.png': [
        {
            'target_name': 'embedded_ai_presentation.jpg',
            'target_ratio': 1.77,  # Presentations format (16:9)
            'description': 'Embedded AI & Platforms Course Presentation Card'
        }
    ],
    'freshair_spiro.png': [
        {
            'target_name': 'freshair_spiro.jpg',
            'target_ratio': 1.77,
            'description': 'FreshAir Spiro Presentation Card'
        }
    ],
    'product_engineering.png': [
        {
            'target_name': 'product_engineering_presentation.jpg',
            'target_ratio': 1.77,
            'description': 'Consumer Product Engineering Presentation Card'
        }
    ],
    'terrarium.png': [
        {
            'target_name': 'terrarium_proj.jpg',
            'target_ratio': 1.33,
            'description': 'Automated IoT Terrarium Project Card'
        }
    ],
    'world_data.png': [
        {
            'target_name': 'world_data_presentation.jpg',
            'target_ratio': 1.77,
            'description': 'Understanding World Through Data Presentation Card'
        }
    ],
    'vocal-chords.png': [
        {
            'target_name': 'vocal-chords.jpg',
            'target_ratio': 1.33,
            'description': 'Vocal Chord Synthesis Project Card'
        }
    ]
}

MAX_WIDTH = 800
JPEG_QUALITY = 80


def process_images() -> None:
  """Processes, resizes, checks aspect ratios, and compresses new images."""
  if not os.path.exists(SOURCE_DIR):
    logger.error('Source directory %s not found!', SOURCE_DIR)
    return

  os.makedirs(TARGET_DIR, exist_ok=True)

  for filename, targets in IMAGE_METADATA.items():
    source_path = os.path.join(SOURCE_DIR, filename)
    if not os.path.exists(source_path):
      logger.warning('Skipping: %s not found in source directory.', filename)
      continue

    for target in targets:
      target_path = os.path.join(TARGET_DIR, target['target_name'])

      try:
        with Image.open(source_path) as img:
          width, height = img.size
          actual_ratio = round(width / height, 2)
          target_ratio = target['target_ratio']

          # 1. Aspect Ratio Anomaly Warning Check
          deviation = abs(actual_ratio - target_ratio) / target_ratio
          if deviation > 0.15:
            logger.warning(
                '[WARNING] Aspect ratio anomaly detected for %s (%s):\n'
                '  Actual aspect ratio: %s (%dx%d)\n'
                '  Target aspect ratio: %s\n'
                '  Please check if visual clipping or skewing occurs on-site.',
                filename, target['description'], actual_ratio, width, height,
                target_ratio
            )
          else:
            logger.info(
                'Aspect ratio check passed for %s -> %s: %s (Target: %s)',
                filename, target['target_name'], actual_ratio, target_ratio
            )

          # 2. Resize maintaining aspect ratio (Max Width 800px)
          if width > MAX_WIDTH:
            new_width = MAX_WIDTH
            new_height = int(height * (MAX_WIDTH / width))
            logger.info('Resizing %s for %s from %dx%d to %dx%d...', filename,
                        target['target_name'], width, height, new_width,
                        new_height)
            img_resized = img.resize((new_width, new_height),
                                     Image.Resampling.LANCZOS)
          else:
            logger.info('No resizing needed for %s -> %s (%dx%d).', filename,
                        target['target_name'], width, height)
            img_resized = img

          # 3. Convert to RGB if PNG/RGBA and save as compressed JPEG
          if img_resized.mode in ('RGBA', 'LA'):
            img_resized = img_resized.convert('RGB')
          img_resized.save(target_path, 'JPEG', optimize=True,
                           quality=JPEG_QUALITY)

          logger.info(
              'Successfully imported & compressed: %s -> %s (%.2f KB)\n',
              filename, target['target_name'], os.path.getsize(target_path) / 1024
          )

      except Exception as e:
        logger.error('Error processing %s for %s: %s', filename,
                     target['target_name'], e)


if __name__ == '__main__':
  process_images()
