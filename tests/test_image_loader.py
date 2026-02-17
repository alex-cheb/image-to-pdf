import pytest
import random
from PIL import Image, UnidentifiedImageError
from pathlib import Path

from core import image_loader as il
from tests.test_helpers import *

@pytest.mark.parametrize('fmt,ext', [
    ('JPEG','.jpg'),
    ('BMP','.bmp'),
    ('PNG','.png'),
    ('GIF','.gif'),
    ('TIFF','.tiff'),
])
def test_positive_load_image(tmp_image_dir, fmt, ext):
    """
    Verifies the image of a particular format
    can be loaded and an image list returns.
    Requirement 1.4
    """
    path = tmp_image_dir/f'test{ext}'
    create_sample_rgb_image(path, (100, 100),'#FF0000', fmt)
    images = il.add_images([path])
    assert len(images) > 0, "No images loaded"
    assert isinstance(images[0], Image.Image), "The image is not an instance of a PIL Image type"
    assert images[0].mode == 'RGB', f"Format {fmt} failed to load as RGB"


def test_nonexistent_file_raises_proper_error(tmp_image_dir):
    """
    Verifies the load image handles non existing files
    Requirement 2.1
    """
    path = tmp_image_dir/'non_existent_file.jpg'
    with pytest.raises(FileNotFoundError, match="does not exist or is not a file."):
        images = il.add_images([path])


def test_unsupported_extension_load_image(tmp_image_dir):
    """
    Verifies the load image handles unsopported file extensions
    Requirement 2.2
    """
    path = tmp_image_dir/'tmp.txt'
    path.touch()

    with pytest.raises(ValueError, match="has an unsupported file extension. Supported formats:"):
        images = il.add_images([path])


def test_corrupt_file_load_image(tmp_image_dir):
    """
    Verifies the load image gracefully handles corrupt files
    Requirement 2.3
    """
    path = tmp_image_dir / f'test.jpg'
    create_corrupted_file(path)
    with pytest.raises(UnidentifiedImageError, match="could not be identified as an image:"):
        images = il.add_images([path])


def test_empty_list_load_image(tmp_image_dir):
    """
    Verifies the load image gracefully handles empty list
    Requirement 2.4
    """
    images = il.add_images([])
    assert images == list(), f"The empty input does not return an empty list, but {images}"


def test_exif_orientation_handling(tmp_image_dir):
    """
    Verifies that EXIF orientation data is correctly applied
    Requirement 1.3
    """
    path = tmp_image_dir/'test_exif.jpg'
    img = Image.new('RGB', (200, 100),'#FF0000')

    exif = img.getexif()
    exif[0x0112] = 6 # Rotate 90 CW
    img.save(path, 'JPEG', exif=exif)

    images = il.add_images([path])
    assert images[0].size == (100, 200), "Image was not rotated"
    

# Can be a parametrized test with several qty inputs.
def test_multiple_images_loaded(tmp_image_dir):
    """
    Verifies the proper image quantity is loaded
    Requirement 1.1
    """
    paths = []
    qty = random.randint(1,10)
    for i in range(qty):
        path = tmp_image_dir/f'test_{i}.png'
        img = create_sample_rgb_image(path, (100,100), '#0000FF', 'PNG')
        paths.append(path)
    loaded_images = il.add_images(paths)
    assert len(loaded_images) == qty, \
        f"Not all images were loaded, the list should be of {qty} elements, but is of {len(loaded_images)}"


@pytest.mark.parametrize('color_mode,color,fmt,ext', [
    ('CMYK', (100,100,0,1),'JPEG', '.jpg'),
    ('RGBA', (255,0,0,255),'PNG', '.png'),
    ('L', (255,), 'TIFF', '.tiff')
])
def test_color_modes_convert_to_rgb_during_load(tmp_image_dir, color_mode, color, fmt, ext):
    """
    Verifies that images in different color modes
    Are properly converted to RGB during image load.
    Requirement 1.2
    """
    path = tmp_image_dir/f'test_{color_mode}{ext}'
    img = create_test_image(path=path, mode=color_mode, size=(100,100), color=color, fmt=fmt)
    assert img.mode == color_mode, f"The image was expected to be created as {color_mode}, but was created as {img.mode}"
    images = il.add_images([path])
    assert len(images) > 0, "The image was not loaded, the list is empty" 
    assert images[0].mode == 'RGB', f"The mode is not properly converted to RGB and is {images[0].mode}"


@pytest.mark.parametrize('size',[
    (150,250),
    (1024,768),
    (3150,3250),
    (1,2),
    (100,100),   
], ids=lambda s: f"{s[0]}x{s[1]}")
def test_image_dimensions_preserved(tmp_image_dir, size):
    """
    Verifies that the image dimensions are preserved
    during image load process
    Requirement 5.1
    """
    path = tmp_image_dir/f'test{size[0]}x{size[1]}.jpg'
    img = create_sample_rgb_image(path, size, '#0000FF', 'JPEG')
    assert img.size == size, \
        f"Initial image created with the wrong dimensions size expected to be {size}, but is {images[0].size}"
    images = il.add_images([path])
    assert images[0].size == size, f"The image size expected to be {size}, but is {images[0].size}"


def test_preserve_file_order_during_load(tmp_image_dir):
    """
    Verifies that the image order is preserved 
    during the load process
    Requirement 5.3
    """
    paths = []
    colours = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF']
    for i, colour in enumerate(colours):
        path = tmp_image_dir/f'test_{i}.png'
        create_sample_rgb_image(path, (10,10), colour, 'PNG')
        paths.append(path)
    images = il.add_images(paths)
    for i, img in enumerate(images):
        expected_colour = colours[i]
        # convert to RGB tuple (int(hex_value, 16))
        expected_rgb = tuple(int(expected_colour[j:j+2], 16) for j in (1, 3, 5))
        actual_colour = img.getpixel((0,0))
        assert actual_colour == expected_rgb, \
            f"The image at position {i} has a wrong colour. Expected {expected_rgb}, got {actual_colour}"