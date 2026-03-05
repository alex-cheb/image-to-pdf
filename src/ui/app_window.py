# build an app main window (drag&drop zone, add files, clear list, create PDF, menu bar, toolbar)
# show the images tree view/list
# Hook elements to actions

from pathlib import Path
from typing import List

import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinterdnd2 import DND_FILES, TkinterDnD

from PIL import Image, ImageTk, UnidentifiedImageError

from core.image_loader import add_images
from core.pdf_builder import build_pdf

TITLE = "Image to PDF Converter"
THEME = "flatly"  # or "darkly", "cyborg", etc. (see https://ttkbootstrap.readthedocs.io/en/latest/themes/index.html)
DEFAULT_SIZE = (600, 800)
PREVIEW_DEFAULT_SIZE = (640, 480)
CANVAS_BG_COLOR = "gray20"
PREVIEW_TITLE_TEMPLATE = "Image Preview  - {index}/{total}"

class ImageToPdfApp(TkinterDnD.Tk):
    THUMB_MAX = 94  # Max size for thumbnails in the list
    def __init__(self):
        super().__init__() 
        style = tb.Style(theme=THEME)
        self.title(TITLE)
        self.geometry(f"{DEFAULT_SIZE[0]}x{DEFAULT_SIZE[1]}")

        self.loaded_images: List[Image.Image] = []
        self._thumb_refs: dict[str, ImageTk.PhotoImage] = {}

        # Create UI elements
        self.create_widgets()

    #------------- Widgets placement -------------------------------
    def create_widgets(self):
        # --- Top toolbar: file-level actions ---
        toolbar = tb.Frame(self)
        toolbar.pack(side=TOP, fill=X)

        tb.Button(toolbar, text="Add Images", command=self.on_add_images).pack(side=LEFT, padx=10, pady=5)
        tb.Button(toolbar, text="Clear List", command=self.on_clear_list).pack(side=LEFT, padx=10, pady=5)
        tb.Button(toolbar, text="Create PDF", command=self.on_create_pdf).pack(side=LEFT, padx=10, pady=5)

        
        # --- Main area: tree + side panel ---
        main_area = tb.Frame(self)
        main_area.pack(fill=BOTH, expand=True, padx=10, pady=10)

               # --- Right panel: selection-level actions ---
        side_panel = tb.Frame(main_area)
        side_panel.pack(side=RIGHT, fill=Y, padx=(5, 0))

        tb.Button(side_panel, text="↑", width=3, command=self.on_move_up).pack(pady=(10, 2))
        tb.Button(side_panel, text="↓", width=3, command=self.on_move_down).pack(pady=(10, 2))
        tb.Button(side_panel, text="↻", width=3, command=self.on_rotate).pack(pady=(10, 0))  
        tb.Button(side_panel, text="X", width=3, command=self.on_delete).pack(pady=(10, 0))  
        tb.Button(side_panel, text="🔍", width=3, command=self.on_preview).pack(pady=(10, 0))  

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
            new_imgs = add_images(file_paths)
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
            thumb = pil_img.copy()
            thumb.thumbnail((self.THUMB_MAX, self.THUMB_MAX), Image.Resampling.LANCZOS)
            tk_thumb = ImageTk.PhotoImage(thumb)

            row_id = self.imgs_tree.insert(
                "",
                "end",
                text="",
                values=(Path(path_str).name,),
                image=tk_thumb
            )
            self._thumb_refs[row_id] = tk_thumb

        self.status.config(text=f"{len(self.loaded_images)} image(s) added to list.")


class PreviewDialog(tb.Toplevel):
    """A dialog window to preview an image with zoom and fit-to-window functionality."""
    def __init__(self, parent, pil_image: Image.Image, title: str | None =None):
        super().__init__(parent)
        self.title(title or "Image Preview")
        self.geometry(f"{PREVIEW_DEFAULT_SIZE[0]}x{PREVIEW_DEFAULT_SIZE[1]}")

        self.original = pil_image.copy()  # Keep original for zooming
        self.zoom = 1.0
        self._preview_images = []  # To keep references to PhotoImage objects

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
                    text="A - full size, F - fit to window, +/- - zoom", anchor="center")
        self.label.pack(side=BOTTOM, fill=X)

        # Place the scrollbars and canvas in the frame
        vbar.pack(side=RIGHT, fill=Y)
        hbar.pack(side=BOTTOM, fill=X)
        self.canvas.pack(fill=BOTH, expand=True)

        # Event bindings for keyboard controls
        self.bind('<Escape>', lambda e: self.destroy())
        self.bind('<f>', lambda e: self.fit_to_window())
        self.bind('<a>', lambda e: self.actual_size())
        self.bind('<plus>', lambda e: self.zoom_img(factor=1.1))
        self.bind('<minus>', lambda e: self.zoom_img(factor=0.9))

        self.fit_to_window()
    #-----------------------Image display and manipulation------------------------------------------------------
    def fit_to_window(self):
        """Resize the image to fit within the current window size while maintaining aspect ratio."""
        width, height = self.winfo_width(), self.winfo_height()
        if width <= 1 or height <= 1:  # Initial size might be 1x1, use default in that case
            width, height = PREVIEW_DEFAULT_SIZE
        
        img_copy = self.original.copy()
        img_copy.thumbnail((width, height), Image.Resampling.LANCZOS)
        self._update_canvas(img_copy)
    
    def actual_size(self):
        """A handler to display the image at its actual size (100% zoom)."""
        self._update_canvas(self.original.copy())

    def zoom_img(self, factor: float):
        """ A handler for zooming the image in or out by the given factor."""
        self.zoom *= factor
        width, height = self.original.size
        new_size = (int(width * self.zoom), int(height * self.zoom))
        img = self.original.resize(new_size, Image.Resampling.LANCZOS)
        self._update_canvas(img)

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
        self._preview_images.append(tk_img)  # Keep reference to prevent GC

if __name__ == "__main__":
    app = ImageToPdfApp()
    app.mainloop()