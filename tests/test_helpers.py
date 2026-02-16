import io
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
from pypdf import PdfReader

def create_test_image(path, mode, size, fmt, color=None):
    """
    Creates a sample image, saves it to a disk and returns an image object
    Color limitations regarding the picture mode:
        - L - a single integer 0 .. 255;
        - P - does not support color;
        - CMYK - use 4 items tuple;
    Format limitations:
        - JPEG/JPG does not support RGBA
    """
    if color is not None:
        img = Image.new(mode=mode, size=size, color=color)
    else:
        img = Image.new(mode=mode, size=size)
    img.save(Path(path), format=fmt)
    return img

def create_sample_rgb_image(path, size, color, fmt):
    """Creates a simple image in the RGB mode"""
    img = create_test_image(path=path, mode='RGB', size=size, color=color, fmt=fmt)
    return img

def create_corrupted_file(path):
    """Create invalid image file"""
    path = Path(path)
    with open(path, 'wb') as f:
        f.write(b'Garbage file with no necessary data')

def assert_images_equal(first_image, second_image):
    """Assert images are identical using PIL"""
    assert first_image.size == second_image.size
    assert first_image.mode == second_image.mode

    diff = ImageChops.difference(first_image, second_image)
    assert diff.getbbox() is None, "Images differ in pixel data"

def assert_images_similar(first_image, second_image, threshold=1.0):
    """Check if two images are visibly similar within a threshold"""
    # if first_image.size != second_image.size or first_image.mode != second_image.mode:
    #     return False
    assert first_image.size == second_image.size
    assert first_image.mode == second_image.mode

    diff = ImageChops.difference(first_image, second_image)
    # statistics difference
    stats = ImageStat.Stat(diff)
    # Check if the mean difference is within threshold
    avg_diff = sum(stats.mean)/len(stats.mean)

    # return avg_diff <= threshold
    assert avg_diff <= threshold, f"Images are not similar enough. Differ by {avg_diff:.4f}"


def create_file(path, extension: str):
    """Create a sample file with defined extension"""
    path = Path(path)

    if not extension.startswith('.'):
        extension = f'.{extension}'

    filepath = path.parent / f'{path.stem}{extension}'
    filepath.write_text("Some value")
    return filepath

def validate_pdf_file(path):
    """Verify the PDF exists and can be opened"""
    path = Path(path)
    if not path.exists():
        return False
    file_size = path.stat().st_size
    if file_size < 10: # Minimum size for a dummy PDF
        return False
    try:
        with open(path, 'rb') as f:
            header = f.read(5)
            if header != b'%PDF-':
                return False
            seek_distance = min(1024, file_size)
            f.seek(-seek_distance, 2)
            last_chunk = f.read()
            return b'%%EOF' in last_chunk
    except (OSError, IOError):
        return False

def get_page_count(path):
    """Get pages quantity in the created file"""
    path = Path(path)
    try:
        reader = PdfReader(path)
        return len(reader.pages)
    except Exception:
        return 0

def get_page_size(path, page_num=0):
    """Retrieve page size"""
    path = Path(path)
    try:
        reader = PdfReader(path)
        page = reader.pages[page_num]

        # Get the mediabox (to define page size)
        # Returns (x0, y0, x1, y1) in points (1/72 inch)
        mediabox = page.mediabox
        width = float(mediabox.width)
        height = float(mediabox.height)

        return (width, height)
    except Exception:
        return None

def extract_image(pdf, page_num=0):
    """Extract the first image from a specific PDF page"""
    try:
        reader = PdfReader(pdf)
        page = reader.pages[page_num]
        
        for image_file in page.images:
            return Image.open(io.BytesIO(image_file.data))
        return None  # No images found
    except Exception:
        return None