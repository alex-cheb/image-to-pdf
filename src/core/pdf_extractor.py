import io
import os
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image
import pypdf
from loguru import logger

SUPPORTED_PDF_FORMATS = {'.pdf'}
OUTPUT_IMAGE_FORMATS = {'.jpg', '.png'}

def extract_images_from_pdf(pdf_path: Path) -> List[Tuple[Image.Image, int, int]]:
    path = _validate_path(pdf_path)

    try:
        reader = pypdf.PdfReader(str(path))
    except Exception as e:
        logger.error(f"Failed to read PDF: {e}")
        raise ValueError(f"Failed to read PDF: {e}")


    imgs = []
    seen_objs = set()  # To track already processed objects and avoid duplicates

    for page_num, page in enumerate(reader.pages, start=1):
        try:
            page_start = len(imgs)
            # Check if the page contains resources
            resources = page.get('/Resources')
            if resources:
                _extract_from_resources(resources, seen_objs, imgs, page_num)
            
            # Extract inline images from the page content
            _extract_inline_images(page, imgs, page_num)
            for page_img_idx, item in enumerate(imgs[page_start:], start=1):
                imgs[page_start + page_img_idx - 1] = (item[0], item[1], page_img_idx)
        except Exception as e:
            logger.error(f"Error processing page {page_num}: {e}")
    logger.info(f"Extracted {len(imgs)} images from PDF: {pdf_path}")
    return imgs

def save_images(
        imgs: List[Tuple[Image.Image, int, int]], 
        output_dir: Path,
        prefix: str = "image", 
        format: str = 'PNG') -> List[Path]:
    """Save extracted images to the specified directory in the given format."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []

    for img, page_num, idx in imgs:
        f_name = f"{prefix}_{page_num}_{idx}.{format}"
        output_path = output_dir / f_name

        try:
            img.save(output_path, format=format)
            saved_paths.append(output_path)
        except Exception as e:
            logger.error(f"Failed to save image {f_name}: {e}")
    
    logger.info(f"Saved {len(saved_paths)} images to: {output_dir}")
    return saved_paths

def _extract_from_resources(resources, 
        seen_objs : set, 
        imgs: List[Tuple[Image.Image, int]], 
        page_num: int) -> None:
    """Recursively extract images from PDF resources."""
    resources = _resolve(resources)
    x_objs_dics = resources.get('/XObject')
    if not x_objs_dics:
        return
    
    x_objs = _resolve(x_objs_dics)
    for obj_name in x_objs:
        obj = _resolve(x_objs[obj_name])
        
        # Avoid duplicates
        if hasattr(obj, 'indirect_reference') and obj.indirect_reference:
            obj_id = obj.indirect_reference.idnum
        else:
            obj_id = hash(bytes(obj.get_data()) if hasattr(obj, 'get_data') else id(obj))

        subtype = obj.get('/Subtype')
        if subtype == '/Image':
            if obj_id not in seen_objs:
                seen_objs.add(obj_id)
                img = _safe_extract(obj, page_num, obj_name)
                if img:
                    imgs.append((img, page_num))

        elif subtype == '/Form':
            # Form can have its own /Resources entry
            if obj_id not in seen_objs:
                seen_objs.add(obj_id)
                nested_resources = obj.get('/Resources')
                if nested_resources:
                    _extract_from_resources(nested_resources, seen_objs, imgs, page_num)

def _extract_inline_images(page, imgs: List[Tuple[Image.Image, int]], page_num: int) -> None:
    """Extract inline images from page"""
    try:
        for img in page.images:
            if getattr(img , 'indirect_reference', None) is None:
                # if indirect regerence is None, this is an inline image, not XObject:
                try:
                    pic = Image.open(io.BytesIO(img.data))
                    pic.load()  # Force loading to catch errors
                    imgs.append((pic, page_num))
                except Exception as e:
                    logger.error(f"Failed to decode inline image from page {page_num}: {e}")
    except Exception as e:
        logger.error(f"Failed to extract inline images from page {page_num}: {e}")
        
def _validate_path(pdf_path: Path | str) -> Path:
    """Validate the provided path and return a Path object."""
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"File not found: {pdf_path}")
    if pdf_path.suffix.lower() != '.pdf':
        raise ValueError(f"Invalid file type: {pdf_path}. Expected a PDF file.")
    if not os.access(pdf_path, os.R_OK):
        raise PermissionError(f"Permission denied: {pdf_path}")
    logger.info(f'Successfully validated PDF path: {pdf_path}')
    return pdf_path

def _resolve(obj):
    """Resolves indirect object to its own objects"""
    if isinstance(obj, pypdf.generic.IndirectObject):
        return obj.get_object()
    return obj

def _safe_extract(obj, page_num: int, obj_name: str) -> Optional[Image.Image]:
    """Extracts image or returns None if failed, with logging."""
    try:
        img = _extract_img_from_obj(obj)
        if img is None:
            logger.warning(f'Object {obj_name} on page {page_num} is not a valid image or failed to extract.')
        return img
    except Exception as e:
        logger.error(f"Failed to extract image from page {page_num}, object {obj_name}: {e}")
        return None

def _get_color_mode(color_space) -> str:
    """Determine the color mode based on the ColorSpace entry."""
    if '/DeviceRGB' in color_space or '/DefaultRGB' in color_space:
        return 'RGB'
    elif '/DeviceCMYK' in color_space or '/DefaultCMYK' in color_space:
        return 'CMYK'
    elif any(x in color_space for x in ('/DeviceGray', '/CalGray', '/DefaultGray')):
        return 'L'
    else:
        logger.warning(f"Unsupported color space: {color_space}. Defaulting to RGB.")
        return 'RGB'

def _extract_img_from_obj(obj) -> Image.Image | None:
    """
    Extract an image from a PDF object and return it as a PIL Image.
    Return None in case of failure
    """
    try:
        data = obj.get_data()
    except Exception as e:
        logger.error(f"Failed to get data from object: {e}")
        return None
    if not data:
        logger.warning("Object data is empty.")
        return None
    
    # --- Get image format ---
    color_space = _resolve(obj.get('/ColorSpace'))
    if isinstance(color_space, pypdf.generic.ArrayObject) and len(color_space) > 0:
        color_space = color_space[0]
    color_space = str(color_space)
    # ---

    # --- Get attributes ---
    try:
        width = int(obj['/Width'])
        height = int(obj['/Height'])
    except (KeyError, TypeError) as e:
        logger.error(f"Image object missing required dimensions: {e}")
        return None
    pdf_filter = obj.get('/Filter')

    # Getting images stored in JPEG format variations
    if pdf_filter in ('/DCTDecode', '/JPXDecode', 
        pypdf.generic.NameObject('/DCTDecode'), 
        pypdf.generic.NameObject('/JPXDecode')):
        return Image.open(io.BytesIO(data))
    
    mode = _get_color_mode(color_space)

    try:
        return Image.frombytes(mode, (width, height), data)
    except Exception as e:
        logger.error(f"Failed to create image from bytes: {e}")
        return None