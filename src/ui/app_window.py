# build an app main window (drag&drop zone, add files, clear list, create PDF, menu bar, toolbar)
# show the images tree view/list
# Hook elements to actions

from pathlib import Path
from typing import List
import time

import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.tooltip import ToolTip
from tkinterdnd2 import DND_FILES, TkinterDnD
from loguru import logger

from PIL import Image, ImageTk, UnidentifiedImageError
# adding async thumbnails
import concurrent.futures
from threading import Lock
import queue
# project imports
from core.image_loader import add_images, add_images_lenient
from core.pdf_builder import build_pdf


# Constants
TITLE = "Image to PDF Converter"
THEME = "flatly"  # or "darkly", "cyborg", etc. (see https://ttkbootstrap.readthedocs.io/en/latest/themes/index.html)
DEFAULT_SIZE = (600, 800)
PREVIEW_DEFAULT_SIZE = (640, 480)
CANVAS_BG_COLOR = "gray20"
PREVIEW_TITLE_TEMPLATE = "Image Preview  - {index}/{total}"
THUMBNAIL_WORKERS = 4
THUMBNAIL_QUEUE_SIZE = 100

class ImageToPdfApp(TkinterDnD.Tk):
    """Main application window for the Image to PDF converter."""
    THUMB_MAX = 94  # Max size for thumbnails in the list
    def __init__(self):
        super().__init__() 
        style = tb.Style(theme=THEME)
        self.title(TITLE)
        self.geometry(f"{DEFAULT_SIZE[0]}x{DEFAULT_SIZE[1]}")

        # async thumbnails
        self._thumbnail_executor = concurrent.futures.ThreadPoolExecutor(
            max_workers = THUMBNAIL_WORKERS,
            thread_name_prefix = 'thumbnail'
        )
        self._thumbnail_lock = Lock()
        self._pending_thumbs = {} # row_id => Future
        self._shutdown_request = False

        self.loaded_images: List[Image.Image] = []
        self._thumb_refs: dict[str, ImageTk.PhotoImage] = {}

        # Create UI elements
        self.create_widgets()

    #------------- Widgets placement -------------------------------
    def create_widgets(self):
        # --- Top toolbar: file-level actions ---
        toolbar = tb.Frame(self)
        toolbar.pack(side=TOP, fill=X)
        
        # General buttons
        add_button = tb.Button(
            toolbar, 
            text="Add Images", 
            command=self.on_add_images
            )
        add_button.pack(side=LEFT, padx=10, pady=5)
        clear_button = tb.Button(
            toolbar, 
            text="Clear List", 
            command=self.on_clear_list
            )
        clear_button.pack(side=LEFT, padx=10, pady=5)
        create_button = tb.Button(
            toolbar,
            text="Create PDF", 
            command=self.on_create_pdf
            )
        create_button.pack(side=LEFT, padx=10, pady=5)
        # Button tooltips
        ToolTip(add_button, text = "Select images for pdf pages")
        ToolTip(clear_button, text = "Remove all images from the list")
        ToolTip(create_button, text = "Generate PDF")

        
        # --- Main area: tree + side panel ---
        main_area = tb.Frame(self)
        main_area.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # --- Right panel: selection-level actions ---
        side_panel = tb.Frame(main_area)
        side_panel.pack(side=RIGHT, fill=Y, padx=(5, 0))

        mv_up_btn = tb.Button(side_panel, text="↑", width=3, command=self.on_move_up)
        mv_up_btn.pack(pady=(10, 2))
        mv_dwn_btn = tb.Button(side_panel, text="↓", width=3, command=self.on_move_down)
        mv_dwn_btn.pack(pady=(10, 2))
        rt_btn = tb.Button(side_panel, text="↻", width=3, command=self.on_rotate)
        rt_btn.pack(pady=(10, 0))  
        rm_btn = tb.Button(side_panel, text="X", width=3, command=self.on_delete)
        rm_btn.pack(pady=(10, 0))  
        prv_btn = tb.Button(side_panel, text="🔍", width=3, command=self.on_preview)
        prv_btn.pack(pady=(10, 0))
        # Side button tooltips
        ToolTip(mv_up_btn, text = "Move page up")
        ToolTip(mv_dwn_btn, text = "Move page down")
        ToolTip(rt_btn, text = "Rotate page")
        ToolTip(rm_btn, text = "Remove page")
        ToolTip(prv_btn, text = "Preview page")

        # --- Treeview ---
        # style = ttk.Style()
        # style.configure("Treeview", rowheight=self.THUMB_MAX + 10)

        self.imgs_tree = ttk.Treeview(
            main_area,
            columns=("filename",),
            show="tree headings",
            height=12,
        )
        self.imgs_tree.heading("#0", text="")
        self.imgs_tree.column("#0", width=self.THUMB_MAX + 10, anchor="center", stretch=False)
        self.imgs_tree.heading("filename", text="Зображення")
        self.imgs_tree.column("filename", anchor="w", width=400)
        style = ttk.Style()
        style.configure("Treeview", rowheight=self.THUMB_MAX + 10)  # Add some padding for the thumbnail
        self.imgs_tree.pack(fill=BOTH, expand=True)

        try:
            self.imgs_tree.drop_target_register(DND_FILES)
            self.imgs_tree.dnd_bind('<<Drop>>', self.on_drop_files)
        except Exception as e:
            messagebox.showerror("Error", f"Drag-and-drop failure: {e}")
        
        # --- Status bar ---
        self.status = tb.Label(self, text="No images loaded.", anchor="w")
        self.status.pack(fill=X, side=BOTTOM, padx=5, pady=5)

        # --- Binding shortcuts ---
        self.bind('<Control-o>', lambda e: self.on_add_images())
        self.bind('<Control-s>', lambda e: self.on_create_pdf())
        self.bind('<Control-c>', lambda e: self.on_clear_list())
        self.bind('<Delete>', lambda e: self.on_delete())
        self.bind('<Control-Up>', lambda e: self.on_move_up())
        self.bind('<Control-Down>', lambda e: self.on_move_down())
        self.bind('<Control-r>', lambda e: self.on_rotate())
        self.bind('<Control-q>', lambda e: self.destroy())


    def destroy(self):
        """Clean shutdown of background threads"""
        self._shutdown_request = True

        # Cancel pending thumbnails
        with self._thumbnail_lock:
            for future in self._pending_thumbs.values():
                future.cancel()
            self._pending_thumbs.clear()

        self._thumbnail_executor.shutdown(wait=False, cancel_futures=True)

        super().destroy()


   
    #-----------------------Event Handlers------------------------------------------------------
    def on_add_images(self):
        """Open a file dialog to select images to add to list"""
        file_paths = filedialog.askopenfilenames(
            title="Select images",
            filetypes=[("Image Files", ['.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.tiff'])]
        )

        if not file_paths:
            return

        try:
            new_imgs = add_images(file_paths)
            self._add_images_to_list(file_paths, new_imgs)
        except UnidentifiedImageError as e:
            messagebox.showerror("Error", f"Corrupt image. One of the images cannot be opened: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load dropped images: {e}")
    
    def on_drop_files(self, event):
        """Handler for a drag and drop images"""
        dropped = event.data

        # Remove potential extra chars and split by spaces
        if dropped.startswith('{'):
            file_paths = []
            current = ""
            in_braces = False
            for char in dropped:
                if char == '{':
                    in_braces = True
                elif char == '}':
                    in_braces = False
                    if current:
                        file_paths.append(current)
                        current = ""
                elif in_braces:
                    current += char
        else:
            file_paths = dropped.split()

        if not file_paths:
            return
        try:
            new_imgs, _ = add_images_lenient(file_paths) 
            # TODO: think if the skipped are necessary for something except for logging
            self._add_images_to_list(file_paths, new_imgs)
        except UnidentifiedImageError as e:
            messagebox.showerror("Error", f"Corrupt image. One of the images cannot be opened: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load dropped images: {e}")

    def on_clear_list(self):
        """
        Clear the list of images and the corresponding thumbnails.
        Does not display a warning message if no images are loaded.
        """
        self.loaded_images.clear()
        for child in self.imgs_tree.get_children():
            self.imgs_tree.delete(child)
        self._thumb_refs.clear()
        self.status.config(text="No images loaded.")


    def on_create_pdf(self):
        """
        Create a PDF from the loaded images.

        If no images are loaded, show a warning message and return without doing anything else.
        Ask the user to select a save location and filename for the PDF.
        Attempt to generate the PDF using the `build_pdf` function from the `core.pdf_builder` module.
        If an error occurs during the PDF creation, show an error message and return.
        Otherwise, show an info message with the path to the created PDF.
        """
        if not self.loaded_images:
            messagebox.showwarning("No Images", "Please add some images before creating a PDF.")
            return
        out_path = filedialog.asksaveasfilename(
            title="Save PDF as",
            defaultextension=".pdf",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if not out_path:
            return  # User cancelled the dialog
        # Add pdf generation
        try:
            build_pdf(self.loaded_images, out_path)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to create PDF:\n{exc}")
            return
        messagebox.showinfo("PDF Created", f"PDF successfully created at:\n{out_path}")
        
    

    def on_move_up(self):
        """Move the selected image up in the list."""
        self._on_move_selected(-1)

    def on_move_down(self):
        """Move the selected image down in the list.s"""
        self._on_move_selected(1)
        
    def on_rotate(self):
        """
        Rotate the selected image clockwise by 90 degrees in place.

        Does not clear the selection after rotation.
        """
        selected = self.imgs_tree.selection()
        if not selected:
            return

        item = selected[0]
        children = self.imgs_tree.get_children()
        index = children.index(item)

        # Rotate the PIL image in place
        self.loaded_images[index] = self.loaded_images[index].rotate(
            -90,            # negative = clockwise
            expand=True     # adjusts canvas so nothing gets cropped
        )

        # Rebuild and update the thumbnail in the tree
        thumb = self.loaded_images[index].copy()
        thumb.thumbnail((self.THUMB_MAX, self.THUMB_MAX), Image.Resampling.LANCZOS)
        tk_thumb = ImageTk.PhotoImage(thumb)

        self.imgs_tree.item(item, image=tk_thumb)
        self._thumb_refs[item] = tk_thumb  # replace the old reference


    def on_delete(self):
        """
        Delete the selected image from the list.

        If no image is selected, displays a warning message and does nothing.

        Otherwise, removes the selected image from both the data list and the UI tree, and
        updates the status bar to reflect the new image count.
        """
        selected = self.imgs_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select an image to delete.")
            return

        item = selected[0]
        children = self.imgs_tree.get_children()
        index = children.index(item)

        # Remove from data and UI
        self.loaded_images.pop(index)
        self.imgs_tree.delete(item)
        
        # Clean up thumbnail reference
        if item in self._thumb_refs:
            del self._thumb_refs[item]
        
        self.status.config(text=f"{len(self.loaded_images)} image(s) loaded.")


    def on_preview(self):
        """Preview the selected image in a new window."""
        selected = self.imgs_tree.selection()
        if not selected:
            return
        
        item = selected[0]
        children = self.imgs_tree.get_children()
        index = children.index(item)
        pil_image = self.loaded_images[index]

        PreviewDialog(self, pil_image, 
            title=f"{PREVIEW_TITLE_TEMPLATE.format(index=index + 1, total=len(self.loaded_images))}")
        
        
               
    #-----------------------Helpers------------------------------------------------------
    def _on_move_selected(self, direction: int):
        """
        Move the selected item in the image list up or down by the given direction (1 or -1).
        
        If no item is selected, does nothing.
        If the new index would be out of bounds, does nothing.
        Otherwise, moves the item to the new index and updates the loaded_images list accordingly.
        """
        selected = self.imgs_tree.selection()
        if not selected:
            return
        item = selected[0]
        children = self.imgs_tree.get_children()
        current_idx = children.index(item)
        new_idx = current_idx + direction
        if new_idx < 0 or new_idx >= len(children):
            return  # Out of bounds
        self.imgs_tree.move(item, "", new_idx)
        self.loaded_images.insert(new_idx, self.loaded_images.pop(current_idx))
    
    def _add_images_to_list(self, file_paths, new_imgs):
        """Shared logic for adding images to the list (D-n-D and add)"""
        self.loaded_images.extend(new_imgs)
        for path_str, pil_img in zip (file_paths, new_imgs):
            row_id = self.imgs_tree.insert(
                "",
                "end",
                text="",
                values=(Path(path_str).name,),
                # Image parameter is set asynchronously
            )
            with self._thumbnail_lock:
                future = self._thumbnail_executor.submit(
                    self._generate_thumbnail_async,
                    pil_img,
                    row_id,
                    path_str
                )
                self._pending_thumbs[row_id] = future
            
        self.status.config(text=f"{len(self.loaded_images)} image(s) loaded.")
    
    def _generate_thumbnail_async(self, pil_img: Image.Image, row_id: str, path: str):
        """Generate thumbnail in the background thread"""
        try:
            # Stop performance in case app is closed
            if self._shutdown_request:
                return
            
            thumb = pil_img.copy()
            thumb.thumbnail((self.THUMB_MAX, self.THUMB_MAX), Image.Resampling.LANCZOS)

            # Schedule UI update in the main thread
            self.after_idle(self._update_thumb_ui, thumb, row_id, path)
        
        except Exception as e:
            logger.error(f'Thumbnail generation failed for: {path}: {e}')
            self.after_idle(self._handle_thumb_error, row_id, path)

    def _update_thumb_ui(self, thumb: Image.Image, row_id, path):
        """Update the UI with generated thumbnails in main thread"""
        try:
            with self._thumbnail_lock:
                # Verify the row exists
                if not self.imgs_tree.exists(row_id):
                    return
                
                tk_thumb = ImageTk.PhotoImage(thumb)
                self.imgs_tree.item(row_id, image=tk_thumb)
                self._thumb_refs[row_id] = tk_thumb

                # Remove from pending
                self._pending_thumbs.pop(row_id, None)
        except Exception as e:
            logger.error(f'UI update failed for: {row_id}, {path}')

    def _handle_thumb_error(self, row_id, path):
        """Handles error in thumb generation"""
        with self._thumbnail_lock:
            self._pending_thumbs.pop(row_id, None)
        logger.warning(f'Using a placeholder thumb for: {row_id}, {path}')



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
        self.bind('<f>', lambda e: self.fit_to_window())
        self.bind('<a>', lambda e: self.actual_size())
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

if __name__ == "__main__":
    app = ImageToPdfApp()
    app.mainloop()