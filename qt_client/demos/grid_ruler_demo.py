"""
Comprehensive demo for grid and ruler system with snap engine.

This demo showcases the complete grid and ruler functionality including:
- Grid overlay with adaptive spacing
- Rulers with measurements and guides
- Snap engine integration
- Configuration dialog
- Interactive drawing tools
"""

import logging
import sys
from typing import Optional

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..graphics.snap_engine import SnapType

# Import our CAD components
from ..ui.canvas.cad_canvas_view import CADCanvasView
from ..ui.dialogs.grid_ruler_config import GridRulerConfigDialog


class GridRulerDemoWindow(QMainWindow):
    """
    Main window for grid and ruler system demonstration.

    Features:
    - Interactive CAD canvas with grid and rulers
    - Snap engine demonstration
    - Configuration panel
    - Status display
    - Drawing tools
    """

    def __init__(self):
        super().__init__()

        # Setup logging
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

        # Initialize UI
        self.setup_ui()
        self.setup_toolbar()
        self.setup_status_bar()
        self.connect_signals()

        # Demo state
        self.drawing_mode = "none"
        self.temp_items = []
        self.current_line_start = None

        self.logger.info("Grid ruler demo initialized")

    def setup_ui(self):
        """Setup the main user interface."""
        self.setWindowTitle("CAD Grid and Ruler System Demo")
        self.setMinimumSize(1000, 700)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Create graphics scene and view
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-500, -500, 1000, 1000)

        self.canvas_view = CADCanvasView(self.scene)

        # Left panel for controls
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 0)

        # Canvas view
        main_layout.addWidget(self.canvas_view, 1)

        # Add some demo content
        self.add_demo_content()

    def create_control_panel(self) -> QWidget:
        """Create the control panel with various settings."""
        panel = QWidget()
        panel.setFixedWidth(250)
        layout = QVBoxLayout(panel)

        # Grid controls
        grid_group = QGroupBox("Grid Controls")
        grid_layout = QGridLayout(grid_group)

        self.grid_visible_cb = QCheckBox("Show Grid")
        self.grid_visible_cb.setChecked(True)
        grid_layout.addWidget(self.grid_visible_cb, 0, 0, 1, 2)

        grid_layout.addWidget(QLabel("Spacing:"), 1, 0)
        self.grid_spacing_sb = QSpinBox()
        self.grid_spacing_sb.setRange(1, 100)
        self.grid_spacing_sb.setValue(10)
        grid_layout.addWidget(self.grid_spacing_sb, 1, 1)

        layout.addWidget(grid_group)

        # Ruler controls
        ruler_group = QGroupBox("Ruler Controls")
        ruler_layout = QGridLayout(ruler_group)

        self.ruler_visible_cb = QCheckBox("Show Rulers")
        self.ruler_visible_cb.setChecked(True)
        ruler_layout.addWidget(self.ruler_visible_cb, 0, 0, 1, 2)

        self.h_ruler_cb = QCheckBox("Horizontal")
        self.h_ruler_cb.setChecked(True)
        ruler_layout.addWidget(self.h_ruler_cb, 1, 0)

        self.v_ruler_cb = QCheckBox("Vertical")
        self.v_ruler_cb.setChecked(True)
        ruler_layout.addWidget(self.v_ruler_cb, 1, 1)

        layout.addWidget(ruler_group)

        # Snap controls
        snap_group = QGroupBox("Snap Controls")
        snap_layout = QVBoxLayout(snap_group)

        self.snap_grid_cb = QCheckBox("Snap to Grid")
        self.snap_grid_cb.setChecked(True)
        snap_layout.addWidget(self.snap_grid_cb)

        self.snap_rulers_cb = QCheckBox("Snap to Rulers")
        self.snap_rulers_cb.setChecked(True)
        snap_layout.addWidget(self.snap_rulers_cb)

        self.snap_geometry_cb = QCheckBox("Snap to Geometry")
        self.snap_geometry_cb.setChecked(True)
        snap_layout.addWidget(self.snap_geometry_cb)

        layout.addWidget(snap_group)

        # Drawing tools
        tools_group = QGroupBox("Drawing Tools")
        tools_layout = QVBoxLayout(tools_group)

        self.line_tool_btn = QPushButton("Line Tool")
        self.line_tool_btn.setCheckable(True)
        tools_layout.addWidget(self.line_tool_btn)

        self.circle_tool_btn = QPushButton("Circle Tool")
        self.circle_tool_btn.setCheckable(True)
        tools_layout.addWidget(self.circle_tool_btn)

        self.clear_btn = QPushButton("Clear All")
        tools_layout.addWidget(self.clear_btn)

        layout.addWidget(tools_group)

        # Action buttons
        self.config_btn = QPushButton("Configuration...")
        layout.addWidget(self.config_btn)

        self.add_guides_btn = QPushButton("Add Test Guides")
        layout.addWidget(self.add_guides_btn)

        layout.addStretch()

        return panel

    def setup_toolbar(self):
        """Setup the main toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # Zoom actions
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setShortcut(QKeySequence.ZoomIn)
        zoom_in_action.triggered.connect(self.canvas_view.zoom_in)
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setShortcut(QKeySequence.ZoomOut)
        zoom_out_action.triggered.connect(self.canvas_view.zoom_out)
        toolbar.addAction(zoom_out_action)

        zoom_fit_action = QAction("Zoom Fit", self)
        zoom_fit_action.setShortcut(QKeySequence("F"))
        zoom_fit_action.triggered.connect(self.canvas_view.zoom_to_fit)
        toolbar.addAction(zoom_fit_action)

        toolbar.addSeparator()

        # Toggle actions
        toggle_grid_action = QAction("Toggle Grid", self)
        toggle_grid_action.setShortcut(QKeySequence("G"))
        toggle_grid_action.triggered.connect(self.canvas_view.toggle_grid)
        toolbar.addAction(toggle_grid_action)

        toggle_rulers_action = QAction("Toggle Rulers", self)
        toggle_rulers_action.setShortcut(QKeySequence("R"))
        toggle_rulers_action.triggered.connect(self.canvas_view.toggle_rulers)
        toolbar.addAction(toggle_rulers_action)

    def setup_status_bar(self):
        """Setup the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Coordinate display
        self.coord_label = QLabel("Coordinates: (0.0, 0.0)")
        self.status_bar.addWidget(self.coord_label)

        # Zoom display
        self.zoom_label = QLabel("Zoom: 100%")
        self.status_bar.addPermanentWidget(self.zoom_label)

        # Snap info
        self.snap_label = QLabel("Snap: None")
        self.status_bar.addPermanentWidget(self.snap_label)

    def connect_signals(self):
        """Connect UI signals."""
        # Grid controls
        self.grid_visible_cb.toggled.connect(self.on_grid_visibility_changed)
        self.grid_spacing_sb.valueChanged.connect(self.on_grid_spacing_changed)

        # Ruler controls
        self.ruler_visible_cb.toggled.connect(self.on_ruler_visibility_changed)
        self.h_ruler_cb.toggled.connect(self.on_horizontal_ruler_changed)
        self.v_ruler_cb.toggled.connect(self.on_vertical_ruler_changed)

        # Snap controls
        self.snap_grid_cb.toggled.connect(self.on_snap_settings_changed)
        self.snap_rulers_cb.toggled.connect(self.on_snap_settings_changed)
        self.snap_geometry_cb.toggled.connect(self.on_snap_settings_changed)

        # Drawing tools
        self.line_tool_btn.toggled.connect(self.on_line_tool_toggled)
        self.circle_tool_btn.toggled.connect(self.on_circle_tool_toggled)
        self.clear_btn.clicked.connect(self.on_clear_all)

        # Action buttons
        self.config_btn.clicked.connect(self.show_configuration)
        self.add_guides_btn.clicked.connect(self.add_test_guides)

        # Canvas signals
        self.canvas_view.coordinates_changed.connect(self.on_coordinates_changed)
        self.canvas_view.zoom_changed.connect(self.on_zoom_changed)

        # Snap engine signals
        snap_engine = self.canvas_view.get_snap_engine()
        snap_engine.snap_preview.connect(self.on_snap_preview)
        snap_engine.snap_cleared.connect(self.on_snap_cleared)

    def add_demo_content(self):
        """Add some demo content to the scene."""
        # Add some basic shapes for snap testing

        # Rectangle
        rect_item = self.scene.addRect(-50, -25, 100, 50)

        # Circle
        circle_item = self.scene.addEllipse(-75, 50, 150, 150)

        # Lines
        line1 = self.scene.addLine(-100, -100, 100, 100)
        line2 = self.scene.addLine(-100, 100, 100, -100)

        self.logger.info("Demo content added to scene")

    def on_grid_visibility_changed(self, visible: bool):
        """Handle grid visibility change."""
        self.canvas_view.get_grid_overlay().setVisible(visible)
        self.canvas_view.update()

    def on_grid_spacing_changed(self, spacing: int):
        """Handle grid spacing change."""
        self.canvas_view.get_grid_overlay().major_spacing = float(spacing)
        self.canvas_view.update()

    def on_ruler_visibility_changed(self, visible: bool):
        """Handle ruler visibility change."""
        self.canvas_view.get_ruler_overlay().set_visible(visible)
        self.canvas_view.update()

    def on_horizontal_ruler_changed(self, visible: bool):
        """Handle horizontal ruler visibility change."""
        self.canvas_view.get_ruler_overlay().set_horizontal_visible(visible)
        self.canvas_view.update()

    def on_vertical_ruler_changed(self, visible: bool):
        """Handle vertical ruler visibility change."""
        self.canvas_view.get_ruler_overlay().set_vertical_visible(visible)
        self.canvas_view.update()

    def on_snap_settings_changed(self):
        """Handle snap settings change."""
        snap_engine = self.canvas_view.get_snap_engine()

        snap_types = SnapType.NONE

        if self.snap_grid_cb.isChecked():
            snap_types |= SnapType.GRID

        if self.snap_rulers_cb.isChecked():
            snap_types |= SnapType.RULER_GUIDE

        if self.snap_geometry_cb.isChecked():
            snap_types |= SnapType.GEOMETRIC

        snap_engine.set_enabled_snaps(snap_types)
        self.logger.debug(f"Snap types updated: {snap_types}")

    def on_line_tool_toggled(self, checked: bool):
        """Handle line tool toggle."""
        if checked:
            self.circle_tool_btn.setChecked(False)
            self.drawing_mode = "line"
            self.status_bar.showMessage("Line tool active - Click to start drawing")
        else:
            self.drawing_mode = "none"
            self.status_bar.showMessage("Ready")
            self.current_line_start = None

    def on_circle_tool_toggled(self, checked: bool):
        """Handle circle tool toggle."""
        if checked:
            self.line_tool_btn.setChecked(False)
            self.drawing_mode = "circle"
            self.status_bar.showMessage("Circle tool active - Click center then radius")
        else:
            self.drawing_mode = "none"
            self.status_bar.showMessage("Ready")

    def on_clear_all(self):
        """Clear all drawing items."""
        # Remove temporary items
        for item in self.temp_items:
            if item.scene():
                self.scene.removeItem(item)
        self.temp_items.clear()

        # Clear guides
        self.canvas_view.get_ruler_guides().clear_all_guides()
        self.canvas_view.update()

        self.status_bar.showMessage("All items cleared")

    def show_configuration(self):
        """Show configuration dialog."""
        dialog = GridRulerConfigDialog(
            self.canvas_view.get_grid_overlay(),
            self.canvas_view.get_ruler_overlay(),
            self,
        )

        # Enable real-time preview
        dialog.enable_preview(True)
        dialog.settings_changed.connect(self.canvas_view.update)

        if dialog.exec() == dialog.Accepted:
            self.logger.info("Configuration applied")
        else:
            # Reload current settings if cancelled
            dialog.load_current_settings()
            dialog.apply_settings()
            self.logger.info("Configuration cancelled, settings restored")

    def add_test_guides(self):
        """Add test ruler guides."""
        guides = self.canvas_view.get_ruler_guides()

        # Add horizontal guides
        guides.add_horizontal_guide(0.0)
        guides.add_horizontal_guide(50.0)
        guides.add_horizontal_guide(-30.0)

        # Add vertical guides
        guides.add_vertical_guide(0.0)
        guides.add_vertical_guide(75.0)
        guides.add_vertical_guide(-45.0)

        self.canvas_view.update()
        self.status_bar.showMessage("Test guides added")

    def on_coordinates_changed(self, x: float, y: float):
        """Handle coordinate changes."""
        self.coord_label.setText(f"Coordinates: ({x:.2f}, {y:.2f})")

    def on_zoom_changed(self, zoom: float):
        """Handle zoom changes."""
        self.zoom_label.setText(f"Zoom: {zoom*100:.1f}%")

    def on_snap_preview(self, position: QPointF, description: str):
        """Handle snap preview."""
        self.snap_label.setText(
            f"Snap: {description} ({position.x():.1f}, {position.y():.1f})"
        )

    def on_snap_cleared(self):
        """Handle snap preview cleared."""
        self.snap_label.setText("Snap: None")

    def mousePressEvent(self, event):
        """Handle mouse press for drawing tools."""
        if self.drawing_mode == "none":
            return super().mousePressEvent(event)

        # Convert to scene coordinates
        scene_pos = self.canvas_view.mapToScene(
            self.canvas_view.mapFromGlobal(event.globalPos())
        )

        # Apply snapping
        snap_result = self.canvas_view.snap_point(scene_pos)
        if snap_result.snapped:
            scene_pos = snap_result.point

        if self.drawing_mode == "line":
            self.handle_line_drawing(scene_pos)
        elif self.drawing_mode == "circle":
            self.handle_circle_drawing(scene_pos)

    def handle_line_drawing(self, pos: QPointF):
        """Handle line drawing interaction."""
        if self.current_line_start is None:
            # Start new line
            self.current_line_start = pos
            self.status_bar.showMessage(
                f"Line started at ({pos.x():.1f}, {pos.y():.1f}) - Click end point"
            )
        else:
            # Complete line
            line_item = QGraphicsLineItem(
                self.current_line_start.x(),
                self.current_line_start.y(),
                pos.x(),
                pos.y(),
            )
            self.scene.addItem(line_item)
            self.temp_items.append(line_item)

            self.status_bar.showMessage(
                f"Line completed to ({pos.x():.1f}, {pos.y():.1f})"
            )
            self.current_line_start = None

    def handle_circle_drawing(self, pos: QPointF):
        """Handle circle drawing interaction."""
        if not hasattr(self, "circle_center"):
            # Set center
            self.circle_center = pos
            self.status_bar.showMessage(
                f"Circle center at ({pos.x():.1f}, {pos.y():.1f}) - Click for radius"
            )
        else:
            # Complete circle
            radius = (
                (pos.x() - self.circle_center.x()) ** 2
                + (pos.y() - self.circle_center.y()) ** 2
            ) ** 0.5

            circle_item = QGraphicsEllipseItem(
                self.circle_center.x() - radius,
                self.circle_center.y() - radius,
                radius * 2,
                radius * 2,
            )
            self.scene.addItem(circle_item)
            self.temp_items.append(circle_item)

            self.status_bar.showMessage(f"Circle completed with radius {radius:.1f}")
            delattr(self, "circle_center")


def main():
    """Run the grid ruler demo."""
    app = QApplication(sys.argv)

    window = GridRulerDemoWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
