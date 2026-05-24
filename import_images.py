"""Structured image importing, aspect-ratio locked cropping, and compression library.

Provides batch image importing (from 'new images/') and an interactive crop GUI.
"""

import argparse
import json
import logging
import os
import sys
from PIL import Image

try:
  import tkinter as tk
  from tkinter import messagebox
  from tkinter import ttk
except ImportError:
  tk = None
  messagebox = None
  ttk = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Base directories configuration
BASE_DIR = '/Users/jakegarrison/Downloads/projects/website'
SOURCE_DIR = os.path.join(BASE_DIR, 'image/new_image')
TARGET_DIR = os.path.join(BASE_DIR, 'image')

# Search directories for original raw images (for cropping)
SEARCH_DIRS = [
    os.path.join(BASE_DIR, 'image/new_image'),
    os.path.join(BASE_DIR, 'image/orig_image')
]

CROP_CACHE_FILE = os.path.join(BASE_DIR, 'processing/outputs/crop_cache.json')

MAX_WIDTH = 800
JPEG_QUALITY = 80

# Image metadata mapping source filename -> list of target configs
IMAGE_METADATA = {
    'asthma.png': [
        {
            'target_name': 'asthma.jpg',
            'target_ratio': 0.77,  # Squarish-vertical paper format (1:1.29)
            'description': 'Asthma Remote Sensor Assessment Paper Preview'
        }
    ],
    'era_blog.png': [
        {
            'target_name': 'era_blog.jpg',
            'target_ratio': 1.11,  # Squarish-horizontal card (10:9)
            'description': 'ERA Nature Medicine Blog Card'
        }
    ],
    'era_nature_blog.png': [
        {
            'target_name': 'era_nature_blog.jpg',
            'target_ratio': 1.11,
            'description': 'ERA Nature Medicine Blog Card'
        }
    ],
    'health_agent.png': [
        {
            'target_name': 'health_agent.jpg',
            'target_ratio': 0.77,
            'description': 'Personal Health Agent Paper Preview'
        }
    ],
    'hear_disease_blog.png': [
        {
            'target_name': 'hear_disease_blog.jpg',
            'target_ratio': 1.11,
            'description': 'HeAR Cough Disease Detection Blog Card'
        }
    ],
    'hear_model_card.png': [
        {
            'target_name': 'hear_model_card.jpg',
            'target_ratio': 1.11,
            'description': 'HeAR Model Card Developer Docs Card'
        }
    ],
    'insulin_wearables_blog.png': [
        {
            'target_name': 'insulin_wearables_blog.jpg',
            'target_ratio': 1.11,
            'description': 'Insulin Resistance Wearables Blog Card'
        }
    ],
    'lsm1.png': [
        {
            'target_name': 'lsm1.jpg',
            'target_ratio': 0.77,
            'description': 'Scaling Wearable Foundation Models Paper Preview'
        }
    ],
    'lsm1_blog.png': [
        {
            'target_name': 'lsm1_blog.jpg',
            'target_ratio': 1.11,
            'description': 'Scaling Wearable Foundation Models Blog Card'
        }
    ],
    'lsm2.png': [
        {
            'target_name': 'lsm2.jpg',
            'target_ratio': 0.77,
            'description': 'LSM-2 Paper Preview'
        }
    ],
    'lsm2_blog.png': [
        {
            'target_name': 'lsm2_blog.jpg',
            'target_ratio': 1.11,
            'description': 'LSM-2 Research Blog Card'
        }
    ],
    'sensorlm.png': [
        {
            'target_name': 'sensorlm.jpg',
            'target_ratio': 0.77,
            'description': 'SensorLM Paper Preview'
        }
    ],
    'sensorlm_blog.png': [
        {
            'target_name': 'sensorlm_blog.jpg',
            'target_ratio': 1.11,
            'description': 'SensorLM Research Blog Card'
        }
    ],
    'probabilistic_reasoning.png': [
        {
            'target_name': 'probabilistic_reasoning.jpg',
            'target_ratio': 0.77,
            'description': 'Probabilistic Reasoning Paper Preview'
        }
    ],
    'frill_speech_blog.png': [
        {
            'target_name': 'frill_speech_blog.jpg',
            'target_ratio': 1.11,
            'description': 'FRILL On-Device Speech Blog Card'
        }
    ],
    'nest_hub_sleep_blog.png': [
        {
            'target_name': 'nest_hub_sleep_blog.jpg',
            'target_ratio': 1.11,
            'description': 'Nest Hub Sleep Sensing Blog Card'
        }
    ],
    'nest_hub_contactless_blog.png': [
        {
            'target_name': 'nest_hub_contactless_blog.jpg',
            'target_ratio': 1.11,
            'description': 'Nest Hub Contactless Sleep Blog Card'
        }
    ],
    'nest_hub_enhanced_blog.png': [
        {
            'target_name': 'nest_hub_enhanced_blog.jpg',
            'target_ratio': 1.11,
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
            'target_ratio': 1.77,
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
    ],
    'ginger_beer.png': [
        {
            'target_name': 'ginger_beer.jpg',
            'target_ratio': 1.33,
            'description': 'Fermentation Ginger Beer Project Card'
        }
    ]
}


def load_crop_cache():
  """Loads cropped coordinate cache if it exists."""
  if os.path.exists(CROP_CACHE_FILE):
    try:
      with open(CROP_CACHE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)
    except Exception as e:
      logger.warning('Failed to load crop cache: %s', e)
  return {}


def save_crop_cache(cache):
  """Saves crop coordinate cache to file."""
  os.makedirs(os.path.dirname(CROP_CACHE_FILE), exist_ok=True)
  try:
    with open(CROP_CACHE_FILE, 'w', encoding='utf-8') as f:
      json.dump(cache, f, indent=2)
  except Exception as e:
    logger.warning('Failed to save crop cache: %s', e)


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


class ImageCropApp:
  """Tkinter GUI application for aspect-ratio locked cropping."""

  def __init__(self, root):
    self.root = root
    self.root.title("Portfolio Asset Crop Tool")
    self.root.geometry("1100x750")

    # App state
    self.items = []
    self.current_idx = 0

    # Crop rectangle state (in canvas coords)
    self.crop_x1 = 50
    self.crop_y1 = 50
    self.crop_x2 = 250
    self.crop_y2 = 250

    # Drag state
    self.drag_start_x = 0
    self.drag_start_y = 0
    self.dragging = False
    self.active_handle = None

    # Current loaded image details
    self.pil_img = None
    self.display_scale = 1.0
    self.canvas_w = 800
    self.canvas_h = 600

    self.find_crop_targets()
    self.setup_ui()
    self.load_current_item()

  def find_crop_targets(self):
    """Parses index.html to discover all active site images and sort by deviation."""
    from bs4 import BeautifulSoup
    index_path = os.path.join(BASE_DIR, 'index.html')
    if not os.path.exists(index_path):
      logger.error('index.html not found at %s', index_path)
      return

    try:
      with open(index_path, 'r', encoding='utf-8') as f:
        html = f.read()

      soup = BeautifulSoup(html, 'html.parser')
      img_tags = soup.find_all('img')
      seen_targets = set()

      for img in img_tags:
        src = img.get('src', '')
        if not src.startswith('image/'):
          continue

        img_filename = os.path.basename(src)
        if img_filename == 'jake.jpg' or 'logo' in img_filename:
          continue

        if img_filename in seen_targets:
          continue
        seen_targets.add(img_filename)

        target_ratio = 1.33
        description = "Project Card Image"

        prev_h4 = img.find_previous('h4')
        if prev_h4:
          h4_text = prev_h4.text.lower()
          if 'paper' in h4_text or 'publication' in h4_text:
            target_ratio = 0.77
            description = "Academic Paper Cover"
          elif 'blog' in h4_text:
            target_ratio = 1.11
            description = "Google Blog Banner"
          elif 'presentation' in h4_text or 'slide' in h4_text:
            target_ratio = 1.77
            description = "Presentation Slides"
          elif 'patent' in h4_text:
            target_ratio = 0.77
            description = "Patent Document Cover"
          else:
            target_ratio = 1.33
            description = f"Project Card ({prev_h4.text})"

        target_file_path = os.path.join(TARGET_DIR, img_filename)
        if os.path.exists(target_file_path):
          try:
            with Image.open(target_file_path) as cropped_img:
              cw, ch = cropped_img.size
              cropped_ratio = cw / ch
              cropped_deviation = abs(cropped_ratio - target_ratio) / target_ratio
              if cropped_deviation <= 0.15:
                continue
          except Exception as e:
            logger.warning('Could not read cropped %s size: %s',
                           target_file_path, e)

        # Locate original source file
        src_path = None
        base_no_ext = os.path.splitext(img_filename)[0]
        for d in SEARCH_DIRS:
          for ext in ('.png', '.jpg', '.jpeg', '.webp'):
            test_path = os.path.join(d, f"{base_no_ext}{ext}")
            if os.path.exists(test_path):
              src_path = test_path
              break
          if src_path:
            break

        if not src_path:
          test_path = os.path.join(TARGET_DIR, img_filename)
          if os.path.exists(test_path):
            src_path = test_path

        if src_path:
          deviation = 0.0
          try:
            with Image.open(src_path) as p_img:
              w, h = p_img.size
              actual_ratio = w / h
              deviation = abs(actual_ratio - target_ratio) / target_ratio
          except Exception as e:
            logger.warning('Could not read %s size: %s', src_path, e)

          self.items.append({
              'src_path': src_path,
              'filename': os.path.basename(src_path),
              'target_name': img_filename,
              'target_ratio': target_ratio,
              'description': description,
              'deviation': deviation
          })

    except Exception as e:
      logger.error('Failed parsing index.html: %s', e)

    self.items.sort(key=lambda x: x['deviation'], reverse=True)
    logger.info('Found %d active site crop targets, sorted by severity.',
                len(self.items))

  def setup_ui(self):
    """Sets up the Tkinter frames, canvas, and control buttons."""
    import tkinter as tk
    from tkinter import ttk

    self.paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
    self.paned.pack(fill=tk.BOTH, expand=True)

    self.left_frame = ttk.Frame(self.paned, padding=10)
    self.paned.add(self.left_frame, weight=3)

    self.canvas = tk.Canvas(
        self.left_frame,
        width=self.canvas_w,
        height=self.canvas_h,
        bg="#1e1e1e",
        highlightthickness=0
    )
    self.canvas.pack(fill=tk.BOTH, expand=True)

    self.canvas.bind("<ButtonPress-1>", self.on_button_press)
    self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
    self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    self.right_frame = ttk.Frame(self.paned, padding=10, width=280)
    self.paned.add(self.right_frame, weight=1)

    self.lbl_index = ttk.Label(self.right_frame, font=("Arial", 12, "bold"))
    self.lbl_index.pack(anchor=tk.W, pady=5)

    self.lbl_desc = ttk.Label(self.right_frame, wraplength=250,
                              font=("Arial", 10, "italic"))
    self.lbl_desc.pack(anchor=tk.W, pady=5)

    self.lbl_ratio = ttk.Label(self.right_frame, font=("Arial", 10))
    self.lbl_ratio.pack(anchor=tk.W, pady=5)

    ttk.Label(self.right_frame, text="Crop Box Size:").pack(anchor=tk.W, pady=10)
    self.slider_scale = ttk.Scale(self.right_frame, from_=0.1, to=1.0,
                                  orient=tk.HORIZONTAL,
                                  command=self.on_slider_change)
    self.slider_scale.pack(fill=tk.X, pady=5)
    self.slider_scale.set(0.5)

    self.var_lock_ratio = tk.BooleanVar(value=True)
    self.chk_lock_ratio = ttk.Checkbutton(self.right_frame,
                                          text="Lock Target Aspect Ratio",
                                          variable=self.var_lock_ratio,
                                          command=self.on_lock_ratio_toggle)
    self.chk_lock_ratio.pack(anchor=tk.W, pady=10)

    self.btn_crop = ttk.Button(self.right_frame, text="Crop & Save JPEG",
                               command=self.crop_and_save)
    self.btn_crop.pack(fill=tk.X, pady=15)

    self.btn_prev = ttk.Button(self.right_frame, text="<< Previous Item",
                               command=self.prev_item)
    self.btn_prev.pack(fill=tk.X, pady=5)

    self.btn_next = ttk.Button(self.right_frame, text="Next Item >>",
                               command=self.next_item)
    self.btn_next.pack(fill=tk.X, pady=5)

  def load_current_item(self):
    """Loads the current active image and sets up the crop overlay."""
    if not self.items:
      self.lbl_index.config(text="No crop targets found.")
      return

    item = self.items[self.current_idx]
    self.lbl_index.config(
        text=f"Item {self.current_idx + 1} of {len(self.items)}"
    )
    self.lbl_desc.config(
        text=f"Source: {item['filename']}\nTarget: {item['target_name']}\n{item['description']}"
    )
    self.lbl_ratio.config(
        text=f"Target Aspect Ratio: {item['target_ratio']}\nAspect Deviation: {item['deviation']:.1%}"
    )

    try:
      self.pil_img = Image.open(item['src_path'])
      self.slider_scale.set(0.5)

      cache = load_crop_cache()
      if item['target_name'] in cache:
        self.var_lock_ratio.set(
            cache[item['target_name']].get('lock_ratio', True)
        )
      else:
        self.var_lock_ratio.set(True)

      self.redraw_canvas()
    except Exception as e:
      messagebox.showerror("Error Loading Image", f"Could not open image: {e}")

  def redraw_canvas(self):
    """Draws scaled image and dotted aspect-locked crop selector overlay."""
    from PIL import ImageTk
    if not self.pil_img:
      return

    img_w, img_h = self.pil_img.size
    scale_w = self.canvas_w / img_w
    scale_h = self.canvas_h / img_h
    self.display_scale = min(scale_w, scale_h, 1.0)

    disp_w = int(img_w * self.display_scale)
    disp_h = int(img_h * self.display_scale)

    preview_img = self.pil_img.resize((disp_w, disp_h),
                                      Image.Resampling.BILINEAR)
    self.tk_img = ImageTk.PhotoImage(preview_img)

    self.canvas.delete("all")
    self.img_offset_x = (self.canvas_w - disp_w) // 2
    self.img_offset_y = (self.canvas_h - disp_h) // 2
    self.canvas.create_image(self.img_offset_x, self.img_offset_y,
                             anchor=tk.NW, image=self.tk_img)

    self.update_crop_box_size()
    self.draw_crop_overlay()

  def update_crop_box_size(self):
    """Calculates crop selector box dimensions from cache or defaults centered."""
    if not self.items:
      return
    item = self.items[self.current_idx]
    target_ratio = item['target_ratio']

    img_w, img_h = self.pil_img.size
    disp_w = int(img_w * self.display_scale)
    disp_h = int(img_h * self.display_scale)

    cache = load_crop_cache()
    if item['target_name'] in cache:
      c = cache[item['target_name']]
      self.crop_x1 = self.img_offset_x + int(c['x1_pct'] * disp_w)
      self.crop_y1 = self.img_offset_y + int(c['y1_pct'] * disp_h)
      self.crop_x2 = self.img_offset_x + int(c['x2_pct'] * disp_w)
      self.crop_y2 = self.img_offset_y + int(c['y2_pct'] * disp_h)
    else:
      max_box_w = disp_w
      max_box_h = int(disp_w / target_ratio)
      if max_box_h > disp_h:
        max_box_h = disp_h
        max_box_w = int(disp_h * target_ratio)

      slider_val = self.slider_scale.get()
      box_w = int(max_box_w * slider_val)
      box_h = int(max_box_h * slider_val)

      cx = self.img_offset_x + (disp_w - box_w) // 2
      cy = self.img_offset_y + (disp_h - box_h) // 2

      self.crop_x1 = cx
      self.crop_y1 = cy
      self.crop_x2 = cx + box_w
      self.crop_y2 = cy + box_h

  def draw_crop_overlay(self):
    """Draws dashed selection box and darkened margins on canvas."""
    self.canvas.delete("overlay")

    self.canvas.create_rectangle(
        self.img_offset_x, self.img_offset_y,
        self.img_offset_x + int(self.pil_img.size[0] * self.display_scale),
        self.crop_y1,
        fill="black", stipple="gray50", width=0, tags="overlay"
    )
    self.canvas.create_rectangle(
        self.img_offset_x, self.crop_y2,
        self.img_offset_x + int(self.pil_img.size[0] * self.display_scale),
        self.img_offset_y + int(self.pil_img.size[1] * self.display_scale),
        fill="black", stipple="gray50", width=0, tags="overlay"
    )
    self.canvas.create_rectangle(
        self.img_offset_x, self.crop_y1,
        self.crop_x1, self.crop_y2,
        fill="black", stipple="gray50", width=0, tags="overlay"
    )
    self.canvas.create_rectangle(
        self.crop_x2, self.crop_y1,
        self.img_offset_x + int(self.pil_img.size[0] * self.display_scale),
        self.crop_y2,
        fill="black", stipple="gray50", width=0, tags="overlay"
    )

    self.canvas.create_rectangle(
        self.crop_x1, self.crop_y1,
        self.crop_x2, self.crop_y2,
        outline="white", width=2, dash=(4, 4), tags="overlay"
    )

    handle_size = 5
    for hx, hy in [(self.crop_x1, self.crop_y1), (self.crop_x2, self.crop_y1),
                   (self.crop_x1, self.crop_y2), (self.crop_x2, self.crop_y2)]:
      self.canvas.create_rectangle(
          hx - handle_size, hy - handle_size,
          hx + handle_size, hy + handle_size,
          fill="white", outline="blue", tags="overlay"
      )

  def on_lock_ratio_toggle(self):
    """Enforces target aspect ratio immediately if toggled on."""
    if self.var_lock_ratio.get():
      self.update_crop_box_size()
      self.draw_crop_overlay()

  def on_slider_change(self, _):
    """Handles crop box scaling updates."""
    if not self.pil_img or not hasattr(self, 'img_offset_x'):
      return
    self.update_crop_box_size()
    self.draw_crop_overlay()

  def on_button_press(self, event):
    """Detects if click is near edge/corner handles or inside the crop box."""
    x, y = event.x, event.y
    tol = 12

    if abs(x - self.crop_x1) <= tol and abs(y - self.crop_y1) <= tol:
      self.active_handle = 'tl'
    elif abs(x - self.crop_x2) <= tol and abs(y - self.crop_y1) <= tol:
      self.active_handle = 'tr'
    elif abs(x - self.crop_x1) <= tol and abs(y - self.crop_y2) <= tol:
      self.active_handle = 'bl'
    elif abs(x - self.crop_x2) <= tol and abs(y - self.crop_y2) <= tol:
      self.active_handle = 'br'
    elif abs(x - self.crop_x1) <= tol and self.crop_y1 <= y <= self.crop_y2:
      self.active_handle = 'l'
    elif abs(x - self.crop_x2) <= tol and self.crop_y1 <= y <= self.crop_y2:
      self.active_handle = 'r'
    elif abs(y - self.crop_y1) <= tol and self.crop_x1 <= x <= self.crop_x2:
      self.active_handle = 't'
    elif abs(y - self.crop_y2) <= tol and self.crop_x1 <= x <= self.crop_x2:
      self.active_handle = 'b'
    elif self.crop_x1 < x < self.crop_x2 and self.crop_y1 < y < self.crop_y2:
      self.active_handle = 'move'
    else:
      self.active_handle = None

    if self.active_handle:
      self.dragging = True
      self.drag_start_x = x
      self.drag_start_y = y

  def on_mouse_drag(self, event):
    """Resizes or moves the crop box based on dragged edge/handle."""
    if not self.dragging:
      return

    dx = event.x - self.drag_start_x
    dy = event.y - self.drag_start_y

    self.drag_start_x = event.x
    self.drag_start_y = event.y

    img_w_scale = int(self.pil_img.size[0] * self.display_scale)
    img_h_scale = int(self.pil_img.size[1] * self.display_scale)
    img_x2 = self.img_offset_x + img_w_scale
    img_y2 = self.img_offset_y + img_h_scale

    x1, y1, x2, y2 = self.crop_x1, self.crop_y1, self.crop_x2, self.crop_y2

    if self.active_handle == 'move':
      if x1 + dx >= self.img_offset_x and x2 + dx <= img_x2:
        x1 += dx
        x2 += dx
      if y1 + dy >= self.img_offset_y and y2 + dy <= img_y2:
        y1 += dy
        y2 += dy
    else:
      if 'l' in self.active_handle or self.active_handle in ('tl', 'bl'):
        if x1 + dx < x2 - 20 and x1 + dx >= self.img_offset_x:
          x1 += dx
      if 'r' in self.active_handle or self.active_handle in ('tr', 'br'):
        if x2 + dx > x1 + 20 and x2 + dx <= img_x2:
          x2 += dx
      if 't' in self.active_handle or self.active_handle in ('tl', 'tr'):
        if y1 + dy < y2 - 20 and y1 + dy >= self.img_offset_y:
          y1 += dy
      if 'b' in self.active_handle or self.active_handle in ('bl', 'br'):
        if y2 + dy > y1 + 20 and y2 + dy <= img_y2:
          y2 += dy

      if self.var_lock_ratio.get():
        item = self.items[self.current_idx]
        target_ratio = item['target_ratio']
        w = x2 - x1
        h = int(w / target_ratio)
        if self.active_handle in ('t', 'tl', 'tr'):
          y1 = y2 - h
          if y1 < self.img_offset_y:
            y1 = self.img_offset_y
            x2 = x1 + int((y2 - y1) * target_ratio)
        else:
          y2 = y1 + h
          if y2 > img_y2:
            y2 = img_y2
            x2 = x1 + int((y2 - y1) * target_ratio)

    self.crop_x1, self.crop_y1, self.crop_x2, self.crop_y2 = x1, y1, x2, y2
    self.draw_crop_overlay()

  def on_button_release(self, _):
    """Stops crop selection drag operation."""
    self.dragging = False

  def crop_and_save(self):
    """Crops original PIL image, resizes, and saves as optimized JPEG."""
    if not self.pil_img:
      return

    item = self.items[self.current_idx]

    orig_x1 = int((self.crop_x1 - self.img_offset_x) / self.display_scale)
    orig_y1 = int((self.crop_y1 - self.img_offset_y) / self.display_scale)
    orig_x2 = int((self.crop_x2 - self.img_offset_x) / self.display_scale)
    orig_y2 = int((self.crop_y2 - self.img_offset_y) / self.display_scale)

    orig_x1 = max(0, orig_x1)
    orig_y1 = max(0, orig_y1)
    orig_x2 = min(self.pil_img.size[0], orig_x2)
    orig_y2 = min(self.pil_img.size[1], orig_y2)

    try:
      cropped_img = self.pil_img.crop((orig_x1, orig_y1, orig_x2, orig_y2))

      w, h = cropped_img.size
      if w > MAX_WIDTH:
        new_w = MAX_WIDTH
        new_h = int(h * (MAX_WIDTH / w))
        cropped_img = cropped_img.resize((new_w, new_h),
                                         Image.Resampling.LANCZOS)

      if cropped_img.mode in ('RGBA', 'LA'):
        cropped_img = cropped_img.convert('RGB')

      target_path = os.path.join(TARGET_DIR, item['target_name'])
      cropped_img.save(target_path, 'JPEG', optimize=True, quality=JPEG_QUALITY)

      img_w_scale = int(self.pil_img.size[0] * self.display_scale)
      img_h_scale = int(self.pil_img.size[1] * self.display_scale)

      cache = load_crop_cache()
      cache[item['target_name']] = {
          'x1_pct': (self.crop_x1 - self.img_offset_x) / img_w_scale,
          'y1_pct': (self.crop_y1 - self.img_offset_y) / img_h_scale,
          'x2_pct': (self.crop_x2 - self.img_offset_x) / img_w_scale,
          'y2_pct': (self.crop_y2 - self.img_offset_y) / img_h_scale,
          'lock_ratio': self.var_lock_ratio.get()
      }
      save_crop_cache(cache)

      msg = (f"Successfully cropped and saved:\n{item['target_name']}\n"
             f"Size: {cropped_img.size[0]}x{cropped_img.size[1]} "
             f"({os.path.getsize(target_path) / 1024:.1f} KB)")
      logger.info(msg)
      messagebox.showinfo("Success", msg)

    except Exception as e:
      messagebox.showerror("Crop Error", f"Failed to crop and save image: {e}")

  def prev_item(self):
    """Navigates to previous image target."""
    if self.current_idx > 0:
      self.current_idx -= 1
      self.load_current_item()

  def next_item(self):
    """Navigates to next image target."""
    if self.current_idx < len(self.items) - 1:
      self.current_idx += 1
      self.load_current_item()


def main():
  import tkinter as tk
  parser = argparse.ArgumentParser(description="Image import and crop utility.")
  parser.add_argument("action", choices=["import", "crop"], nargs="?",
                      default="import",
                      help="Action to perform: import/compress or crop GUI.")
  args = parser.parse_args()

  if args.action == "import":
    process_images()
  elif args.action == "crop":
    root = tk.Tk()
    ImageCropApp(root)
    root.mainloop()


if __name__ == "__main__":
  main()
