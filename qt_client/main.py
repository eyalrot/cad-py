#!/usr/bin/env python3
"""Main entry point for PyCAD Qt6 application."""

import logging
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from PySide6.QtCore import QSettings, Qt
    from PySide6.QtGui import QIcon, QPixmap
    from PySide6.QtWidgets import QApplication, QMessageBox
except ImportError:
    print("PySide6 is not installed. Please install it with: pip install PySide6")
    sys.exit(1)

from qt_client.core.application import CADApplication
from qt_client.ui.main_window import CADMainWindow


def setup_logging():
    """Setup application logging."""
    log_dir = Path.home() / ".pycad" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_dir / "pycad.log"), logging.StreamHandler()],
    )


def setup_qt_application():
    """Setup Qt application with proper settings."""
    # Enable high DPI scaling
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("PyCAD 2D Professional")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("CAD-PY")
    app.setOrganizationDomain("cad-py.org")

    # Set application icon
    # app.setWindowIcon(QIcon(":/icons/app_icon.png"))

    return app


def main():
    """Main application entry point."""
    try:
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Starting PyCAD Qt6 application")

        # Create Qt application
        qt_app = setup_qt_application()

        # Create CAD application
        cad_app = CADApplication()

        # Create and show main window
        main_window = CADMainWindow(cad_app)
        main_window.show()

        # Center window on screen
        main_window.center_on_screen()

        logger.info("PyCAD application started successfully")

        # Run application
        return qt_app.exec()

    except Exception as e:
        error_msg = f"Failed to start PyCAD application: {str(e)}"
        logging.error(error_msg, exc_info=True)

        # Show error dialog if Qt is available
        try:
            if "qt_app" in locals():
                QMessageBox.critical(None, "PyCAD Error", error_msg)
        except:
            pass

        return 1


if __name__ == "__main__":
    sys.exit(main())
