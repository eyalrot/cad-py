"""Export options dialog for CAD documents."""

import asyncio
import logging
from typing import Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QLineEdit,
    QPushButton,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QProgressBar,
    QTextEdit,
    QTabWidget,
    QWidget,
    QMessageBox,
    QSplitter
)

logger = logging.getLogger(__name__)


class ExportOptionsDialog(QDialog):
    """Dialog for configuring export options."""

    export_requested = Signal(str, str, dict)  # file_path, format, options

    def __init__(self, api_client, document_id: str, parent=None):
        super().__init__(parent)
        self.api_client = api_client
        self.document_id = document_id
        self.supported_formats = []
        self.current_format = ""
        self.export_options = {}

        self.setWindowTitle("Export Document")
        self.setModal(True)
        self.resize(600, 500)

        self._setup_ui()
        self._load_supported_formats()

    def _setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Create main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # Left side - Options
        options_widget = QWidget()
        options_layout = QVBoxLayout(options_widget)

        # File selection group
        file_group = QGroupBox("Export File")
        file_layout = QFormLayout(file_group)

        self.file_path_edit = QLineEdit()
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self._browse_file)

        file_path_layout = QHBoxLayout()
        file_path_layout.addWidget(self.file_path_edit)
        file_path_layout.addWidget(self.browse_button)

        self.format_combo = QComboBox()
        self.format_combo.currentTextChanged.connect(self._on_format_changed)

        file_layout.addRow("File Path:", file_path_layout)
        file_layout.addRow("Format:", self.format_combo)

        options_layout.addWidget(file_group)

        # Create tabs for different option categories
        self.options_tabs = QTabWidget()
        options_layout.addWidget(self.options_tabs)

        # General options tab
        self._create_general_options_tab()

        # Page options tab
        self._create_page_options_tab()

        # Quality options tab
        self._create_quality_options_tab()

        # Format-specific options tab
        self._create_format_options_tab()

        splitter.addWidget(options_widget)

        # Right side - Preview
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        preview_label = QLabel("Export Preview")
        preview_label.setStyleSheet("font-weight: bold;")
        preview_layout.addWidget(preview_label)

        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setMaximumHeight(200)
        preview_layout.addWidget(self.preview_text)

        # Preview refresh button
        self.refresh_preview_button = QPushButton("Refresh Preview")
        self.refresh_preview_button.clicked.connect(self._refresh_preview)
        preview_layout.addWidget(self.refresh_preview_button)

        splitter.addWidget(preview_widget)
        splitter.setSizes([400, 200])

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._export_document)
        button_box.rejected.connect(self.reject)

        self.export_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.export_button.setText("Export")
        self.export_button.setEnabled(False)

        layout.addWidget(button_box)

    def _create_general_options_tab(self):
        """Create general options tab."""
        widget = QWidget()
        layout = QFormLayout(widget)

        # Layer options
        layer_group = QGroupBox("Layer Options")
        layer_layout = QFormLayout(layer_group)

        self.include_layers_edit = QLineEdit()
        self.include_layers_edit.setPlaceholderText("Leave empty for all layers")
        self.exclude_layers_edit = QLineEdit()
        self.exclude_layers_edit.setPlaceholderText("Comma-separated layer names")

        layer_layout.addRow("Include Layers:", self.include_layers_edit)
        layer_layout.addRow("Exclude Layers:", self.exclude_layers_edit)

        layout.addRow(layer_group)

        # Scale options
        self.scale_factor_spin = QDoubleSpinBox()
        self.scale_factor_spin.setRange(0.1, 10.0)
        self.scale_factor_spin.setValue(1.0)
        self.scale_factor_spin.setSingleStep(0.1)
        self.scale_factor_spin.setDecimals(2)

        layout.addRow("Scale Factor:", self.scale_factor_spin)

        self.options_tabs.addTab(widget, "General")

    def _create_page_options_tab(self):
        """Create page options tab."""
        widget = QWidget()
        layout = QFormLayout(widget)

        # Page size
        self.page_size_combo = QComboBox()
        self.page_size_combo.addItems(["A4", "A3", "A2", "A1", "A0", "LETTER", "LEGAL", "CUSTOM"])
        self.page_size_combo.currentTextChanged.connect(self._on_page_size_changed)
        layout.addRow("Page Size:", self.page_size_combo)

        # Orientation
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["portrait", "landscape"])
        layout.addRow("Orientation:", self.orientation_combo)

        # Custom dimensions (initially hidden)
        self.custom_width_spin = QDoubleSpinBox()
        self.custom_width_spin.setRange(10, 2000)
        self.custom_width_spin.setValue(210)
        self.custom_width_spin.setSuffix(" mm")
        self.custom_width_spin.setVisible(False)

        self.custom_height_spin = QDoubleSpinBox()
        self.custom_height_spin.setRange(10, 2000)
        self.custom_height_spin.setValue(297)
        self.custom_height_spin.setSuffix(" mm")
        self.custom_height_spin.setVisible(False)

        self.custom_width_label = QLabel("Custom Width:")
        self.custom_height_label = QLabel("Custom Height:")
        self.custom_width_label.setVisible(False)
        self.custom_height_label.setVisible(False)

        layout.addRow(self.custom_width_label, self.custom_width_spin)
        layout.addRow(self.custom_height_label, self.custom_height_spin)

        # Units
        self.units_combo = QComboBox()
        self.units_combo.addItems(["mm", "inch", "px"])
        layout.addRow("Units:", self.units_combo)

        # Margin
        self.margin_spin = QDoubleSpinBox()
        self.margin_spin.setRange(0, 50)
        self.margin_spin.setValue(10.0)
        self.margin_spin.setSuffix(" mm")
        layout.addRow("Margin:", self.margin_spin)

        self.options_tabs.addTab(widget, "Page")

    def _create_quality_options_tab(self):
        """Create quality options tab."""
        widget = QWidget()
        layout = QFormLayout(widget)

        # Line width scale
        self.line_width_scale_spin = QDoubleSpinBox()
        self.line_width_scale_spin.setRange(0.1, 5.0)
        self.line_width_scale_spin.setValue(1.0)
        self.line_width_scale_spin.setSingleStep(0.1)
        self.line_width_scale_spin.setDecimals(2)
        layout.addRow("Line Width Scale:", self.line_width_scale_spin)

        # Text scale
        self.text_scale_spin = QDoubleSpinBox()
        self.text_scale_spin.setRange(0.1, 5.0)
        self.text_scale_spin.setValue(1.0)
        self.text_scale_spin.setSingleStep(0.1)
        self.text_scale_spin.setDecimals(2)
        layout.addRow("Text Scale:", self.text_scale_spin)

        # Precision
        self.precision_spin = QSpinBox()
        self.precision_spin.setRange(0, 6)
        self.precision_spin.setValue(3)
        layout.addRow("Coordinate Precision:", self.precision_spin)

        self.options_tabs.addTab(widget, "Quality")

    def _create_format_options_tab(self):
        """Create format-specific options tab."""
        self.format_widget = QWidget()
        self.format_layout = QFormLayout(self.format_widget)

        # SVG options
        self.svg_embed_fonts_check = QCheckBox()
        self.svg_embed_fonts_check.setChecked(True)

        # PDF options
        self.pdf_compression_check = QCheckBox()
        self.pdf_compression_check.setChecked(True)

        self.pdf_title_edit = QLineEdit("CAD Drawing")
        self.pdf_author_edit = QLineEdit("PyCAD")
        self.pdf_subject_edit = QLineEdit("Technical Drawing")

        self.options_tabs.addTab(self.format_widget, "Format Options")

    def _on_page_size_changed(self, page_size: str):
        """Handle page size change."""
        is_custom = page_size == "CUSTOM"
        
        self.custom_width_label.setVisible(is_custom)
        self.custom_width_spin.setVisible(is_custom)
        self.custom_height_label.setVisible(is_custom)
        self.custom_height_spin.setVisible(is_custom)

        if not is_custom:
            self._refresh_preview()

    def _on_format_changed(self, format_name: str):
        """Handle format selection change."""
        self.current_format = format_name.lower()
        self._update_format_options()
        self._update_file_extension()
        self._refresh_preview()

    def _update_format_options(self):
        """Update format-specific options based on selected format."""
        # Clear existing options
        while self.format_layout.count():
            child = self.format_layout.takeAt(0)
            if child.widget():
                child.widget().setVisible(False)

        if self.current_format == "svg":
            self.format_layout.addRow("Embed Fonts:", self.svg_embed_fonts_check)
            self.svg_embed_fonts_check.setVisible(True)
        elif self.current_format == "pdf":
            self.format_layout.addRow("Compression:", self.pdf_compression_check)
            self.format_layout.addRow("Title:", self.pdf_title_edit)
            self.format_layout.addRow("Author:", self.pdf_author_edit)
            self.format_layout.addRow("Subject:", self.pdf_subject_edit)
            
            self.pdf_compression_check.setVisible(True)
            self.pdf_title_edit.setVisible(True)
            self.pdf_author_edit.setVisible(True)
            self.pdf_subject_edit.setVisible(True)

    def _update_file_extension(self):
        """Update file extension based on format."""
        current_path = self.file_path_edit.text()
        if current_path:
            # Remove existing extension
            if '.' in current_path:
                current_path = current_path.rsplit('.', 1)[0]
            
            # Add new extension
            extension = f".{self.current_format}"
            self.file_path_edit.setText(current_path + extension)

    def _browse_file(self):
        """Open file dialog to select export file."""
        if not self.current_format:
            QMessageBox.warning(self, "Warning", "Please select an export format first.")
            return

        # Create file filter
        format_name = self.current_format.upper()
        extension = f"*.{self.current_format}"
        file_filter = f"{format_name} Files ({extension});;All Files (*.*)"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export to {format_name}",
            f"untitled.{self.current_format}",
            file_filter
        )

        if file_path:
            self.file_path_edit.setText(file_path)
            self.export_button.setEnabled(bool(file_path))

    async def _load_supported_formats(self):
        """Load supported export formats from API."""
        try:
            if not self.api_client:
                # Fallback to default formats
                self.supported_formats = ["svg", "pdf"]
                self.format_combo.addItems([fmt.upper() for fmt in self.supported_formats])
                return

            response = await self.api_client.get_supported_export_formats()
            if response.get("success", False):
                formats_data = response.get("data", {}).get("supported_formats", [])
                self.supported_formats = [fmt["format"] for fmt in formats_data]
                self.format_combo.addItems([fmt["format"].upper() for fmt in formats_data])
                
                if self.supported_formats:
                    self.current_format = self.supported_formats[0]
                    self._update_format_options()
            else:
                logger.warning("Failed to load supported formats, using defaults")
                self.supported_formats = ["svg", "pdf"]
                self.format_combo.addItems([fmt.upper() for fmt in self.supported_formats])

        except Exception as e:
            logger.error(f"Error loading supported formats: {e}")
            self.supported_formats = ["svg", "pdf"]
            self.format_combo.addItems([fmt.upper() for fmt in self.supported_formats])

    def _refresh_preview(self):
        """Refresh export preview."""
        if not self.current_format or not self.api_client:
            return

        asyncio.create_task(self._update_preview())

    async def _update_preview(self):
        """Update preview information."""
        try:
            options = self._gather_options()
            
            response = await self.api_client.preview_export(
                self.document_id, options
            )
            
            if response.get("success", False):
                preview_data = response.get("data", {}).get("preview", {})
                self._display_preview(preview_data)
            else:
                self.preview_text.setText("Preview not available")
                
        except Exception as e:
            logger.error(f"Error updating preview: {e}")
            self.preview_text.setText(f"Preview error: {str(e)}")

    def _display_preview(self, preview_data: Dict):
        """Display preview information."""
        bounds = preview_data.get("bounds", {})
        page = preview_data.get("page", {})
        transform = preview_data.get("transform", {})
        
        preview_text = f"""Export Preview:

Content Bounds:
  Width: {bounds.get('width', 0):.2f} units
  Height: {bounds.get('height', 0):.2f} units
  
Page Size:
  {page.get('width', 0):.2f} x {page.get('height', 0):.2f} {page.get('units', 'mm')}
  
Scale: {transform.get('scale', 1.0):.3f}

Entities: {preview_data.get('entity_count', 0)}
Layers: {preview_data.get('layer_count', 0)}
"""
        self.preview_text.setText(preview_text)

    def _gather_options(self) -> Dict:
        """Gather all export options from the UI."""
        options = {
            "scale_factor": self.scale_factor_spin.value(),
            "page_size": self.page_size_combo.currentText(),
            "orientation": self.orientation_combo.currentText(),
            "units": self.units_combo.currentText(),
            "margin": self.margin_spin.value(),
            "line_width_scale": self.line_width_scale_spin.value(),
            "text_scale": self.text_scale_spin.value(),
            "precision": self.precision_spin.value()
        }

        # Layer options
        include_layers = self.include_layers_edit.text().strip()
        if include_layers:
            options["include_layers"] = [layer.strip() for layer in include_layers.split(",")]

        exclude_layers = self.exclude_layers_edit.text().strip()
        if exclude_layers:
            options["exclude_layers"] = [layer.strip() for layer in exclude_layers.split(",")]

        # Custom page size
        if self.page_size_combo.currentText() == "CUSTOM":
            options["custom_width"] = self.custom_width_spin.value()
            options["custom_height"] = self.custom_height_spin.value()

        # Format-specific options
        if self.current_format == "svg":
            options["svg_embed_fonts"] = self.svg_embed_fonts_check.isChecked()
        elif self.current_format == "pdf":
            options["pdf_compression"] = self.pdf_compression_check.isChecked()
            options["pdf_metadata"] = {
                "title": self.pdf_title_edit.text(),
                "author": self.pdf_author_edit.text(),
                "subject": self.pdf_subject_edit.text()
            }

        return options

    def _export_document(self):
        """Perform the export operation."""
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            QMessageBox.warning(self, "Warning", "Please specify a file path.")
            return

        if not self.current_format:
            QMessageBox.warning(self, "Warning", "Please select an export format.")
            return

        options = self._gather_options()
        
        # Emit signal for parent to handle
        self.export_requested.emit(file_path, self.current_format, options)
        self.accept()

    def showEvent(self, event):
        """Handle dialog show event."""
        super().showEvent(event)
        # Load formats when dialog is shown
        asyncio.create_task(self._load_supported_formats())