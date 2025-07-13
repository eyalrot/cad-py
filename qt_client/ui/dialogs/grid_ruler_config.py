"""
Grid and ruler configuration dialog.

This module provides a comprehensive configuration interface for grid
and ruler settings in the CAD application.
"""

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from ..canvas.grid_overlay import GridOverlay
from ..canvas.ruler_overlay import RulerOverlay

logger = logging.getLogger(__name__)


class ColorButton(QPushButton):
    """Button for color selection."""

    color_changed = Signal(QColor)

    def __init__(self, color: QColor = QColor(255, 255, 255)):
        super().__init__()
        self.current_color = color
        self.setFixedSize(40, 25)
        self.update_button_color()
        self.clicked.connect(self.select_color)

    def update_button_color(self):
        """Update button appearance with current color."""
        self.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {self.current_color.name()};
                border: 1px solid #ccc;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                border: 2px solid #999;
            }}
        """
        )

    def select_color(self):
        """Open color selection dialog."""
        color = QColorDialog.getColor(self.current_color, self, "Select Color")
        if color.isValid():
            self.current_color = color
            self.update_button_color()
            self.color_changed.emit(color)

    def set_color(self, color: QColor):
        """Set color without emitting signal."""
        self.current_color = color
        self.update_button_color()


class GridRulerConfigDialog(QDialog):
    """
    Configuration dialog for grid and ruler settings.

    Provides controls for:
    - Grid visibility and spacing
    - Grid colors and line widths
    - Ruler visibility and units
    - Ruler precision and formatting
    - Snap settings
    """

    # Signals
    settings_changed = Signal()

    def __init__(
        self, grid_overlay: GridOverlay, ruler_overlay: RulerOverlay, parent=None
    ):
        super().__init__(parent)
        self.grid_overlay = grid_overlay
        self.ruler_overlay = ruler_overlay

        self.setWindowTitle("Grid and Ruler Settings")
        self.setModal(True)
        self.resize(400, 500)

        self.setup_ui()
        self.load_current_settings()
        self.connect_signals()

        logger.debug("Grid ruler config dialog initialized")

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Grid settings group
        grid_group = self.create_grid_settings_group()
        layout.addWidget(grid_group)

        # Ruler settings group
        ruler_group = self.create_ruler_settings_group()
        layout.addWidget(ruler_group)

        # Snap settings group
        snap_group = self.create_snap_settings_group()
        layout.addWidget(snap_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.apply_btn = QPushButton("Apply")
        self.reset_btn = QPushButton("Reset")
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")

        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def create_grid_settings_group(self) -> QGroupBox:
        """Create grid settings group."""
        group = QGroupBox("Grid Settings")
        layout = QGridLayout(group)

        # Grid visibility
        self.grid_visible_cb = QCheckBox("Show Grid")
        layout.addWidget(self.grid_visible_cb, 0, 0, 1, 2)

        # Spacing settings
        layout.addWidget(QLabel("Major Spacing:"), 1, 0)
        self.major_spacing_sb = QDoubleSpinBox()
        self.major_spacing_sb.setRange(0.001, 10000.0)
        self.major_spacing_sb.setDecimals(3)
        self.major_spacing_sb.setSuffix(" units")
        layout.addWidget(self.major_spacing_sb, 1, 1)

        layout.addWidget(QLabel("Subdivisions:"), 2, 0)
        self.subdivisions_sb = QSpinBox()
        self.subdivisions_sb.setRange(2, 100)
        layout.addWidget(self.subdivisions_sb, 2, 1)

        # Color settings
        layout.addWidget(QLabel("Major Line Color:"), 3, 0)
        self.major_color_btn = ColorButton()
        layout.addWidget(self.major_color_btn, 3, 1)

        layout.addWidget(QLabel("Minor Line Color:"), 4, 0)
        self.minor_color_btn = ColorButton()
        layout.addWidget(self.minor_color_btn, 4, 1)

        # Line width settings
        layout.addWidget(QLabel("Major Line Width:"), 5, 0)
        self.major_width_sb = QDoubleSpinBox()
        self.major_width_sb.setRange(0.1, 10.0)
        self.major_width_sb.setDecimals(1)
        self.major_width_sb.setSuffix(" px")
        layout.addWidget(self.major_width_sb, 5, 1)

        layout.addWidget(QLabel("Minor Line Width:"), 6, 0)
        self.minor_width_sb = QDoubleSpinBox()
        self.minor_width_sb.setRange(0.1, 10.0)
        self.minor_width_sb.setDecimals(1)
        self.minor_width_sb.setSuffix(" px")
        layout.addWidget(self.minor_width_sb, 6, 1)

        return group

    def create_ruler_settings_group(self) -> QGroupBox:
        """Create ruler settings group."""
        group = QGroupBox("Ruler Settings")
        layout = QGridLayout(group)

        # Ruler visibility
        self.ruler_visible_cb = QCheckBox("Show Rulers")
        layout.addWidget(self.ruler_visible_cb, 0, 0, 1, 2)

        self.horizontal_ruler_cb = QCheckBox("Horizontal Ruler")
        layout.addWidget(self.horizontal_ruler_cb, 1, 0, 1, 2)

        self.vertical_ruler_cb = QCheckBox("Vertical Ruler")
        layout.addWidget(self.vertical_ruler_cb, 2, 0, 1, 2)

        # Units
        layout.addWidget(QLabel("Units:"), 3, 0)
        self.units_combo = QComboBox()
        self.units_combo.addItems(["mm", "cm", "m", "in", "ft", "units"])
        layout.addWidget(self.units_combo, 3, 1)

        # Precision
        layout.addWidget(QLabel("Precision:"), 4, 0)
        self.precision_sb = QSpinBox()
        self.precision_sb.setRange(0, 6)
        self.precision_sb.setSuffix(" decimal places")
        layout.addWidget(self.precision_sb, 4, 1)

        # Ruler height
        layout.addWidget(QLabel("Ruler Height:"), 5, 0)
        self.ruler_height_sb = QSpinBox()
        self.ruler_height_sb.setRange(15, 50)
        self.ruler_height_sb.setSuffix(" px")
        layout.addWidget(self.ruler_height_sb, 5, 1)

        return group

    def create_snap_settings_group(self) -> QGroupBox:
        """Create snap settings group."""
        group = QGroupBox("Snap Settings")
        layout = QGridLayout(group)

        # Snap to grid
        self.snap_to_grid_cb = QCheckBox("Snap to Grid")
        layout.addWidget(self.snap_to_grid_cb, 0, 0, 1, 2)

        # Snap to rulers
        self.snap_to_rulers_cb = QCheckBox("Snap to Ruler Guides")
        layout.addWidget(self.snap_to_rulers_cb, 1, 0, 1, 2)

        # Snap tolerance
        layout.addWidget(QLabel("Snap Tolerance:"), 2, 0)
        self.snap_tolerance_sb = QDoubleSpinBox()
        self.snap_tolerance_sb.setRange(0.1, 50.0)
        self.snap_tolerance_sb.setDecimals(1)
        self.snap_tolerance_sb.setSuffix(" px")
        layout.addWidget(self.snap_tolerance_sb, 2, 1)

        return group

    def connect_signals(self):
        """Connect UI signals."""
        # Buttons
        self.apply_btn.clicked.connect(self.apply_settings)
        self.reset_btn.clicked.connect(self.reset_settings)
        self.ok_btn.clicked.connect(self.accept_settings)
        self.cancel_btn.clicked.connect(self.reject)

        # Real-time preview
        self.grid_visible_cb.toggled.connect(self.preview_changes)
        self.major_spacing_sb.valueChanged.connect(self.preview_changes)
        self.subdivisions_sb.valueChanged.connect(self.preview_changes)
        self.major_color_btn.color_changed.connect(self.preview_changes)
        self.minor_color_btn.color_changed.connect(self.preview_changes)
        self.major_width_sb.valueChanged.connect(self.preview_changes)
        self.minor_width_sb.valueChanged.connect(self.preview_changes)

        self.ruler_visible_cb.toggled.connect(self.preview_changes)
        self.horizontal_ruler_cb.toggled.connect(self.preview_changes)
        self.vertical_ruler_cb.toggled.connect(self.preview_changes)
        self.units_combo.currentTextChanged.connect(self.preview_changes)
        self.precision_sb.valueChanged.connect(self.preview_changes)
        self.ruler_height_sb.valueChanged.connect(self.preview_changes)

    def load_current_settings(self):
        """Load current settings from overlays."""
        # Grid settings
        grid_info = self.grid_overlay.get_grid_info()
        self.grid_visible_cb.setChecked(grid_info["visible"])
        self.major_spacing_sb.setValue(grid_info["major_spacing"])
        self.subdivisions_sb.setValue(grid_info["subdivision"])

        # Grid colors (parse from hex strings)
        major_color = QColor(grid_info["major_color"])
        minor_color = QColor(grid_info["minor_color"])
        self.major_color_btn.set_color(major_color)
        self.minor_color_btn.set_color(minor_color)

        # Line widths
        self.major_width_sb.setValue(self.grid_overlay._major_width)
        self.minor_width_sb.setValue(self.grid_overlay._minor_width)

        # Ruler settings
        ruler_info = self.ruler_overlay.get_ruler_info()
        self.ruler_visible_cb.setChecked(ruler_info["visible"])
        self.horizontal_ruler_cb.setChecked(ruler_info["show_horizontal"])
        self.vertical_ruler_cb.setChecked(ruler_info["show_vertical"])
        self.units_combo.setCurrentText(ruler_info["units"])
        self.precision_sb.setValue(ruler_info["precision"])
        self.ruler_height_sb.setValue(ruler_info["ruler_height"])

        # Snap settings (default values)
        self.snap_to_grid_cb.setChecked(True)
        self.snap_to_rulers_cb.setChecked(True)
        self.snap_tolerance_sb.setValue(5.0)

    def apply_settings(self):
        """Apply current settings to overlays."""
        # Grid settings
        self.grid_overlay.setVisible(self.grid_visible_cb.isChecked())
        self.grid_overlay.major_spacing = self.major_spacing_sb.value()

        # Grid colors
        self.grid_overlay.set_colors(
            self.major_color_btn.current_color, self.minor_color_btn.current_color
        )

        # Grid line widths
        self.grid_overlay.set_line_widths(
            self.major_width_sb.value(), self.minor_width_sb.value()
        )

        # Ruler settings
        self.ruler_overlay.set_visible(self.ruler_visible_cb.isChecked())
        self.ruler_overlay.set_horizontal_visible(self.horizontal_ruler_cb.isChecked())
        self.ruler_overlay.set_vertical_visible(self.vertical_ruler_cb.isChecked())
        self.ruler_overlay.set_units(self.units_combo.currentText())
        self.ruler_overlay.set_precision(self.precision_sb.value())
        self.ruler_overlay.ruler_height = self.ruler_height_sb.value()

        # Emit change signal
        self.settings_changed.emit()

        logger.info("Grid and ruler settings applied")

    def preview_changes(self):
        """Preview changes in real-time."""
        if hasattr(self, "_preview_enabled") and self._preview_enabled:
            self.apply_settings()

    def reset_settings(self):
        """Reset settings to defaults."""
        # Grid defaults
        self.grid_visible_cb.setChecked(True)
        self.major_spacing_sb.setValue(10.0)
        self.subdivisions_sb.setValue(10)
        self.major_color_btn.set_color(QColor(180, 180, 180, 128))
        self.minor_color_btn.set_color(QColor(220, 220, 220, 128))
        self.major_width_sb.setValue(1.0)
        self.minor_width_sb.setValue(0.5)

        # Ruler defaults
        self.ruler_visible_cb.setChecked(True)
        self.horizontal_ruler_cb.setChecked(True)
        self.vertical_ruler_cb.setChecked(True)
        self.units_combo.setCurrentText("mm")
        self.precision_sb.setValue(1)
        self.ruler_height_sb.setValue(20)

        # Snap defaults
        self.snap_to_grid_cb.setChecked(True)
        self.snap_to_rulers_cb.setChecked(True)
        self.snap_tolerance_sb.setValue(5.0)

        logger.info("Settings reset to defaults")

    def accept_settings(self):
        """Apply settings and close dialog."""
        self.apply_settings()
        self.accept()

    def enable_preview(self, enabled: bool = True):
        """Enable/disable real-time preview."""
        self._preview_enabled = enabled

    def get_snap_settings(self) -> dict:
        """Get snap settings as dictionary."""
        return {
            "snap_to_grid": self.snap_to_grid_cb.isChecked(),
            "snap_to_rulers": self.snap_to_rulers_cb.isChecked(),
            "snap_tolerance": self.snap_tolerance_sb.value(),
        }
