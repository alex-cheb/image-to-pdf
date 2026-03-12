# Validate the image path and format
# Open image using PIL
# Return the list of Pillow Image objects
from pathlib import Path
from typing import List, Iterable
from PIL import Image, ImageOps, UnidentifiedImageError
from loguru import logger

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'}

def _is_valid_image(path: Path) -> bool:
    """Returns true in case the file format is supported"""
    return path.suffix.lower() in SUPPORTED_EXTENSIONS

def add_images_lenient(paths: Iterable[Path]) -> tuple[List[Image.Image], List[Path]]:
    """Returns a tuple containing a list of images and a list of skipped paths items"""
    images = []
    skipped = []

    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file() or not _is_valid_image(path):
            logger.warning(f"'{path}' could not be identified as an image.")
            skipped.append(path)
            continue
        try:
            img = Image.open(path)
            img = ImageOps.exif_transpose(img)  # Handle EXIF orientation
            if img.mode != 'RGB':
                img = img.convert('RGB') # Convert to RGB to work with PDF
            images.append(img)
        except UnidentifiedImageError as e:
            logger.warning(f"Skipping corrupted file. Error {e}")
            skipped.append(path)
    return images, skipped

def add_images(paths: Iterable[Path]) -> List[Image.Image]:
    """
    Validate a collection of file paths and load them as Pillow Image objects.

    Parameters
    ----------
    paths:
        An iterable of pathlib.Path objects (or strings that can be cast to Path).

    Returns
    -------
    List[Image.Image]
        A list of opened Pillow Image instances, ready for further processing.

    Raises
    ------
    InvalidImageError
        If any path does not point to a supported image file.
    UnidentifiedImageError
        Propagated from Pillow when a file cannot be decoded as an image.
    """
    images: List[Image.Image] = []

    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file():
            raise FileNotFoundError(f"'{path}' does not exist or is not a file.")
        if not _is_valid_image(path):
            raise ValueError(f"'{path}' has an unsupported file extension. Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}")
        try:
            img = Image.open(path)
            img = ImageOps.exif_transpose(img)  # Handle EXIF orientation
            if img.mode != 'RGB':
                img = img.convert('RGB') # Convert to RGB to work with PDF
            images.append(img)
        except UnidentifiedImageError as e:
            logger.warning(f"'{path}' could not be identified as an image: {e}")
            raise UnidentifiedImageError(f"'{path}' could not be identified as an image: {e}")
    return images
