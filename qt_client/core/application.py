"""Core CAD application logic."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtWidgets import QMessageBox

logger = logging.getLogger(__name__)


class CADApplication(QObject):
    """Core CAD application managing documents and global state."""

    # Signals
    document_opened = Signal(str)  # document_id
    document_closed = Signal(str)  # document_id
    current_document_changed = Signal(str)  # document_id
    settings_changed = Signal()

    def __init__(self):
        super().__init__()

        # Application state
        self._current_document_id: Optional[str] = None
        self._recent_files: list[str] = []
        self._settings = QSettings()

        # Load settings
        self._load_settings()

        logger.info("CAD application initialized")

    @property
    def current_document_id(self) -> Optional[str]:
        """Get current document ID."""
        return self._current_document_id

    @property
    def recent_files(self) -> list[str]:
        """Get list of recent files."""
        return self._recent_files.copy()

    def _load_settings(self):
        """Load application settings."""
        try:
            # Load recent files
            self._recent_files = self._settings.value("recent_files", [], type=list)

            # Validate recent files exist
            self._recent_files = [f for f in self._recent_files if Path(f).exists()][
                :10
            ]  # Keep only last 10 existing files

            logger.info(f"Loaded {len(self._recent_files)} recent files")

        except Exception as e:
            logger.warning(f"Error loading settings: {e}")
            self._recent_files = []

    def _save_settings(self):
        """Save application settings."""
        try:
            self._settings.setValue("recent_files", self._recent_files)
            self._settings.sync()
            logger.debug("Settings saved")
        except Exception as e:
            logger.warning(f"Error saving settings: {e}")

    def add_recent_file(self, file_path: str):
        """Add file to recent files list."""
        file_path = str(Path(file_path).resolve())

        # Remove if already in list
        if file_path in self._recent_files:
            self._recent_files.remove(file_path)

        # Add to beginning
        self._recent_files.insert(0, file_path)

        # Keep only last 10
        self._recent_files = self._recent_files[:10]

        # Save settings
        self._save_settings()
        self.settings_changed.emit()

    def clear_recent_files(self):
        """Clear recent files list."""
        self._recent_files.clear()
        self._save_settings()
        self.settings_changed.emit()

    def set_current_document(self, document_id: Optional[str]):
        """Set current document."""
        if self._current_document_id != document_id:
            old_id = self._current_document_id
            self._current_document_id = document_id

            logger.info(f"Current document changed: {old_id} -> {document_id}")
            self.current_document_changed.emit(document_id or "")

    def new_document(self, name: str = "Untitled") -> bool:
        """Create a new document."""
        try:
            # TODO: Call gRPC service to create document
            document_id = f"doc_{len(self._recent_files) + 1}"  # Mock ID

            self.set_current_document(document_id)
            self.document_opened.emit(document_id)

            logger.info(f"Created new document: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create new document: {e}")
            self._show_error("Failed to create new document", str(e))
            return False

    def open_document(self, file_path: str) -> bool:
        """Open an existing document."""
        try:
            file_path = str(Path(file_path).resolve())

            if not Path(file_path).exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            # TODO: Call gRPC service to load document
            document_id = f"doc_{Path(file_path).stem}"  # Mock ID

            self.set_current_document(document_id)
            self.add_recent_file(file_path)
            self.document_opened.emit(document_id)

            logger.info(f"Opened document: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to open document {file_path}: {e}")
            self._show_error("Failed to open document", str(e))
            return False

    def save_document(self, file_path: Optional[str] = None) -> bool:
        """Save current document."""
        try:
            if not self._current_document_id:
                raise ValueError("No document is currently open")

            if not file_path:
                # TODO: Get current document file path
                file_path = f"untitled_{self._current_document_id}.cad"

            # TODO: Call gRPC service to save document

            self.add_recent_file(file_path)

            logger.info(f"Saved document: {file_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save document: {e}")
            self._show_error("Failed to save document", str(e))
            return False

    def close_document(self) -> bool:
        """Close current document."""
        try:
            if not self._current_document_id:
                return True

            # TODO: Check for unsaved changes

            old_id = self._current_document_id
            self.set_current_document(None)
            self.document_closed.emit(old_id)

            logger.info(f"Closed document: {old_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to close document: {e}")
            self._show_error("Failed to close document", str(e))
            return False

    def exit_application(self) -> bool:
        """Exit the application."""
        try:
            # Close current document
            if not self.close_document():
                return False

            # Save settings
            self._save_settings()

            logger.info("Application exiting")
            return True

        except Exception as e:
            logger.error(f"Error during application exit: {e}")
            return False

    def _show_error(self, title: str, message: str):
        """Show error message to user."""
        try:
            QMessageBox.critical(None, title, message)
        except Exception as e:
            logger.error(f"Failed to show error dialog: {e}")

    def get_setting(self, key: str, default_value: Any = None) -> Any:
        """Get application setting."""
        return self._settings.value(key, default_value)

    def set_setting(self, key: str, value: Any):
        """Set application setting."""
        self._settings.setValue(key, value)
        self._settings.sync()
        self.settings_changed.emit()
