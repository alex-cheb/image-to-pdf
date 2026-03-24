# Image to PDF Converter

A simple, user-friendly desktop application for converting multiple images into a single PDF document with optimized performance and security.

## Features

### Core Functionality
- **Drag-and-Drop Support**: Drag image files directly onto the application window (gracefully skips non-image files)
- **Add Images**: Select multiple images through a file dialog (`Ctrl+O`)
- **Visual Preview**: View thumbnails of loaded images in an organized list with full-size preview
- **Image Management**: Delete (`Delete`), reorder (`Ctrl+Up/Down`), and rotate (`Ctrl+R`) images
- **Batch Conversion**: Convert all loaded images into a single PDF file (`Ctrl+S`)
- **EXIF Orientation Support**: Automatically handles image rotation based on EXIF data
- **Multiple Format Support**: Works with JPG, JPEG, PNG, BMP, GIF, and TIFF files
- **Keyboard Shortcuts**: Full keyboard navigation for all operations
- **Logging**: Automatic logging to `logs/app.log` with rotation

### Performance Optimizations (v0.4.0)
- **Async Thumbnail Generation**: Non-blocking UI when loading multiple large images - thumbnails generate in background threads
- **Optimized Preview Zoom**: Intelligent caching and fast resampling for smooth zoom operations
  - Zoom cache stores up to 10 zoom levels for instant recall
  - Fast BILINEAR resampling for high zoom levels (>2.0x)
  - High-quality LANCZOS resampling for normal zoom levels
  - 50ms debounce prevents excessive zoom operations
- **Responsive UI**: No freezing when loading large image sets

### Security & Validation (v0.3.0)
- **Path Validation**: Protection against path traversal attacks
- **File Size Limits**: 50MB maximum file size to prevent DoS attacks
- **Dimension Limits**: 15,000×15,000 pixel maximum to prevent memory exhaustion
- **Input Sanitization**: Comprehensive validation of all file paths and image data
- **Memory Leak Prevention**: Proper resource cleanup in preview dialogs

## Requirements

- Python 3.10 or higher
- Dependencies listed in `pyproject.toml`

## Performance Characteristics

- **Thumbnail Generation**: Non-blocking, < 200ms per thumbnail in background threads
- **Zoom Operations**: < 100ms response time with caching, smooth interaction
- **Large Image Support**: Handles images up to 15,000×15,000 pixels and 50MB safely
- **Memory Management**: Controlled zoom cache (max 10 levels), no memory leaks
- **Concurrent Processing**: Up to 4 background threads for thumbnail generation

## Installation

1. Clone or download this repository

2. Create a virtual environment (recommended):
```bash
python -m venv .venv
```

3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`

4. Install dependencies from `pyproject.toml`:
```bash
pip install -e .
```

**Fallback option:** If you prefer to use a `requirements.txt` file, you can generate it from `pyproject.toml`:
```bash
pip install pip-tools
pip-compile pyproject.toml -o requirements.txt
pip install -r requirements.txt
```

## Usage

Run the application:
```bash
python src/main.py
```

Or use the CLI entry point:
```bash
pdf-maker
```

### How to Use:

1. **Add Images**: 
   - Click the "Add Images" button (`Ctrl+O`) to select image files, OR
   - Drag and drop image files directly onto the window
2. **Preview**: Double-click any image to view it full-size with zoom controls (`Ctrl+MouseWheel`)
3. **Manage Images** (optional):
   - **Rotate**: Select an image and click "Rotate" (`Ctrl+R`) to rotate 90° clockwise
   - **Reorder**: Use "Move Up ↑" (`Ctrl+Up`) or "Move Down ↓" (`Ctrl+Down`) buttons to change the order
   - **Delete**: Remove selected image (`Delete`) from the list
   - **Clear List**: Remove all loaded images (`Ctrl+C`) to start fresh
4. **Create PDF**: Click "Create PDF" (`Ctrl+S`) and choose where to save your output file
5. **Quit**: Press `Ctrl+Q` to exit the application

### Keyboard Shortcuts:

**Main Window:**
- `Ctrl+O`: Add Images
- `Ctrl+S`: Create PDF
- `Ctrl+C`: Clear List
- `Delete`: Remove selected image
- `Ctrl+Up/Down`: Move image up/down
- `Ctrl+R`: Rotate selected image
- `Ctrl+Q`: Quit application

**Preview Window:**
- `F`: Fit to window
- `A`: Actual size (100%)
- `+/-`: Zoom in/out
- `Ctrl+MouseWheel`: Zoom in/out
- `Esc`: Close preview

## Project Structure

```
.
├── src/
│   ├── core/
│   │   ├── image_loader.py    # Image validation and loading logic
│   │   └── pdf_builder.py     # PDF generation logic
│   ├── ui/
│   │   └── app_window.py      # Main GUI application with drag-and-drop
│   └── main.py                # Application entry point with logging setup
├── tests/
│   ├── test_image_loader.py   # Tests for image loading
│   ├── test_pdf_builder.py    # Tests for PDF generation
│   ├── test_helpers.py        # Test utility functions
│   └── conftest.py            # Shared pytest fixtures
├── logs/
│   └── app.log                # Application logs (auto-created)
├── pyproject.toml             # Project configuration and dependencies
├── pytest.ini                 # Test configuration
├── DESIGN.md                  # Architecture and design decisions
└── README.md                  # This file
```

## Development

### Running Tests

The project includes a comprehensive test suite with both unit tests and property-based tests using Hypothesis.

**Run all tests:**
```bash
pytest
```

**Run with verbose output:**
```bash
pytest -v
```

**Run with coverage reporting:**
```bash
pytest --cov=src --cov-report=html --cov-report=term
```

This will generate:
- Terminal coverage report showing line coverage percentages
- HTML coverage report in `htmlcov/` directory (open `htmlcov/index.html` in a browser)

**Run specific test files:**
```bash
# Test image loading module
pytest tests/test_image_loader.py

# Test PDF generation module
pytest tests/test_pdf_builder.py

# Run with verbose output for a specific file
pytest -v tests/test_image_loader.py
```

**Run specific test categories:**
```bash
# Run only property-based tests
pytest -m property

# Run only unit tests (if marked)
pytest -m unit
```

**Property-Based Testing:**

The test suite uses [Hypothesis](https://hypothesis.readthedocs.io/) for property-based testing, which automatically generates hundreds of test cases to verify that correctness properties hold across a wide range of inputs. 

Property tests validate universal behaviors such as:
- Image count preservation during loading
- RGB mode conversion for all color modes
- Dimension preservation in PDFs
- Image order preservation
- Multi-page PDF generation

Each property test runs a minimum of 100 iterations with randomly generated test data.

**Test Structure:**
- `tests/test_image_loader.py` - Unit and property tests for image loading
- `tests/test_pdf_builder.py` - Unit and property tests for PDF generation
- `tests/test_helpers.py` - Utility functions for creating test images and validating PDFs
- `tests/conftest.py` - Shared pytest fixtures (temp directories, sample images)
- `pytest.ini` - Test configuration and markers

**Coverage Goals:**
- Line coverage: 90%+ for core modules
- Branch coverage: 85%+ for error handling
- All 13 correctness properties have corresponding property-based tests

## Roadmap & Architecture

See [DESIGN.md](DESIGN.md) for:
- Detailed architecture and design decisions
- Current implementation status (v0.4.0 - Performance Optimizations complete)
- Phase 1 (v0.3.0): Security & Performance Hardening ✅
- Phase 2 (v0.4.0): Performance Optimizations ✅
- Phase 3: Code Quality & Security (planned)
- Technical decisions and rationale
- Testing strategy and coverage goals

### Version History

**v0.4.0 - Performance Optimizations** (Current)
- Async thumbnail generation with background threads
- Optimized preview zoom with caching and fast resampling
- Non-blocking UI for large image sets
- Improved responsiveness and user experience

**v0.3.0 - Security & Performance Hardening**
- Path validation and security hardening
- File size and dimension limits
- Memory leak prevention
- Comprehensive input validation

**v0.2.0 - UI Enhancements**
- Drag-and-drop support
- Keyboard shortcuts
- Preview dialog with zoom
- Tooltips and improved UX

**v0.1.0 - Initial Release**
- Core image to PDF conversion
- Basic UI with image management
- EXIF orientation support

### Known Issues

- No undo/redo functionality
- No batch processing capabilities

## Dependencies

- **Pillow**: Image processing and PDF generation
- **ttkbootstrap**: Modern themed tkinter widgets
- **tkinterdnd2**: Cross-platform drag-and-drop support
- **loguru**: Logging with automatic rotation
- **pytest**: Testing framework
- **hypothesis**: Property-based testing framework
- **pypdf**: PDF reading and validation for tests
- **psutil**: System and process utilities for performance monitoring

All threading and concurrency features use Python's built-in `concurrent.futures` and `threading` modules (no external dependencies).

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Author

[Add author information here]
