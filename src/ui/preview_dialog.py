import ttkbootstrap as tb
from ttkbootstrap.constants import *
import time

from PIL import Image, ImageTk, UnidentifiedImageError

PREVIEW_DEFAULT_SIZE = (640, 480)
CANVAS_BG_COLOR = "gray20"

class PreviewDialog(tb.Toplevel):
    """A dialog window to preview an image with zoom and fit-to-window functionality."""
    def __init__(self, parent, pil_image: Image.Image, title: str | None =None):
        super().__init__(parent)
        self.title(title or "Image Preview")
        self.geometry(f"{PREVIEW_DEFAULT_SIZE[0]}x{PREVIEW_DEFAULT_SIZE[1]}")

        self.original = pil_image.copy()  # Keep original for zooming
        self.zoom = 1.0
        self.current_size = self.original.size
        self._preview_images = []  # Holds current image reference

        # --- Zoom caching values
        self._zoom_cache = {} # zoom level: PIL Image
        self._max_cache_size = 10 # Limit the cache size
        self._fast_zoom_threshold = 2.0 # Zoom after this threshold is simplified
        self._last_zoom_time = 0
        self._zoom_debounce_ms = 50 # ignore zoom operation if it is within the lower time period
        # ---

        frame = tb.Frame(self)
        frame.pack(fill=BOTH, expand=True)
        # Creating the scrollbars
        vbar = tb.Scrollbar(frame, orient=VERTICAL)
        hbar = tb.Scrollbar(frame, orient=HORIZONTAL)
        # Create canvas
        self.canvas = tb.Canvas(frame, bg=CANVAS_BG_COLOR, 
                    yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        # Configure scrollbars to control the canvas
        vbar.config(command=self.canvas.yview)
        hbar.config(command=self.canvas.xview)
        self.label = tb.Label(self, 
                    text="A - full size, F - fit to window, +/- - zoom, Ctrl+Wheel - zoom", anchor="center")
        self.label.pack(side=BOTTOM, fill=X)

        # Place the scrollbars and canvas in the frame
        vbar.pack(side=RIGHT, fill=Y)
        hbar.pack(side=BOTTOM, fill=X)
        self.canvas.pack(fill=BOTH, expand=True)

        # --- Event bindings section
        # Event bindings for keyboard controls
        self.bind('<Escape>', lambda e: self.destroy())
        self.bind('<KeyPress>', self._shortcuts_handler)
        self.bind('<plus>', lambda e: self.zoom_img(factor=1.1))
        self.bind('<minus>', lambda e: self.zoom_img(factor=0.9))
        # Event bindings for mouse controls
        self.canvas.bind('<Control-MouseWheel>', self._on_mousewheel) # Windows/MacOs
        self.canvas.bind('<Control-Button-4>', self._on_mousewheel) # Linux scroll up
        self.canvas.bind('<Control-Button-5>', self._on_mousewheel) # Linux scroll down

        self.fit_to_window()
    #-----------------------Image display and manipulation------------------------------------------------------
    def fit_to_window(self):
        """Resize the image to fit within the current window size while maintaining aspect ratio."""
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 1 or height <= 1:  # Initial size might be 1x1, use default in that case
            width, height = PREVIEW_DEFAULT_SIZE
        
        # Calculate scale factor
        orig_w, orig_h = self.original.size
        scale = min(width/orig_w, height/orig_h) # current zoom level

        # Zoom level and current size update
        self.zoom = scale
        self.current_size = (int(orig_w*scale), int(orig_h*scale))

        # Create cache key
        zoom_key = round(self.zoom, 2)

        # Check the cache
        if zoom_key in self._zoom_cache:
            cached_img = self._zoom_cache[zoom_key]
            self._update_canvas(cached_img)
            return
        # Not cached, calculate value
        resized = self.original.resize(self.current_size, Image.Resampling.LANCZOS)
        self._zoom_cache[zoom_key] = resized

        self._update_canvas(resized)
    
    def actual_size(self):
        """A handler to display the image at its actual size (100% zoom)."""
        self.current_size = self.original.size # update current size
        self.zoom = 1.0 # reset zoom
        self._update_canvas(self.original.copy())

    def zoom_img(self, factor: float):
        """ A handler for zooming the image in or out by the given factor."""
        # Restrict zoom operations per period quantity
        current_time = time.time() * 1000
        if current_time - self._last_zoom_time < self._zoom_debounce_ms:
            return
        self._last_zoom_time = current_time

        self.zoom *= factor
        zoom_key = round(self.zoom, 2)

        # Check the cache
        if zoom_key in self._zoom_cache:
            cached_img = self._zoom_cache[zoom_key]
            self._update_canvas(cached_img)
            return

        # New size calculation
        original_w, original_h = self.original.size
        # A slightly more condensed version
        # new_size = tuple(int(dim * self.zoom) for dim in self.original.size)
        new_size = (int(original_w * self.zoom), int(original_h * self.zoom))

        # Use faster zoom mechanism for bigger zoom values
        if self.zoom > self._fast_zoom_threshold:
            resampling = Image.Resampling.BILINEAR
        else:
            resampling = Image.Resampling.LANCZOS

        resized_img = self.original.resize(new_size, resampling)

        if len(self._zoom_cache) >= self._max_cache_size:
            # remove the oldest cached entry
            oldest_entry = next(iter(self._zoom_cache))
            del(self._zoom_cache[oldest_entry])
        self._zoom_cache[zoom_key]  = resized_img

        self._update_canvas(resized_img)

    def _clear_zoom_cache(self):
        """ Free memory by clearing cache """
        try:
            self._zoom_cache.clear()
        except AttributeError:
            # Can be ignored since the cache is not yet initialized
            pass

    def _update_canvas(self, pil_image: Image.Image):
        """ A helper method to update the canvas with the given PIL image."""
        tk_img = ImageTk.PhotoImage(pil_image)

        # Place the image in the center of the canvas
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw <= 1 or ch <= 1:  # Initial size might be 1x1, use image size in that case
            self.after(100, lambda: self._update_canvas(pil_image))  # Try again after a short delay
            return

        self.canvas.delete("all")
        self.canvas.create_image(cw//2, ch//2, image=tk_img, anchor="center")
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self._preview_images = [tk_img]  # Having only one image in preview to prevent memory leaks

    def _on_mousewheel(self, event):
        """Handle mouse wheel zoom"""
        if event.state & 0x0004:
            if event.num == 4 or event.delta > 0:
                self.zoom_img(1.1)
            elif event.num == 5 or event.delta < 0:
                self.zoom_img(0.9)
    
    def _shortcuts_handler(self, event):
        keycode_map = {
            70: self.fit_to_window,
            65: self.actual_size
        }
        if event.keycode in keycode_map:
            keycode_map[event.keycode]()
