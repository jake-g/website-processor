"""Interactive image cropper tool for portfolio assets.

Allows user to crop uploaded screenshots/photos to their exact target aspect
ratios before importing and compressing them.
"""

import logging
import os
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk
from PIL import Image
from PIL import ImageTk

# Import metadata and directories from import_images
from processing.import_images import IMAGE_METADATA
from processing.import_images import JPEG_QUALITY
from processing.import_images import MAX_WIDTH
from processing.import_images import TARGET_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Search directories for original images
SEARCH_DIRS = [
    '/Users/jakegarrison/Downloads/projects/website/new images',
    '/Users/jakegarrison/Downloads/projects/website/new images/orig images'
]


class ImageCropApp:
  """Tkinter GUI application for aspect-ratio locked cropping."""

  def __init__(self, root: tk.Tk):
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

    # Current loaded image details
    self.pil_img = None  # Original PIL Image
    self.display_scale = 1.0  # Scale from original PIL size to canvas size
    self.canvas_w = 800
    self.canvas_h = 600

    self.find_crop_targets()
    self.setup_ui()
    self.load_current_item()

  def find_crop_targets(self):
    """Finds all defined target images in the search directories."""
    for filename, targets in IMAGE_METADATA.items():
      found_path = None
      for d in SEARCH_DIRS:
        test_path = os.path.join(d, filename)
        if os.path.exists(test_path):
          found_path = test_path
          break

      if found_path:
        for target in targets:
          self.items.append({
              'src_path': found_path,
              'filename': filename,
              'target_name': target['target_name'],
              'target_ratio': target['target_ratio'],
              'description': target['description']
          })

    logger.info('Found %d crop targets.', len(self.items))

  def setup_ui(self):
    """Sets up the Tkinter frames, canvas, and control buttons."""
    # Main Paned Window
    self.paned = ttk.Panedwindow(self.root, orient=tk.HORIZONTAL)
    self.paned.pack(fill=tk.BOTH, expand=True)

    # Left Panel: Canvas
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

    # Mouse bindings for dragging crop area
    self.canvas.bind("<ButtonPress-1>", self.on_button_press)
    self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
    self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

    # Right Panel: Controls
    self.right_frame = ttk.Frame(self.paned, padding=10, width=280)
    self.paned.add(self.right_frame, weight=1)

    # Item info labels
    self.lbl_index = ttk.Label(self.right_frame, font=("Arial", 12, "bold"))
    self.lbl_index.pack(anchor=tk.W, pady=5)

    self.lbl_desc = ttk.Label(
        self.right_frame,
        wraplength=250,
        font=("Arial", 10, "italic")
    )
    self.lbl_desc.pack(anchor=tk.W, pady=5)

    self.lbl_ratio = ttk.Label(self.right_frame, font=("Arial", 10))
    self.lbl_ratio.pack(anchor=tk.W, pady=5)

    # Scale slider to resize crop box
    ttk.Label(self.right_frame, text="Crop Box Size:").pack(anchor=tk.W, pady=10)
    self.slider_scale = ttk.Scale(
        self.right_frame,
        from_=0.1,
        to=1.0,
        orient=tk.HORIZONTAL,
        command=self.on_slider_change
    )
    self.slider_scale.pack(fill=tk.X, pady=5)
    self.slider_scale.set(0.5)

    # Navigation & action buttons
    self.btn_crop = ttk.Button(
        self.right_frame,
        text="Crop & Save JPEG",
        command=self.crop_and_save
    )
    self.btn_crop.pack(fill=tk.X, pady=15)

    self.btn_prev = ttk.Button(
        self.right_frame,
        text="<< Previous Item",
        command=self.prev_item
    )
    self.btn_prev.pack(fill=tk.X, pady=5)

    self.btn_next = ttk.Button(
        self.right_frame,
        text="Next Item >>",
        command=self.next_item
    )
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
    self.lbl_ratio.config(text=f"Target Aspect Ratio: {item['target_ratio']}")

    # Load PIL image
    try:
      self.pil_img = Image.open(item['src_path'])
      self.slider_scale.set(0.5)
      self.redraw_canvas()
    except Exception as e:
      messagebox.showerror("Error Loading Image", f"Could not open image: {e}")

  def redraw_canvas(self):
    """Draws scaled image and dotted aspect-locked crop selector overlay."""
    if not self.pil_img:
      return

    img_w, img_h = self.pil_img.size

    # Fit image within the canvas bounds
    scale_w = self.canvas_w / img_w
    scale_h = self.canvas_h / img_h
    self.display_scale = min(scale_w, scale_h, 1.0)

    disp_w = int(img_w * self.display_scale)
    disp_h = int(img_h * self.display_scale)

    # Resize preview
    preview_img = self.pil_img.resize((disp_w, disp_h), Image.Resampling.BILINEAR)
    self.tk_img = ImageTk.PhotoImage(preview_img)

    # Clear and draw image centered
    self.canvas.delete("all")
    self.img_offset_x = (self.canvas_w - disp_w) // 2
    self.img_offset_y = (self.canvas_h - disp_h) // 2
    self.canvas.create_image(
        self.img_offset_x,
        self.img_offset_y,
        anchor=tk.NW,
        image=self.tk_img
    )

    # Update crop overlay box coordinates
    self.update_crop_box_size()
    self.draw_crop_overlay()

  def update_crop_box_size(self):
    """Calculates crop selector box dimensions based on scale slider and ratio."""
    if not self.items:
      return
    item = self.items[self.current_idx]
    target_ratio = item['target_ratio']

    img_w, img_h = self.pil_img.size
    disp_w = int(img_w * self.display_scale)
    disp_h = int(img_h * self.display_scale)

    # Determine maximum bounding box size on canvas matching aspect ratio
    max_box_w = disp_w
    max_box_h = int(disp_w / target_ratio)
    if max_box_h > disp_h:
      max_box_h = disp_h
      max_box_w = int(disp_h * target_ratio)

    # Apply size slider percentage
    slider_val = self.slider_scale.get()
    box_w = int(max_box_w * slider_val)
    box_h = int(max_box_h * slider_val)

    # Center crop box relative to image boundaries on canvas
    cx = self.img_offset_x + (disp_w - box_w) // 2
    cy = self.img_offset_y + (disp_h - box_h) // 2

    self.crop_x1 = cx
    self.crop_y1 = cy
    self.crop_x2 = cx + box_w
    self.crop_y2 = cy + box_h

  def draw_crop_overlay(self):
    """Draws dashed selection box and darkened margins on canvas."""
    self.canvas.delete("overlay")

    # Darken outside crop region
    # Top margin
    self.canvas.create_rectangle(
        self.img_offset_x, self.img_offset_y,
        self.img_offset_x + int(self.pil_img.size[0] * self.display_scale),
        self.crop_y1,
        fill="black", stipple="gray50", width=0, tags="overlay"
    )
    # Bottom margin
    self.canvas.create_rectangle(
        self.img_offset_x, self.crop_y2,
        self.img_offset_x + int(self.pil_img.size[0] * self.display_scale),
        self.img_offset_y + int(self.pil_img.size[1] * self.display_scale),
        fill="black", stipple="gray50", width=0, tags="overlay"
    )
    # Left margin
    self.canvas.create_rectangle(
        self.img_offset_x, self.crop_y1,
        self.crop_x1, self.crop_y2,
        fill="black", stipple="gray50", width=0, tags="overlay"
    )
    # Right margin
    self.canvas.create_rectangle(
        self.crop_x2, self.crop_y1,
        self.img_offset_x + int(self.pil_img.size[0] * self.display_scale),
        self.crop_y2,
        fill="black", stipple="gray50", width=0, tags="overlay"
    )

    # Dotted selection crop rectangle
    self.canvas.create_rectangle(
        self.crop_x1,
        self.crop_y1,
        self.crop_x2,
        self.crop_y2,
        outline="white",
        width=2,
        dash=(4, 4),
        tags="overlay"
    )

  def on_slider_change(self, _):
    """Handles crop box scaling updates."""
    if not self.pil_img or not hasattr(self, 'img_offset_x'):
      return
    # Move box to center and change size
    self.update_crop_box_size()
    self.draw_crop_overlay()

  def on_button_press(self, event):
    """Starts dragging of the crop box if mouse hits within selection bounds."""
    if (self.crop_x1 <= event.x <= self.crop_x2 and
        self.crop_y1 <= event.y <= self.crop_y2):
      self.dragging = True
      self.drag_start_x = event.x
      self.drag_start_y = event.y

  def on_mouse_drag(self, event):
    """Updates the position of the crop box inside image boundaries."""
    if not self.dragging:
      return

    dx = event.x - self.drag_start_x
    dy = event.y - self.drag_start_y

    img_w_scale = int(self.pil_img.size[0] * self.display_scale)
    img_h_scale = int(self.pil_img.size[1] * self.display_scale)

    new_x1 = self.crop_x1 + dx
    new_y1 = self.crop_y1 + dy
    new_x2 = self.crop_x2 + dx
    new_y2 = self.crop_y2 + dy

    # Constrain to display offset bounds
    if new_x1 >= self.img_offset_x and new_x2 <= self.img_offset_x + img_w_scale:
      self.crop_x1 = new_x1
      self.crop_x2 = new_x2
      self.drag_start_x = event.x

    if new_y1 >= self.img_offset_y and new_y2 <= self.img_offset_y + img_h_scale:
      self.crop_y1 = new_y1
      self.crop_y2 = new_y2
      self.drag_start_y = event.y

    self.draw_crop_overlay()

  def on_button_release(self, _):
    """Stops crop selection drag operation."""
    self.dragging = False

  def crop_and_save(self):
    """Crops original PIL image, resizes, and saves as optimized JPEG."""
    if not self.pil_img:
      return

    item = self.items[self.current_idx]

    # Convert canvas crop coordinates back to original PIL coordinates
    orig_x1 = int((self.crop_x1 - self.img_offset_x) / self.display_scale)
    orig_y1 = int((self.crop_y1 - self.img_offset_y) / self.display_scale)
    orig_x2 = int((self.crop_x2 - self.img_offset_x) / self.display_scale)
    orig_y2 = int((self.crop_y2 - self.img_offset_y) / self.display_scale)

    # Prevent out of bounds rounding errors
    orig_x1 = max(0, orig_x1)
    orig_y1 = max(0, orig_y1)
    orig_x2 = min(self.pil_img.size[0], orig_x2)
    orig_y2 = min(self.pil_img.size[1], orig_y2)

    try:
      # Crop original PIL image
      cropped_img = self.pil_img.crop((orig_x1, orig_y1, orig_x2, orig_y2))

      # Resize maintaining aspect ratio to MAX_WIDTH
      w, h = cropped_img.size
      if w > MAX_WIDTH:
        new_w = MAX_WIDTH
        new_h = int(h * (MAX_WIDTH / w))
        cropped_img = cropped_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

      # Convert RGBA to RGB
      if cropped_img.mode in ('RGBA', 'LA'):
        cropped_img = cropped_img.convert('RGB')

      target_path = os.path.join(TARGET_DIR, item['target_name'])
      cropped_img.save(target_path, 'JPEG', optimize=True, quality=JPEG_QUALITY)

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
  root = tk.Tk()
  app = ImageCropApp(root)
  root.mainloop()


if __name__ == "__main__":
  main()
