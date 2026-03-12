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

### Image Management
**Status**: Complete

- **Add Images**: File dialog to select multiple images (`Ctrl+O`)
- **Delete Image**: Remove selected image from list (`Delete`)
- **Reorder Images**: Move images up/down in the list (`Ctrl+Up/Down`)
- **Rotate Image**: Rotate selected image 90° clockwise (`Ctrl+R`)
- **Clear List**: Remove all images at once (`Ctrl+C`)

### User Interface
**Status**: Complete

- **Main Window**: Clean, intuitive layout with toolbar and image list
- **Keyboard Shortcuts**: Full keyboard navigation support
  - `Ctrl+O`: Add Images
  - `Ctrl+S`: Create PDF  
  - `Ctrl+C`: Clear List
  - `Delete`: Remove selected image
  - `Ctrl+Up/Down`: Move image up/down
  - `Ctrl+R`: Rotate selected image
  - `Ctrl+Q`: Quit application
- **Tooltips**: Helpful hover text on all buttons
- **Status Bar**: Shows current image count and operation feedback

### PDF Generation
**Status**: Complete

- Generate single or multi-page PDFs from loaded images (`Ctrl+S`)
- Preserve image order and dimensions
- 150 DPI resolution metadata
- Error handling for empty image lists

### Image Preview
**Status**: Complete

- Full-size preview window (`PreviewDialog` class)
- Zoom in/out (+ / - keys)
- Ctrl + Mouse wheel zoom (smooth zooming from current view)
- Fit to window (F key)
- Actual size view (A key)
- Scrollable canvas for large images
- Close with Escape key

### Drag-and-Drop Support
**Status**: Complete

- Drag files directly onto the treeview to add them
- Cross-platform support (Windows, macOS, Linux)
- Handles both single and multiple file drops
- Parses Windows-style paths (with braces) and Unix-style paths
- Uses `tkinterdnd2` library
- Base class: `TkinterDnD.Tk` with manual ttkbootstrap theming
- **Graceful non-image file handling**: Silently skips non-image files, logs warnings

---

## Planned Features 📋

### Advanced Features (Future Versions)
**Priority**: Low  
**Effort**: Variable

- **Undo/Redo functionality**: Allow users to undo/redo operations
- **Batch image processing**: Apply transformations to multiple images at once
- **Custom page sizes**: Allow users to specify PDF page dimensions
- **Image compression settings**: Control output file size vs quality

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

### Logging Infrastructure
**Status**: Complete

- Loguru-based logging to `logs/app.log`
- 1 MB log rotation
- Automatic log directory creation
- Configured in `main.py` before app launch

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
- No undo/redo functionality
- No batch processing capabilities

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

### Why Ctrl+MouseWheel for Zoom?
- Prevents accidental zooming while scrolling through content
- Standard convention in many image viewers and browsers
- Leaves plain scroll wheel available for future scrolling features

### Why Standard Keyboard Shortcuts?
- `Ctrl+O` (Open), `Ctrl+S` (Save) follow universal conventions
- `Ctrl+C` for Clear is intuitive (though different from Copy)
- Arrow keys with Ctrl for reordering is common in list applications
- `Delete` key for removal is standard across most applications
