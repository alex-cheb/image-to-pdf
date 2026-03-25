# Validate the image path and format
# Open image using PIL
# Return the list of Pillow Image objects
import os
from pathlib import Path
from typing import List, Iterable, Optional
from PIL import Image, ImageOps, UnidentifiedImageError
from loguru import logger

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff'}
MAX_FILE_SIZE = 50 * 1024 * 1024 # max size of 50 MB
MAX_WIDTH = 15000
MAX_HEIGHT = 15000
MIN_WIDTH = 1
MIN_HEIGHT = 1

def add_images_lenient(paths: Iterable[str]) -> tuple[List[Image.Image], List[str]]:
    """Returns a tuple containing a list of images and a list of skipped paths items"""
    images = []
    skipped = []

    for raw_path in paths:
        # path = Path(raw_path)
        path = _validate_file_path(raw_path)
        if path is None:
            logger.warning(f"'{_sanitize_path_for_log(raw_path)}' failed validation.")
            skipped.append(raw_path)
            continue

        if not _is_valid_image(path):
            logger.warning(f"'{_sanitize_path_for_log(path)}' could not be identified as an image.")
            skipped.append(raw_path)
            continue
        is_safe, error_msg = _validate_image_safety(path)
        if not is_safe:
            logger.warning(f"Unsafe image file: {_sanitize_path_for_log(path)}: {error_msg}")
            skipped.append(raw_path)
            continue
        try:
            img = Image.open(path)
            img = ImageOps.exif_transpose(img)  # Handle EXIF orientation
            if img.mode != 'RGB':
                img = img.convert('RGB') # Convert to RGB to work with PDF
            images.append(img)
        except UnidentifiedImageError as e:
            logger.warning(f"Skipping corrupted file. Error {e}")
            skipped.append(raw_path)
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
        # path = Path(raw_path)
        path = _validate_file_path(str(raw_path))
        if path is None:
            raise ValueError(f"Invalid or inaccessible path: {raw_path}")
        if not _is_valid_image(path):
            raise ValueError(f"'{path}' has an unsupported file extension. Supported formats: {', '.join(SUPPORTED_EXTENSIONS)}")
        is_safe, error_msg = _validate_image_safety(path)
        if not is_safe:
            raise ValueError(f"Unsafe image file: {path}: {error_msg}")

        img = Image.open(path)
        img = ImageOps.exif_transpose(img)  # Handle EXIF orientation
        if img.mode != 'RGB':
            img = img.convert('RGB') # Convert to RGB to work with PDF
        images.append(img)
        
    return images

# --- Helper functions
def _is_valid_image(path: Path) -> bool:
    """Returns true in case the file format is supported"""
    return path.suffix.lower() in SUPPORTED_EXTENSIONS

def _validate_file_path(path_str: str) -> Optional[Path]:
    """ Validates the file path correctness. Handles symlinks, 
        not existing files, not readable """
    try:
        path = Path(path_str).resolve()

        # if not path.exists():
        #     logger.warning(f'The {_sanitize_path_for_log(path_str)} does not exist')
        #     return None
        if not path.exists() or not path.is_file():
            logger.warning(f'The {_sanitize_path_for_log(path_str)} does not exist or is not a file')
            return None

        # if not path.is_file():
        #     logger.warning(f'The {_sanitize_path_for_log(path_str)} is not a file')
        #     return None

        if not os.access(path, os.R_OK):
            logger.warning(f'The file {_sanitize_path_for_log(path_str)} is not a readable')
            return None
        
        return path
    except (OSError, ValueError, RuntimeError) as e:
        logger.warning(f"Invalid path '{_sanitize_path_for_log(path_str)}': {e}")
        return None

def _validate_image_safety(path: Path) -> tuple[bool, str]:
    """ Validate image file for safety and performance """
    try:
        file_size = path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            size_mb = file_size / (1024*1024)
            return False, f"File is too big: {size_mb:.1f} MB"
        if file_size == 0:
            return False, 'File is empty'

        with Image.open(path) as img:
            w, h = img.size
            if w > MAX_WIDTH or h > MAX_HEIGHT:
                return False, f"Image is too large: {w}x{h}"
        return True, ""
    except Exception as e:
        filename = _sanitize_path_for_log(path)
        error_type = type(e).__name__
        
        # Provide helpful error messages based on exception type
        if error_type == "UnidentifiedImageError":
            return False, "File format not recognized or corrupted"
        elif error_type == "PermissionError":
            return False, "Permission denied"
        elif error_type == "OSError":
            return False, "File system error"
        else:
            # For other exceptions, provide generic message
            return False, f"Cannot validate image ({error_type})"


def _sanitize_path_for_log(path: Path | str) -> str:
    """
    Sanitizes file paths to avoid disclosure of sensitive data
    Common practice for highlevel logs. tradeoff between traceability 
    and security
    """
    return Path(path).name