"""
Comprehensive demo for CAD modification tools.

This demo showcases all the modification tools including move, copy, rotate,
scale, and mirror operations with interactive preview and selection.
"""

import logging
import sys
from enum import Enum
from typing import Any, Dict, Optional

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSlider,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from ..core.selection_manager import SelectionManager
from ..graphics.snap_engine import SnapType
from ..graphics.tools import (
    CopyTool,
    MirrorTool,
    MoveTool,
    RotateTool,
    ScaleTool,
    ToolManager,
)

# Import our CAD components
from ..ui.canvas.cad_canvas_view import CADCanvasView


class DemoTool(Enum):
    """Available demo tools."""

    SELECT = "Select"
    MOVE = "Move"
    COPY = "Copy"
    ROTATE = "Rotate"
    SCALE = "Scale"
    MIRROR = "Mirror"


class ModificationToolsDemoWindow(QMainWindow):
    """
    Main window for modification tools demonstration.

    Features:
    - Interactive CAD canvas with all modification tools
    - Selection system integration
    - Tool switching and configuration
    - Real-time status display
    - Demo content for testing
    """

    def __init__(self):
        super().__init__()

        # Setup logging
        logging.basicConfig(level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

        # Initialize tool system
        self.setup_tools()

        # Initialize UI
        self.setup_ui()
        self.setup_toolbar()
        self.setup_status_bar()
        self.connect_signals()

        # Demo state
        self.current_tool_type = DemoTool.SELECT
        self.demo_items = []

        # Set initial tool
        self.switch_to_tool(DemoTool.SELECT)

        self.logger.info("Modification tools demo initialized")

    def setup_tools(self):
        """Setup the tool system with all modification tools."""
        # Create mock API client and command manager
        self.api_client = MockAPIClient()
        self.command_manager = MockCommandManager()

        # This will be set when the canvas is created
        self.snap_engine = None
        self.selection_manager = None
        self.tool_manager = None

        # Tool instances will be created after scene setup
        self.tools = {}

    def setup_ui(self):
        """Setup the main user interface."""
        self.setWindowTitle("CAD Modification Tools Demo")
        self.setMinimumSize(1200, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Create graphics scene and view
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-500, -500, 1000, 1000)

        self.canvas_view = CADCanvasView(self.scene)

        # Get references to canvas components
        self.snap_engine = self.canvas_view.get_snap_engine()

        # Create selection manager (mock for demo)
        self.selection_manager = MockSelectionManager(self.scene)

        # Create tool manager
        self.tool_manager = ToolManager(self.scene)
        self.canvas_view.set_tool_manager(self.tool_manager)

        # Initialize modification tools
        self._initialize_tools()

        # Left panel for controls
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 0)

        # Canvas view
        main_layout.addWidget(self.canvas_view, 1)

        # Add demo content
        self.add_demo_content()

    def _initialize_tools(self):
        """Initialize all modification tools."""
        self.tools = {
            DemoTool.MOVE: MoveTool(
                self.scene,
                self.api_client,
                self.command_manager,
                self.snap_engine,
                self.selection_manager,
            ),
            DemoTool.COPY: CopyTool(
                self.scene,
                self.api_client,
                self.command_manager,
                self.snap_engine,
                self.selection_manager,
            ),
            DemoTool.ROTATE: RotateTool(
                self.scene,
                self.api_client,
                self.command_manager,
                self.snap_engine,
                self.selection_manager,
            ),
            DemoTool.SCALE: ScaleTool(
                self.scene,
                self.api_client,
                self.command_manager,
                self.snap_engine,
                self.selection_manager,
            ),
            DemoTool.MIRROR: MirrorTool(
                self.scene,
                self.api_client,
                self.command_manager,
                self.snap_engine,
                self.selection_manager,
            ),
        }

        # Register tools with tool manager
        for tool in self.tools.values():
            self.tool_manager.register_tool(tool)

    def create_control_panel(self) -> QWidget:
        """Create the control panel with tool selection and settings."""
        panel = QWidget()
        panel.setFixedWidth(280)
        layout = QVBoxLayout(panel)

        # Tool selection
        tools_group = QGroupBox("Modification Tools")
        tools_layout = QVBoxLayout(tools_group)

        self.tool_buttons = {}
        for tool_type in DemoTool:
            btn = QPushButton(tool_type.value)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, t=tool_type: self.switch_to_tool(t))
            self.tool_buttons[tool_type] = btn
            tools_layout.addWidget(btn)

        layout.addWidget(tools_group)

        # Selection controls
        selection_group = QGroupBox("Selection")
        selection_layout = QVBoxLayout(selection_group)

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all_items)
        selection_layout.addWidget(self.select_all_btn)

        self.clear_selection_btn = QPushButton("Clear Selection")
        self.clear_selection_btn.clicked.connect(self.clear_selection)
        selection_layout.addWidget(self.clear_selection_btn)

        self.selection_info_label = QLabel("Selected: 0 items")
        selection_layout.addWidget(self.selection_info_label)

        layout.addWidget(selection_group)

        # Snap controls
        snap_group = QGroupBox("Snap Settings")
        snap_layout = QVBoxLayout(snap_group)

        self.snap_grid_cb = QCheckBox("Snap to Grid")
        self.snap_grid_cb.setChecked(True)
        snap_layout.addWidget(self.snap_grid_cb)

        self.snap_geometry_cb = QCheckBox("Snap to Geometry")
        self.snap_geometry_cb.setChecked(True)
        snap_layout.addWidget(self.snap_geometry_cb)

        self.snap_rulers_cb = QCheckBox("Snap to Rulers")
        self.snap_rulers_cb.setChecked(True)
        snap_layout.addWidget(self.snap_rulers_cb)

        layout.addWidget(snap_group)

        # Tool-specific settings
        self.tool_settings_group = QGroupBox("Tool Settings")
        self.tool_settings_layout = QVBoxLayout(self.tool_settings_group)
        layout.addWidget(self.tool_settings_group)

        # Demo controls
        demo_group = QGroupBox("Demo Controls")
        demo_layout = QVBoxLayout(demo_group)

        self.add_shapes_btn = QPushButton("Add Test Shapes")
        self.add_shapes_btn.clicked.connect(self.add_test_shapes)
        demo_layout.addWidget(self.add_shapes_btn)

        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.clicked.connect(self.clear_all_items)
        demo_layout.addWidget(self.clear_all_btn)

        layout.addWidget(demo_group)

        layout.addStretch()
        return panel

    def setup_toolbar(self):
        """Setup the main toolbar."""
        toolbar = QToolBar()
        self.addToolBar(toolbar)

        # Tool actions
        for tool_type in DemoTool:
            action = QAction(tool_type.value, self)
            action.setCheckable(True)
            if tool_type == DemoTool.SELECT:
                action.setChecked(True)
            action.triggered.connect(
                lambda checked, t=tool_type: self.switch_to_tool(t)
            )
            toolbar.addAction(action)

        toolbar.addSeparator()

        # View actions
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

    def setup_status_bar(self):
        """Setup the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Tool status
        self.tool_status_label = QLabel("Tool: Select")
        self.status_bar.addWidget(self.tool_status_label)

        # Coordinate display
        self.coord_label = QLabel("Coordinates: (0.0, 0.0)")
        self.status_bar.addWidget(self.coord_label)

        # Tool info
        self.tool_info_label = QLabel("Ready")
        self.status_bar.addPermanentWidget(self.tool_info_label)

    def connect_signals(self):
        """Connect UI signals."""
        # Snap controls
        self.snap_grid_cb.toggled.connect(self.update_snap_settings)
        self.snap_geometry_cb.toggled.connect(self.update_snap_settings)
        self.snap_rulers_cb.toggled.connect(self.update_snap_settings)

        # Canvas signals
        self.canvas_view.coordinates_changed.connect(self.on_coordinates_changed)

        # Selection manager signals
        self.selection_manager.selection_changed.connect(self.on_selection_changed)

        # Tool signals
        for tool in self.tools.values():
            if hasattr(tool, "move_started"):
                tool.move_started.connect(
                    lambda p: self.tool_info_label.setText(
                        f"Move started at ({p.x():.1f}, {p.y():.1f})"
                    )
                )
            if hasattr(tool, "copy_started"):
                tool.copy_started.connect(
                    lambda p: self.tool_info_label.setText(
                        f"Copy started at ({p.x():.1f}, {p.y():.1f})"
                    )
                )
            if hasattr(tool, "rotate_started"):
                tool.rotate_started.connect(
                    lambda p: self.tool_info_label.setText(
                        f"Rotation center at ({p.x():.1f}, {p.y():.1f})"
                    )
                )
            if hasattr(tool, "scale_started"):
                tool.scale_started.connect(
                    lambda p: self.tool_info_label.setText(
                        f"Scale base at ({p.x():.1f}, {p.y():.1f})"
                    )
                )
            if hasattr(tool, "mirror_started"):
                tool.mirror_started.connect(
                    lambda p: self.tool_info_label.setText(
                        f"Mirror line start at ({p.x():.1f}, {p.y():.1f})"
                    )
                )

    def add_demo_content(self):
        """Add some demo content to the scene."""
        # Add some basic shapes for testing

        # Rectangle
        rect_item = self.scene.addRect(-50, -25, 100, 50)
        rect_item.entity_id = "rect_1"
        self.demo_items.append(rect_item)

        # Circle
        circle_item = self.scene.addEllipse(-75, 50, 150, 150)
        circle_item.entity_id = "circle_1"
        self.demo_items.append(circle_item)

        # Lines
        line1 = self.scene.addLine(-100, -100, 100, 100)
        line1.entity_id = "line_1"
        self.demo_items.append(line1)

        line2 = self.scene.addLine(-100, 100, 100, -100)
        line2.entity_id = "line_2"
        self.demo_items.append(line2)

        self.logger.info("Demo content added to scene")

    def add_test_shapes(self):
        """Add additional test shapes."""
        import random

        for i in range(3):
            x = random.randint(-200, 200)
            y = random.randint(-200, 200)

            if i % 3 == 0:
                # Rectangle
                item = self.scene.addRect(x, y, 50, 30)
            elif i % 3 == 1:
                # Circle
                item = self.scene.addEllipse(x, y, 40, 40)
            else:
                # Line
                item = self.scene.addLine(x, y, x + 50, y + 30)

            item.entity_id = f"test_shape_{len(self.demo_items)}"
            self.demo_items.append(item)

        self.logger.info("Additional test shapes added")

    def switch_to_tool(self, tool_type: DemoTool):
        """Switch to the specified tool."""
        # Update button states
        for tt, btn in self.tool_buttons.items():
            btn.setChecked(tt == tool_type)

        # Update toolbar actions
        for action in self.findChildren(QAction):
            if action.text() == tool_type.value:
                action.setChecked(True)
            elif action.text() in [t.value for t in DemoTool]:
                action.setChecked(False)

        # Deactivate current tool
        if self.current_tool_type in self.tools:
            self.tools[self.current_tool_type].deactivate()

        self.current_tool_type = tool_type

        # Activate new tool
        if tool_type in self.tools:
            self.tools[tool_type].activate()
            self.tool_manager.set_active_tool(self.tools[tool_type])
        else:
            self.tool_manager.set_active_tool(None)

        # Update status
        self.tool_status_label.setText(f"Tool: {tool_type.value}")
        self.tool_info_label.setText("Ready")

        # Update tool-specific settings
        self.update_tool_settings(tool_type)

        self.logger.debug(f"Switched to tool: {tool_type.value}")

    def update_tool_settings(self, tool_type: DemoTool):
        """Update tool-specific settings panel."""
        # Clear existing settings
        for i in reversed(range(self.tool_settings_layout.count())):
            self.tool_settings_layout.itemAt(i).widget().setParent(None)

        if tool_type == DemoTool.COPY:
            multi_copy_cb = QCheckBox("Multiple Copy Mode")
            self.tool_settings_layout.addWidget(multi_copy_cb)

        elif tool_type == DemoTool.SCALE:
            mode_combo = QComboBox()
            mode_combo.addItems(["Uniform", "Non-Uniform", "Reference"])
            self.tool_settings_layout.addWidget(QLabel("Scale Mode:"))
            self.tool_settings_layout.addWidget(mode_combo)

        elif tool_type == DemoTool.MIRROR:
            copy_mode_cb = QCheckBox("Copy Mode (Keep Original)")
            copy_mode_cb.setChecked(True)
            self.tool_settings_layout.addWidget(copy_mode_cb)

    def update_snap_settings(self):
        """Update snap settings."""
        snap_types = SnapType.NONE

        if self.snap_grid_cb.isChecked():
            snap_types |= SnapType.GRID

        if self.snap_geometry_cb.isChecked():
            snap_types |= SnapType.GEOMETRIC

        if self.snap_rulers_cb.isChecked():
            snap_types |= SnapType.RULER_GUIDE

        self.snap_engine.set_enabled_snaps(snap_types)
        self.logger.debug(f"Snap settings updated: {snap_types}")

    def select_all_items(self):
        """Select all demo items."""
        self.selection_manager.clear_selection()
        for item in self.demo_items:
            self.selection_manager.add_to_selection(item)

    def clear_selection(self):
        """Clear current selection."""
        self.selection_manager.clear_selection()

    def clear_all_items(self):
        """Clear all items from the scene."""
        for item in self.demo_items:
            if item.scene():
                self.scene.removeItem(item)
        self.demo_items.clear()
        self.clear_selection()

    def on_coordinates_changed(self, x: float, y: float):
        """Handle coordinate changes."""
        self.coord_label.setText(f"Coordinates: ({x:.2f}, {y:.2f})")

    def on_selection_changed(self, selected_items):
        """Handle selection changes."""
        count = len(selected_items)
        self.selection_info_label.setText(f"Selected: {count} items")

        # Notify tools about selection change
        for tool in self.tools.values():
            if hasattr(tool, "selection_changed"):
                tool.selection_changed(selected_items)


class MockAPIClient:
    """Mock API client for demo purposes."""

    async def move_entities(self, entity_ids, dx, dy):
        """Mock move entities."""
        print(f"Mock: Moving {len(entity_ids)} entities by ({dx:.2f}, {dy:.2f})")
        return True

    async def copy_entities(self, entity_ids, dx, dy):
        """Mock copy entities."""
        print(f"Mock: Copying {len(entity_ids)} entities by ({dx:.2f}, {dy:.2f})")
        return True

    async def rotate_entities(self, entity_ids, cx, cy, angle):
        """Mock rotate entities."""
        print(
            f"Mock: Rotating {len(entity_ids)} entities around ({cx:.2f}, {cy:.2f}) by {angle:.1f}°"
        )
        return True

    async def scale_entities(self, entity_ids, cx, cy, sx, sy):
        """Mock scale entities."""
        print(
            f"Mock: Scaling {len(entity_ids)} entities from ({cx:.2f}, {cy:.2f}) by ({sx:.2f}, {sy:.2f})"
        )
        return True

    async def mirror_entities(self, entity_ids, x1, y1, x2, y2, copy_mode):
        """Mock mirror entities."""
        mode = "copy" if copy_mode else "move"
        print(
            f"Mock: Mirroring ({mode}) {len(entity_ids)} entities across line ({x1:.2f}, {y1:.2f}) to ({x2:.2f}, {y2:.2f})"
        )
        return True


class MockCommandManager:
    """Mock command manager for demo purposes."""

    async def execute_command(self, command):
        """Mock execute command."""
        print(f"Mock: Executing command {type(command).__name__}")
        # Simulate command execution
        if hasattr(command, "execute"):
            return await command.execute()
        return True


class MockSelectionManager:
    """Mock selection manager for demo purposes."""

    def __init__(self, scene):
        from PySide6.QtCore import QObject, Signal

        super().__init__()
        self.scene = scene
        self.selected_items = set()

        # Create signal manually since we can't inherit from QObject properly here
        self.selection_changed = lambda items: None

    def has_selection(self):
        """Check if there are selected items."""
        return len(self.selected_items) > 0

    def get_selected_items(self):
        """Get selected items."""
        return list(self.selected_items)

    def add_to_selection(self, item):
        """Add item to selection."""
        self.selected_items.add(item)
        item.setSelected(True)
        self.selection_changed(list(self.selected_items))

    def remove_from_selection(self, item):
        """Remove item from selection."""
        if item in self.selected_items:
            self.selected_items.remove(item)
            item.setSelected(False)
            self.selection_changed(list(self.selected_items))

    def clear_selection(self):
        """Clear all selection."""
        for item in self.selected_items:
            item.setSelected(False)
        self.selected_items.clear()
        self.selection_changed([])

    def toggle_selection(self, item):
        """Toggle item selection."""
        if item in self.selected_items:
            self.remove_from_selection(item)
        else:
            self.add_to_selection(item)


def main():
    """Run the modification tools demo."""
    app = QApplication(sys.argv)

    window = ModificationToolsDemoWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
