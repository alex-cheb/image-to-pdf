import pytest
from PIL import Image
from pathlib import Path

from core import image_loader as il
from tests.test_helpers import create_sample_rgb_image

@pytest.mark.parametrize('fmt,ext', [
    ('JPEG','.jpg'),
    ('BMP','.bmp'),
    ('PNG','.png'),
    ('GIF','.gif'),
    ('TIFF','.tiff'),
])
def test_load_image(tmp_image_dir, fmt, ext):
    """
    Verifies the image of a particular format
    can be loaded and an image list returns
    """
    path = tmp_image_dir/f'test{ext}'
    create_sample_rgb_image(path, (100, 100),'#FF0000', fmt)
    images = il.add_images([path])
    assert len(images) > 0, "No images loaded"
    assert isinstance(images[0], Image.Image), "The image is not an instanse of a PIL Image type"
    assert images[0].mode == 'RGB', f"Format {fmt} failed to load as RGB"
