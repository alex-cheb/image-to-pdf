# build an app main window (drag&drop zone, add files, clear list, create PDF, menu bar, toolbar)
# show the images tree view/list
# Hook elements to actions

from pathlib import Path
from typing import List

import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *

from PIL import Image, ImageTk, UnidentifiedImageError

from core.image_loader import add_images
from core.pdf_builder import build_pdf

class ImageToPdfApp(tb.Window):
    THUMB_MAX = 94  # Max size for thumbnails in the list
    def __init__(self):
        super().__init__(themename="flatly") # or any other theme
        self.title("Image to PDF Converter")
        self.geometry("600x800")

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
        tb.Button(side_panel, text="↻", width=3, command=self.on_rotate).pack(pady=(10, 0))  # small gap before rotate

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
        
        # --- Status bar ---
        self.status = tb.Label(self, text="No images loaded.", anchor="w")
        self.status.pack(fill=X, side=BOTTOM, padx=5, pady=5)

   
    #-----------------------Event Handlers------------------------------------------------------
    def on_add_images(self):
        """
        Open a file dialog to select images to add to the list.

        If images are selected, attempt to open them using Pillow. If any of the images
        cannot be opened (e.g. due to a corrupt file), show an error message. If any
        unexpected error occurs while loading the images, show a generic error message.

        If the images are loaded successfully, add them to the list and update the status
        label to reflect the number of images loaded.
        """
        file_paths = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[("Image Files", ['.jpg', '*.jpeg', '*.png', '*.bmp', '*.gif', '*.tiff'])]
        )
        
        if not file_paths:
            return  # User cancelled the dialog
        try:
            new_imgs = add_images(file_paths)   # returns a list of Pillow Image objects
        except UnidentifiedImageError as e:
            messagebox.showerror("Error", f"Corrupt image. One of the files cannot be opened: {e}")
        except Exception as exc:               # any unexpected error
            messagebox.showerror("Error", f"Failed to load images:\n{exc}")
            return
        self.loaded_images.extend(new_imgs)
        for path_str, pil_img in zip(file_paths, new_imgs):
            # ----create a thumbnail -------------------------------------------------
            thumb = pil_img.copy()
            thumb.thumbnail((self.THUMB_MAX, self.THUMB_MAX), Image.Resampling.LANCZOS)

            # ----convert to a Tk‑compatible PhotoImage -------------------------------
            # ImageTk.PhotoImage handles the PNG encoding internally.
            tk_thumb = ImageTk.PhotoImage(thumb)

            row_id = self.imgs_tree.insert(
                "",
                "end",
                text="",                    # not used when show="headings"
                values=(Path(path_str).name,),
                image=tk_thumb              # ← thumbnail goes here (left side)
            )

            # ----keep a strong reference so Tk does not GC the image ---------------
            self._thumb_refs[row_id] = tk_thumb

        self.status.config(text=f"{len(self.loaded_images)} image(s) loaded.")

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
        self._on_move_selected(-1)

    def on_move_down(self):
        self._on_move_selected(1)
    def on_rotate(self):
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
        

if __name__ == "__main__":
    app = ImageToPdfApp()
    app.mainloop()