# Design Document: Image to PDF Converter

## Overview

This document outlines the architecture, design decisions, implemented features, and planned enhancements for the Image to PDF Converter project.

## Current Architecture

### Module Structure
```
src/
├── core/
│   ├── image_loader.py      # Image validation, loading, EXIF handling
│   └── pdf_builder.py       # PDF generation from PIL images
├── ui/
│   └── app_window.py        # Tkinter GUI with drag-and-drop support
└── main.py                  # Entry point with logging configuration
```

### Key Design Principles
- **Separation of Concerns**: Core logic (image/PDF operations) is independent of UI
- **PIL as Core**: All image processing uses Pillow (PIL) for consistency and reliability
- **No External State**: Images held in memory until PDF generation (no temporary files)
- **Testability**: Core modules are decoupled and fully tested via pytest + Hypothesis
- **Cross-platform**: Works on Windows, macOS, and Linux

---

## Implemented Features ✅

### Core Image Operations
**Status**: Complete

- Load multiple images via file dialog
- Support for JPG, JPEG, PNG, BMP, GIF, and TIFF formats
- Automatic EXIF orientation handling
- Automatic RGB conversion for PDF compatibility
- Thumbnail generation for list display

### PDF Generation
**Status**: Complete

- Generate single or multi-page PDFs from loaded images
- Preserve image order and dimensions
- 150 DPI resolution metadata
- Error handling for empty image lists

### Image Management
**Status**: Complete

- **Add Images**: File dialog to select multiple images
- **Delete Image**: Remove selected image from list
- **Reorder Images**: Move images up/down in the list
- **Rotate Image**: Rotate selected image 90° clockwise
- **Clear List**: Remove all images at once

### Image Preview
**Status**: Complete

- Full-size preview window (`PreviewDialog` class)
- Zoom in/out (+ / - keys)
- Ctrl + Mouse wheel zoom (smooth zooming from current view)
- Fit to window (F key)
- Actual size view (A key)
- Scrollable canvas for large images
- Close with Escape key
- Tooltips on all buttons for better UX

### Drag-and-Drop Support
**Status**: Complete

- Drag files directly onto the treeview to add them
- Cross-platform support (Windows, macOS, Linux)
- Handles both single and multiple file drops
- Parses Windows-style paths (with braces) and Unix-style paths
- Uses `tkinterdnd2` library
- Base class: `TkinterDnD.Tk` with manual ttkbootstrap theming

### Logging Infrastructure
**Status**: Complete

- Loguru-based logging to `logs/app.log`
- 1 MB log rotation
- Automatic log directory creation
- Configured in `main.py` before app launch

---

## Planned Features 📋

### Graceful Non-Image File Handling
**Priority**: Medium  
**Effort**: 2-3 hours

**Current Behavior**:
- Dropping non-image files via drag-and-drop shows an error dialog
- No files are added to the list (all-or-nothing approach)

**Desired Behavior**:
- **Single non-image file**: Silently ignored, no error dialog shown
- **Mixed files (images + non-images)**: 
  - Valid images are added to the list
  - Non-image files are silently skipped
  - Status bar shows: "X image(s) loaded (Y skipped)"
- **All non-image files**: No files added, status bar shows: "No valid images found"

**Implementation Plan**:

Add new function to `core/image_loader.py`:
```python
def add_images_lenient(paths: Iterable[Path]) -> tuple[List[Image.Image], List[Path]]:
    """
    Load images from paths, skipping invalid files instead of raising exceptions.
    
    Returns:
        tuple: (loaded_images, skipped_paths)
    """
    images = []
    skipped = []
    
    for raw_path in paths:
        path = Path(raw_path)
        if not path.is_file() or not _is_valid_image(path):
            skipped.append(path)
            continue
        
        try:
            img = Image.open(path)
            img = ImageOps.exif_transpose(img)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            images.append(img)
        except UnidentifiedImageError as e:
            logger.warning(f"Skipping corrupted file: {path}")
            skipped.append(path)
    
    return images, skipped
```

Update `on_drop_files()` in `ui/app_window.py` to use lenient loading.

**Testing**:
- Drop single non-image file → no error, no files added
- Drop mix of images and non-images → only images added, status shows count
- Drop only non-images → status shows "No valid images found"

---

### Keyboard Shortcuts for Main Window
**Priority**: Low  
**Effort**: 1-2 hours

**Desired Shortcuts**:
- `Ctrl+O`: Open file dialog (Add Images)
- `Ctrl+S`: Save as PDF (Create PDF)
- `Delete`: Remove selected image
- `Ctrl+Up/Down`: Move image up/down
- `Ctrl+R`: Rotate selected image
- `Ctrl+Q`: Quit application

---

## Technical Decisions

### Why tkinterdnd2?
- Cross-platform drag-and-drop support
- Integrates well with tkinter/ttkbootstrap
- Active maintenance and community support

### Why Not Built-in Size Control?
- Changing DPI metadata alone is misleading
- Automatic resampling adds complexity
- Users can resize images externally if needed
- Keeps the app focused and simple

### Why Loguru?
- Simple, elegant logging API
- Automatic log rotation
- No configuration boilerplate

### Why Property-Based Testing?
- Hypothesis generates hundreds of test cases automatically
- Catches edge cases that manual tests miss
- Validates properties across wide input ranges

### Why Ctrl+MouseWheel for Zoom?
- Prevents accidental zooming while scrolling through content
- Standard convention in many image viewers and browsers
- Leaves plain scroll wheel available for future scrolling features

---

## Testing Strategy

### Unit Tests ✅
- Test each core function in isolation
- Focus on business logic in `core/` modules
- Coverage: `test_image_loader.py`, `test_pdf_builder.py`

### Property-Based Tests ✅
- Use Hypothesis to generate random test cases
- Verify dimension preservation, order preservation, etc.
- Coverage: Property tests in `test_pdf_builder.py`

---

## Known Issues & Technical Debt

### Resolved ✅
- ~~No drag-and-drop support~~ → Implemented
- ~~No image preview~~ → Implemented
- ~~No logging~~ → Implemented

### Current
- Drag-and-drop shows errors for non-image files (planned fix)
- No keyboard shortcuts for main window (planned enhancement)
- No undo/redo functionality

---

## Dependencies

- **Python**: >=3.10
- **Pillow**: Image processing and PDF generation
- **ttkbootstrap**: Modern themed tkinter widgets
- **tkinterdnd2**: Cross-platform drag-and-drop
- **loguru**: Logging
- **pytest**: Testing framework
- **hypothesis**: Property-based testing
- **pypdf**: PDF validation

---

## Changelog

### Version 0.1.0 (Current)
- ✅ Core image loading with EXIF support
- ✅ Multi-page PDF generation
- ✅ Image management (add, delete, reorder, rotate)
- ✅ Image preview with zoom
- ✅ Drag-and-drop support
- ✅ Logging infrastructure
- ✅ Comprehensive test suite

### Version 0.2.0 (Planned)
- 📋 Graceful non-image file handling
- 📋 Keyboard shortcuts for main window

### Version 0.1.1 (Current - Minor Updates)
- ✅ Ctrl + Mouse wheel zoom in preview window
- ✅ Smooth zoom from fitted/current view (not from original size)
- ✅ Tooltips on all buttons
