from pathlib import Path
from typing import List
from PIL import Image

def build_pdf(images: List[Image.Image], output_path: Path) -> None:
    """
    Save a list of PIL images to a single PDF file.

    Parameters
    ----------
    images: a list of PIL Image objects already converted to RGB
    output_path: the path where the PDF should be saved. Should end with .pdf
    """
    if not images:
        raise ValueError("No images provided to build the PDF.")
    output_path = Path(output_path)

    first, * rest = images
    first.save(output_path, 
               format="PDF",
               save_all=True,
               append_images=rest,
               resolution=150.0, # adjusts PDF metadata, not the actual image quality
            #    quality=95, # for JPEG compression if used internally by Pillow
               ) 