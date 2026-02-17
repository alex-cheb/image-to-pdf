import pytest
import tempfile
from pathlib import Path
from hypothesis import given, settings, strategies as st
from PIL import Image
from tests.test_helpers import *
from core import image_loader, pdf_builder


def test_create_single_page_pdf(tmp_image_dir, tmp_pdf_dir):
    """
    Verifies the single-page pdf is created in the expected path
    Requirements: 3.1, 3.3
    """
    image_path = tmp_image_dir/f'test.jpg'
    create_sample_rgb_image(image_path, (100, 100),'#FF0000', 'JPEG')
    images = image_loader.add_images([image_path])
    pdf_path = tmp_pdf_dir/f'test.pdf'
    pdf_builder.build_pdf(images, pdf_path)
    assert pdf_path.exists() and pdf_path.is_file(), f"The expected file was not created at {pdf_path}"
    assert get_page_count(pdf_path) == 1, f"Expected a single-page document, but got {get_page_count(pdf_path)} pages"


def test_create_multiple_page_pdf(tmp_image_dir, tmp_pdf_dir):
    """
    Verifies the multiple page pdf is created from multiple images
    Requirements: 3.3, 3.4
    """
    image_paths = []
    page_count = 3
    for i in range(page_count):
        image_path = tmp_image_dir/f'test_{i}.jpg'
        create_sample_rgb_image(image_path, (100, 100),'#FF0000', 'JPEG')
        image_paths.append(image_path)
    images = image_loader.add_images(image_paths)
    assert len(images) == page_count, f"Incorrect quantity of the images in the initial list."
    pdf_path = tmp_pdf_dir/f'test.pdf'
    pdf_builder.build_pdf(images, pdf_path)
    assert pdf_path.exists() and pdf_path.is_file(), f"The expected file was not created at {pdf_path}"
    assert get_page_count(pdf_path) == page_count, \
        f"Expected a {page_count}-page document, but got {get_page_count(pdf_path)} pages"


def test_builder_handles_empty_list(tmp_pdf_dir):
    """
    Verifies that the builder handles properly an empty list
    Requirements: 4.1
    """
    path = tmp_pdf_dir / 'test.pdf'
    with pytest.raises(ValueError, match="No images provided to build the PDF."):
        pdf_builder.build_pdf([], path)

# Feature: test-suite, Property 5: PDF creation from images
# Feature: test-suite, Property 7: multi-page PDF generation
@settings(deadline=None)
@pytest.mark.property
@given(st.lists(
    st.tuples(
        st.integers(min_value=1,max_value=500), # width
        st.integers(min_value=1,max_value=500) # height
    ),
    min_size=1,
    max_size=10,
))
def test_property_pdf_creation(img_sizes):
    """
    Property based test for non-empty list of PIL
    images; build_pdf should create a PDF file
    Requirements: 3.1, 3.4
    """
    images = [Image.new('RGB', size, color='#00FF00') for size in img_sizes]

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / 'test.pdf'

        pdf_builder.build_pdf(images, path)
        assert path.exists(), f"PDF was not created in {path}"
        assert path.is_file(), f"Output path {path} is not a file."
        assert get_page_count(path) == len(images), f"The quantity of images does not correspond to the dpf pages quantity"


# Feature: test-suite, Property 6: preserving pages order
@settings(deadline=None)
@pytest.mark.property
@given(st.lists(
    st.integers(min_value=0,max_value=255),
    min_size=2,
    max_size=10,
))
def test_property_pdf_creation_image_order_preserved(color_values):
    """
    Property based test to verify order of images in pdf
    Requirements: 3.2
    """
    images = []
    for i, val in enumerate(color_values):
        colour = (val,val,val)
        img = Image.new('RGB', (10,10), color=colour)
        images.append(img)

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / 'test.pdf'

        pdf_builder.build_pdf(images, path)
        for page_num, original_img in enumerate(images):
            extracted = extract_image(path, page_num)
            assert extracted is not None, f"Was unable to extract {page_num}"
            assert_images_similar(original_img, extracted, threshold=1.0)


# Feature: test-suite, Property 8: preserving image dimensions
@settings(deadline=None)
@pytest.mark.property
@given(st.lists(
    st.tuples(
        st.integers(min_value=1,max_value=500), # width
        st.integers(min_value=1,max_value=500) # height
    ),
    min_size=1,
    max_size=10,
))
def test_property_pdf_pages_dimensions_preserved(img_sizes):
    """
    Property based test to verify that page dimensions correspond to 
    those of the original images
    Requirements: 6.1
    """
    images = [Image.new('RGB', size, color='#00FF00') for size in img_sizes]

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = Path(tmp_dir) / 'test.pdf'

        pdf_builder.build_pdf(images, path)
        for page_num, original_img in enumerate(images):
            extracted = extract_image(path, page_num)
            assert extracted is not None, f"Was unable to extract {page_num}"
            assert extracted.size == original_img.size,\
             f"The imaze sizes are not preserved: original ({original_img.size}) ≠ pdf page size {extracted.size}"
