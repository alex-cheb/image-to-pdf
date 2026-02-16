import pytest
import tempfile
from pathlib import Path
from PIL import Image

@pytest.fixture
def tmp_image_dir():
    """Create a temporary directory for test images."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def tmp_pdf_dir():
    """Create a temporary directory for PDF outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)

@pytest.fixture
def sample_rgb_image():
    """Create a sample RGB image in memory"""
    img = Image.new('RGB', (100,100), color="#FF0000") # or 'red', (255,0,0)
    return img

@pytest.fixture
def sample_images(tmp_image_dir):
    """Create sample image files in different formats."""
    images = {}
    img = Image.new('RGB', (50,50), color='#0000FF')

    for fmt, ext in [('JPEG', '.jpg'), ('PNG', '.png'), ('BMP', '.bmp'), ('TIFF', '.tiff')]:
        path = tmp_image_dir / f'test.{ext}'
        # sample_rgb_image.save(path, format=fmt)
        image.save(path, format=fmt)
        images[fmt.lower()] = path
    return images

@pytest.fixture
def cleanup_test_files():
    """Track and cleanup test files after tests"""
    files_to_cleanup = []
    def register_file(filepath):
        files_to_cleanup.append(Path(filepath))

    yield register_file

    for filepath in files_to_cleanup:
        if filepath.exists():
            filepath.unlink()