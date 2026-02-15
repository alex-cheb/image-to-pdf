# Image to PDF Converter

A simple, user-friendly desktop application for converting multiple images into a single PDF document.

## Features

- **Drag and Add Images**: Select multiple images through a file dialog
- **Visual Preview**: View thumbnails of loaded images in an organized list
- **Reorder Images**: Move images up or down to arrange them in your desired order
- **Batch Conversion**: Convert all loaded images into a single PDF file
- **EXIF Orientation Support**: Automatically handles image rotation based on EXIF data
- **Multiple Format Support**: Works with JPG, JPEG, PNG, BMP, GIF, and TIFF files

## Requirements

- Python 3.10 or higher
- Dependencies listed in `pyproject.toml`

## Installation

1. Clone or download this repository

2. Create a virtual environment (recommended):
```bash
python -m venv .venv
```

3. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - macOS/Linux: `source .venv/bin/activate`

4. Install dependencies:
```bash
pip install -e .
```

Or install from requirements.txt:
```bash
pip install -r requirements.txt
```

**Note:** `pyproject.toml` is the source of truth for dependencies. To regenerate `requirements.txt`:
```bash
pip install pip-tools
pip-compile pyproject.toml -o requirements.txt
```

## Usage

Run the application:
```bash
python src/main.py
```

Or:
```bash
python -m src.main
```

### How to Use:

1. **Add Images**: Click the "Add Images" button to select image files from your computer
2. **Reorder** (optional): Select an image and use "Move Up ↑" or "Move Down ↓" buttons to change the order
3. **Create PDF**: Click "Create PDF" and choose where to save your output file
4. **Clear List** (optional): Remove all loaded images to start fresh

## Project Structure

```
.
├── src/
│   ├── core/
│   │   ├── image_loader.py    # Image validation and loading logic
│   │   └── pdf_builder.py     # PDF generation logic
│   ├── ui/
│   │   └── app_window.py      # Main GUI application
│   └── main.py                # Application entry point (to be implemented)
├── tests/
│   ├── test_image_loader.py   # Tests for image loading
│   └── test_pdf_builder.py    # Tests for PDF generation
├── pyproject.toml             # Project configuration and dependencies
├── requirements.txt           # Alternative dependency list
└── README.md                  # This file
```

## Development

### Running Tests

```bash
pytest tests/
```

### Known Issues

- Test files are currently empty and need implementation
- `src/main.py` entry point needs to be created
- Some error handling could be improved

## Dependencies

- **ttkbootstrap**: Modern themed tkinter widgets
- **Pillow**: Image processing and PDF generation
- **pytest**: Testing framework
- **tkinterdnd2**: Drag-and-drop support (optional)
- **loguru**: Logging utility (optional)

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Author

[Add author information here]
