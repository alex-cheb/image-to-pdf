"""
Image to PDF Converter - Main Entry Point
"""
from pathlib import Path
from ui.app_window import ImageToPdfApp
from loguru import logger



def main():
    """Launch the Image to PDF Converter application."""
    Path("logs").mkdir(exist_ok=True)
    logger.configure(handlers=[{"sink": "logs/app.log", 
        "rotation": "1 MB", 
        "level":"DEBUG"}])

    app = ImageToPdfApp()
    app.mainloop()


if __name__ == "__main__":
    main()
