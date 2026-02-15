"""
Image to PDF Converter - Main Entry Point
"""
from ui.app_window import ImageToPdfApp


def main():
    """Launch the Image to PDF Converter application."""
    app = ImageToPdfApp()
    app.mainloop()


if __name__ == "__main__":
    main()
