from pathlib import Path
from typing import List, Tuple
import tkinter.ttk as ttk
from tkinter import filedialog, messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
from loguru import logger

import core.pdf_extractor as pdf_extractor
from ttkbootstrap.tooltip import ToolTip

DIALOG_SIZE = (500, 600)
THUMB_SIZE = 150
AVAILABLE_FORMATS = ('PNG', 'JPEG')

TITLE = "PDF Image Extractor"
SELECT_PDF_TEXT="Select PDF File"
OUTPUT_DIR_TEXT="Output Directory"
IMAGE_FMT_TEXT = "Image Format:"
SELECT_FOLDER_TEXT = "Browse..."

SELECT_ALL_TEXT = "Select All"
DESELECT_ALL_TEXT = "Deselect All"
EXTRACT_SELECTED_TEXT = "Extract Selected"

SHORTCUTS_TEXT = "Ctrl+O - select pdf, Ctrl+S - save images, Esc/Ctrl+Q - quit, Ctrl+A - toggle select all"

class ExtractorDialog(tb.Toplevel):
    """Dialog for extracting images from PDF files."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title(TITLE)
        self.geometry(f"{DIALOG_SIZE[0]}x{DIALOG_SIZE[1]}")
        
        self.pdf_path = None
        self.pdf_path_tooltip = None
        self.extractor = None
        self.extracted_images = []  # List of (img, page, idx, selected)
        self._thumb_refs = []
        self.output_dir = None
        self.output_dir_tooltip = None
        
        self.create_widgets()

    def create_widgets(self):
        
        # --- PDF Select section ---
        pdf_select_frame = tb.Frame(self)
        pdf_select_frame.pack(fill=X, padx=10, pady=10)

        tb.Label(pdf_select_frame, text=SELECT_PDF_TEXT).pack(side=LEFT)
        self.pdf_label = tb.Label(pdf_select_frame, 
            text="No file selected", anchor=W, width=40)
        self.pdf_label.pack(side=LEFT, fill=X, expand=True, padx=10)
        tb.Button(pdf_select_frame, 
            text=SELECT_FOLDER_TEXT, 
            command=self.on_browse_pdf).pack(side=RIGHT)
        self.pdf_path_tooltip = ToolTip(self.pdf_label, text = self.pdf_path or "No file selected")

        # --- Image Grid section ---
        grid_frame = tb.Frame(self)
        grid_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

        canvas = tb.Canvas(grid_frame)
        scrollbar = tb.Scrollbar(grid_frame, 
                orient=VERTICAL, 
                command=canvas.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.grid_container = tb.Frame(canvas)

        self.grid_container.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0,0), window=self.grid_container, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)

        # --- Settings section ---
        output_frame = tb.Frame(self)
        output_frame.pack(fill=X, padx=10, pady=10)

        tb.Label(output_frame, text=OUTPUT_DIR_TEXT).pack(side=LEFT)
        self.output_label = tb.Label(output_frame, 
                                text=SELECT_FOLDER_TEXT, anchor=W,
                                width=40)
        self.output_label.pack(side=LEFT, fill=X, expand=True, padx=10)
        tb.Button(output_frame, 
            text=SELECT_FOLDER_TEXT, 
            command=self.on_browse_output).pack(side=RIGHT)
        self.output_dir_tooltip = ToolTip(self.output_label, text = self.output_dir or "No output directory selected")
        
        #Format selection
        settings_frame = tb.Frame(self)
        settings_frame.pack(fill=X, padx=10, pady=10)
        tb.Label(settings_frame, text=IMAGE_FMT_TEXT).pack(side=LEFT)
        self.format_var = tb.StringVar(value=AVAILABLE_FORMATS[0])
        tb.Radiobutton(settings_frame, 
            text=AVAILABLE_FORMATS[0], 
            variable=self.format_var, 
            value=AVAILABLE_FORMATS[0]).pack(side=LEFT, padx=10)
        tb.Radiobutton(settings_frame, 
            text=AVAILABLE_FORMATS[1], 
            variable=self.format_var, 
            value=AVAILABLE_FORMATS[1]).pack(side=LEFT, padx=10)
        prefix_lbl = tb.Label(settings_frame, text="Image name prefix:")
        prefix_lbl.pack(side=LEFT, padx=(20, 5))
        self.prefix_var = tb.StringVar(value="image")
        prefix_entry = tb.Entry(settings_frame, textvariable=self.prefix_var, width=15)
        prefix_entry.pack(side=LEFT, padx=5)
        
        # --- Buttons ---
        button_frame = tb.Frame(self)
        button_frame.pack(fill=X, padx=10, pady=10)

        tb.Button(button_frame, 
            text=SELECT_ALL_TEXT, 
            command=self.on_select_all).pack(side=LEFT, padx=5)
        tb.Button(button_frame, 
            text=DESELECT_ALL_TEXT, 
            command=self.on_deselect_all).pack(side=LEFT, padx=5)
        tb.Button(button_frame, 
            text=EXTRACT_SELECTED_TEXT, 
            command=self.on_extract, 
            bootstyle="success").pack(side=RIGHT, padx=5)


        # --- Keyboard Shortcuts ---
        self.bind('<Escape>', lambda e: self.destroy())
        self.bind('<Control-KeyPress>', self._handle_ctrl_shortcuts)

        # --- Status Bar ---
        self.status = tb.Label(self, text="Ready", anchor=W)
        self.status.pack(fill=X, side=BOTTOM, padx=10, pady=5)
        self.label = tb.Label(self, 
            text=SHORTCUTS_TEXT,  anchor="center")
        self.label.pack(side=BOTTOM, fill=X)
    
    def on_browse_pdf(self):
        """Opens a dialogue for PDF selection"""
        file_path = filedialog.askopenfilename(
            title=SELECT_PDF_TEXT, 
            filetypes=[("PDF Files", "*.pdf")])
        
        if not file_path:
            return
        
        try:
            self.pdf_path = Path(file_path)
            self.pdf_label.config(text=self.pdf_path.name)
            self.pdf_path_tooltip.text = str(self.pdf_path)
            self.load_pdf_images()
            self.output_dir = self.pdf_path.parent
            self.output_label.config(text=str(self.output_dir))
            self.output_dir_tooltip = ToolTip(self.output_label, text=self.output_dir)
        except Exception as e:
            messagebox.showerror("Error", f'Failed to load PDF: {e}')
            logger.error(f"Failed to load PDF: {e}")

    def load_pdf_images(self):
        """
        Extracts images from the selected PDF
        and displays them in the grid.
        """
        if not self.pdf_path:
            return
        try:
            self.status.config(text="Extracting images...")
            self.update()

            images = pdf_extractor.extract_images_from_pdf(self.pdf_path)
            
            self.extracted_images = [(img, page, idx, True) for img, page, idx in images]
            
            self.display_image_grid()
            
            self.status.config(text=f"Found {len(images)} images")
        except Exception as e:
            messagebox.showerror("Error", f'Failed to extract images: {e}')
            logger.error(f"Failed to extract images: {e}")
            self.status.config(text="Error")

    def display_image_grid(self):
        """Displays extracted images in a grid with checkboxes."""
        # Clear previous thumbnails
        for widget in self.grid_container.winfo_children():
            widget.destroy()
        self._thumb_refs.clear()

        cols = 3
        for idx, (img, page, img_idx, selected) in enumerate(self.extracted_images):
            row = idx // cols
            col = idx % cols

            frame = tb.Frame(self.grid_container, 
                             relief=RAISED, borderwidth=2)
            frame.grid(row=row, column=col, padx=5, pady=5)

            # Thumbnail
            thumb = img.copy()
            thumb.thumbnail((THUMB_SIZE, THUMB_SIZE),
                Image.Resampling.LANCZOS)
            thumb_tk = ImageTk.PhotoImage(thumb)
            self._thumb_refs.append(thumb_tk)
            self.update()  # Ensure UI updates to show thumbnails

            # Checkbox
            chk_var = tb.BooleanVar(value=selected)
            chk_var.trace_add("write", lambda *args, i=idx, v=chk_var: self.on_toggle_selection(i, v))
            chk = tb.Checkbutton(frame, variable=chk_var)
            chk.pack(anchor=NW)

            lbl = tb.Label(frame, image=thumb_tk)
            lbl.pack()

            info = tb.Label(frame, text=f"Page {page}, Img {img_idx}")
            info.pack()

            # # Store checkbox variable for later retrieval
            # self.extracted_images[idx] = (img, page, img_idx, chk_var)

    def on_toggle_selection(self, idx: int, var: tb.BooleanVar):
        """Toggle selection state of an image."""
        img, page, img_idx, _ = self.extracted_images[idx]
        self.extracted_images[idx] = (img, page, img_idx, var.get())

    def on_select_all(self):
        """Select all images."""
        self.extracted_images = [(img, page, idx, True) for img, page, idx, _ in self.extracted_images]
        self.display_image_grid()
    
    def on_deselect_all(self):
        """Clear image selection."""
        self.extracted_images = [(img, page, idx, False) for img, page, idx, _ in self.extracted_images]
        self.display_image_grid()

    def on_browse_output(self):
        """Handle output folder selection"""
        dir_path = filedialog.askdirectory(title=OUTPUT_DIR_TEXT)
        if dir_path:
            self.output_dir = Path(dir_path)
            self.output_label.config(text=str(self.output_dir))
            self.output_dir_tooltip.text = str(self.output_dir)

    def on_extract(self):
        """Extract images"""
        if not hasattr(self, 'output_dir') or not self.output_dir:
            messagebox.showwarning(
                "No output Directory", 
                "Please select an output directory.")
            return
        
        selected = [(img, page, idx) for img, page, idx, sel in self.extracted_images if sel]
        
        if not selected:
            messagebox.showinfo(
                "No images selected", 
                "Please select at least one image to extract.")
            return
        
        try:
            self.status.config(text=f"Saving {len(selected)} images...")
            self.update()
            safe_prefix = self._sanitize_prefix(self.prefix_var.get())
            
            saved_paths = pdf_extractor.save_images(
                selected,
                self.output_dir,
                safe_prefix,
                self.format_var.get())
            
            self.status.config(text=f"Saved {len(saved_paths)} images to {self.output_dir}")

        except Exception as e:
            messagebox.showerror("Error", f'Failed to save images: {e}')
            logger.error(f"Failed to save images: {e}")
            self.status.config(text="Error")


    def _handle_ctrl_shortcuts(self, event):
        """Handle shortcuts with no layout dependencies"""
        if not (event.state & 0x0004):
            return

        keycode_map = {
            79: self.on_browse_pdf, # O
            83: self.on_extract, # S
            81: self.destroy, # Q
            65: self._toggle_select_all, # A
        }
        if event.keycode in keycode_map:
            keycode_map[event.keycode]()

    def _toggle_select_all(self):
        """Toggle between select all and deselect all."""
        if self.extracted_images and all(sel for _, _, _, sel in self.extracted_images):
            self.on_deselect_all()
        else:
            self.on_select_all()

    def _sanitize_prefix(self, prefix: str, max_length: int = 50) -> str:
        """Sanitize filename prefix - remove invalid characters.
        
        Args:
            prefix: User input string
            max_length: Maximum allowed length
            
        Returns:
            Sanitized prefix safe for filenames
        """
        # Invalid filename characters (Windows & Unix)
        invalid_chars = r'<>:"/\|?*'
        
        # Remove invalid characters
        sanitized = ''.join(c for c in prefix if c not in invalid_chars)
        
        # Replace spaces with underscores
        sanitized = sanitized.replace(' ', '_')
        
        # Remove leading/trailing whitespace
        sanitized = sanitized.strip()
        
        # Limit length
        sanitized = sanitized[:max_length]
        
        # If empty after sanitization, use default
        if not sanitized:
            sanitized = "image"
        
        return sanitized