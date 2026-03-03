# Design Document: Image to PDF Converter

## Overview

This document outlines the architecture, design decisions, and planned features for the Image to PDF Converter project.

## Current Architecture

### Module Structure
```
src/
├── core/
│   ├── image_loader.py      # Image validation, loading, EXIF handling
│   └── pdf_builder.py       # PDF generation from PIL images
├── ui/
│   └── app_window.py        # Tkinter GUI (ttkbootstrap themed)
└── main.py                  # Entry point
```

### Key Design Principles
- **Separation of Concerns**: Core logic (image/PDF operations) is independent of UI
- **PIL as Core**: All image processing uses Pillow (PIL) for consistency and reliability
- **No External State**: Images held in memory until PDF generation (no temporary files)
- **Testability**: Core modules are decoupled and fully tested via pytest

---

## Stage 1: Core Features (Phase 1 – completed)

### 1.1 Delete Individual Images

**Requirement**: allow users to remove a single image from the list without
clearing the entire set.

**Design**:
- "Delete" button in the side panel alongside the move and rotate controls
- Command is inert when nothing is selected
- Deletion updates both the underlying `self.loaded_images` list and the
  `Treeview` widget, and keeps the thumbnail reference map in sync
- Status bar always reflects the current count

*This feature has been implemented in Phase 1 and is exercised by the
existing test suite.*

**Testing**:
- Test delete at start, middle, end of list
- Test status bar updates
- Test with selected/unselected state

---

### 1.2 Decision: No Built-in Size Control (Keep App Minimal)

After consideration, the project will not include an image-size/quality control in the UI. Changing DPI metadata alone is misleading (it does not change pixel data), and automatic resampling adds complexity that users can perform themselves (e.g., in an image editor) if desired.

Implications:
- Remove any plan to add presets for automatic resizing from the immediate roadmap.
- Keep the app focused on straightforward workflows: add images, reorder, delete, preview (TBD), and generate PDFs.

Remaining feature priorities:
- `Delete image` — implemented.
- `Preview` — design and implementation to be considered later; leave as an optional enhancement.
- `Drag-and-drop` — valuable UX improvement; plan for Stage 2 when ready.

Notes for future work (if reintroduced):
- If automatic resizing is later desired, prefer an explicit `scale` parameter (e.g., 0.5, 0.25) with clear UI labels and UX warnings about quality change. Avoid implying that changing DPI metadata alone will improve or reduce perceived quality.

This keeps the current product simple and predictable for users.

---

### 1.3 Image Preview Dialog

**Requirement**: Show full-size preview of selected image before PDF generation.

**Design**:
- Add "Preview" button in side panel
- Opens new window with full image display
- Window is resizable and has basic fit-to-window scaling
- Keyboard support: Esc to close, arrow keys to navigate

**Implementation Details**:

*In ui/app_window.py, add new method*:
```python
def on_preview_image(self):
    """Open a preview window for the selected image."""
    selected = self.imgs_tree.selection()
    if not selected:
        messagebox.showwarning("No Selection", "Please select an image to preview.")
        return
    
    item = selected[0]
    children = self.imgs_tree.get_children()
    index = children.index(item)
    pil_image = self.loaded_images[index]
    
    # Create preview window
    preview_win = tk.Toplevel(self)
    preview_win.title(f"Image Preview - {index + 1}/{len(self.loaded_images)}")
    preview_win.geometry("600x600")
    
    # Convert PIL image to PhotoImage for display
    display_img = pil_image.copy()
    # Scale to fit window (preserve aspect ratio)
    display_img.thumbnail((600, 600), Image.Resampling.LANCZOS)
    tk_image = ImageTk.PhotoImage(display_img)
    
    canvas = tk.Canvas(preview_win, bg="gray20")
    canvas.pack(fill=tk.BOTH, expand=True)
    canvas.create_image(300, 300, image=tk_image)
    canvas.image = tk_image  # Keep reference
    
    # Close on Escape
    preview_win.bind('<Escape>', lambda e: preview_win.destroy())
```

**Testing**:
- Test preview window opens with correct image
- Test image scaling for various aspect ratios
- Test window close behavior

---

## Stage 2: Advanced Features (Phase 2)

### 2.1 Drag-and-Drop Support

**Requirement**: Allow users to drag image files directly onto the application window to add them.

**Design**:
- Use `tkinterdnd2` (already in dependencies) for drag-and-drop
- Accept drops on main treeview widget
- Validate dropped files using existing `add_images()` function
- Integrate with existing thumbnail generation pipeline

**Implementation Details**:

*In ui/app_window.py*:
```python
from tkinterdnd2 import DND_FILES, DND_TEXT

# In create_widgets(), after treeview creation
try:
    self.imgs_tree.drop_target_register(DND_FILES)
    self.imgs_tree.dnd_bind('<<Drop>>', self.on_drop_files)
except Exception as e:
    logger.warning(f"Drag-and-drop not available: {e}")

def on_drop_files(self, event):
    """Handle dropped files via drag-and-drop."""
    # event.data contains dropped files (may have braces on Windows)
    dropped = event.data.replace('{', '').replace('}', '')
    file_paths = dropped.split() if ' ' in dropped else [dropped]
    
    try:
        new_imgs = add_images(file_paths)
        # Reuse existing add logic: thumbnails, tree insertion, etc.
        self._add_images_to_list(file_paths, new_imgs)
    except Exception as exc:
        messagebox.showerror("Error", f"Failed to load dropped images:\n{exc}")

def _add_images_to_list(self, file_paths, new_imgs):
    """Shared logic for adding images (from dialog or drag-drop)."""
    self.loaded_images.extend(new_imgs)
    for path_str, pil_img in zip(file_paths, new_imgs):
        # [existing thumbnail + tree insertion code]
    self.status.config(text=f"{len(self.loaded_images)} image(s) loaded.")
```

**Considerations**:
- Drag-and-drop may not work on all systems (warning in logs)
- Use try-except to gracefully degrade
- Extract thumbnail logic into `_add_images_to_list()` to avoid code duplication

**Testing**:
- Test drag-drop with single and multiple files
- Test error handling for mixed file types
- Test on Windows/Linux (may vary by platform)

---

## Stage 3: Testing & Validation

### 3.1 Test Coverage for New Features

**Unit Tests** (in `tests/test_ui_features.py`):

```python
"""Tests for new UI features"""
import pytest
from unittest.mock import patch, MagicMock
from PIL import Image
from pathlib import Path

def test_delete_image_from_list(tmp_image_dir):
    """Verify single image deletion works correctly."""
    # Create mock app, add 3 images, delete middle one
    # Assert correct image removed from both list and UI

def test_delete_nonexistent_image():
    """Verify delete handles no selection gracefully."""
    # Mock app with no selection
    # Assert warning shown, list unchanged

def test_quality_resolution_parameter(tmp_image_dir, tmp_pdf_dir):
    """Verify different resolutions produce different file sizes."""
    # Generate PDFs at 72, 150, 300 DPI
    # Assert file sizes: 72 < 150 < 300 (approximately)

def test_preview_window_creates_correct_image(sample_rgb_image):
    """Verify preview window displays correct image."""
    # Mock Tk window, call on_preview_image()
    # Assert PhotoImage created with correct dimensions

def test_drag_drop_multiple_images(tmp_image_dir):
    """Verify drag-drop adds multiple files."""
    # Mock DND event with multiple file paths
    # Assert all images added to list

def test_drag_drop_invalid_file():
    """Verify drag-drop handles unsupported files gracefully."""
    # Mock DND with mixed valid/invalid files
    # Assert error shown, valid files added
```

**Integration Tests**:

```python
def test_end_to_end_delete_and_generate_pdf(tmp_image_dir, tmp_pdf_dir):
    """Test workflow: add 5 images, delete 2, generate PDF with remaining."""
    # Add 5 images
    # Delete images at index 1 and 3
    # Generate PDF
    # Assert PDF has 3 pages

def test_quality_setting_affects_pdf_size(tmp_image_dir, tmp_pdf_dir):
    """Verify quality combobox value affects output PDF."""
    # Set quality to "72 (Low)"
    # Generate PDF, measure size
    # Set quality to "300 (High)"
    # Generate PDF, measure size
    # Assert high-quality PDF is larger
```

**Test Fixtures** (add to `tests/conftest.py`):

```python
@pytest.fixture
def mock_app_window():
    """Create a mock ImageToPdfApp for testing without GUI."""
    # Return mock with necessary attributes
    pass

@pytest.fixture
def sample_dnd_event():
    """Create mock drag-and-drop event."""
    # Return event with .data attribute containing file paths
    pass
```

---

## Implementation Roadmap

| Feature | Priority | Est. Effort | Dependencies | Timeline |
|---------|----------|-------------|--------------|----------|
| Delete Images | High | 1-2 hours | None | Phase 1 Week 1 |
| Quality Settings | High | 2-3 hours | None | Phase 1 Week 1 |
| Preview Dialog | Medium | 3-4 hours | None | Phase 1 Week 2 |
| Drag-n-Drop | Medium | 4-6 hours | tkinterdnd2 | Phase 2 Week 3-4 |
| Tests (All Features) | High | 6-8 hours | All above | Phase 3 Week 5 |

---

## Testing Strategy

### Unit Tests
- Test each new method in isolation
- Use mocks for UI components
- Focus on business logic in `core/` modules

### Integration Tests
- Test feature workflows (e.g., quality setting → PDF generation)
- Use temporary directories for file operations
- Validate PDF output structure via `pypdf`

### Property-Based Tests (Hypothesis)
- Test delete with random list sizes
- Test quality settings with various image dimensions
- Verify preview scaling works for edge-case aspect ratios

### Manual Testing Checklist
- [ ] Delete image at start, middle, end of list
- [ ] Preview with various image formats and sizes
- [ ] Quality setting actually affects PDF file size
- [ ] Drag-drop works with mixed file types
- [ ] Drag-drop with invalid files shows error gracefully
- [ ] All buttons enable/disable correctly based on selection state

---

## Future Considerations

- **Batch operations**: Rotate all, flip all, apply filters to all
- **Undo/Redo**: Maintain change history
- **Watermarking**: Add text or image watermarks to PDF
- **Compression**: Further optimize PDF file size
- **Multi-page PDF merge**: Merge multiple PDFs into one
- **Rename images in list**: For better organization before PDF creation
- **Export to image formats**: Save individual pages as images
- **Accessibility**: Keyboard shortcuts, screen reader support

---

## Technical Debt & Known Issues

- `src/main.py` entry point not used (app launched directly from `src/ui/app_window.py`)
- Error handling could distinguish between recoverable and fatal errors
- No logging beyond loguru setup in `core/image_loader.py`
- UI tests currently non-existent (Stage 3 addresses this)

---

## References

- [PIL/Pillow Documentation](https://pillow.readthedocs.io/)
- [tkinterdnd2 Wiki](https://github.com/pmgagne/tkinterdnd2)
- [ttkbootstrap Docs](https://ttkbootstrap.readthedocs.io/)
- [Hypothesis Testing](https://hypothesis.readthedocs.io/)
- [pypdf Documentation](https://pypdf.readthedocs.io/)
