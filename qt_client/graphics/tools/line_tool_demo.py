"""
Demo application for the line drawing tool.

This example shows how to integrate the line tool with a Qt application
and demonstrates the various features and modes.
"""

import logging
import sys
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.api_client import APIClientManager
from ...core.command_manager import CommandManager
from ...core.snap_engine import SnapEngine
from ..ui.panels.history_panel import HistoryPanel
from .base_tool import ToolManager
from .line_tool import LineMode, LineTool


class CADGraphicsView(QGraphicsView):
    """Custom graphics view with tool event routing."""

    def __init__(self, scene: QGraphicsScene, tool_manager: ToolManager, parent=None):
        super().__init__(scene, parent)
        self.tool_manager = tool_manager

        # Configure view
        self.setDragMode(QGraphicsView.NoDrag)
        self.setRenderHint(self.painter().Antialiasing)

    def mousePressEvent(self, event: QMouseEvent):
        """Route mouse press to tool manager."""
        if not self.tool_manager.route_mouse_press(event):
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Route mouse move to tool manager."""
        if not self.tool_manager.route_mouse_move(event):
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Route mouse release to tool manager."""
        if not self.tool_manager.route_mouse_release(event):
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        """Route key press to tool manager."""
        if not self.tool_manager.route_key_press(event):
            super().keyPressEvent(event)


class LineToolDemo(QMainWindow):
    """Demo application for the line drawing tool."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAD Line Tool Demo")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize systems
        self.api_client: Optional[APIClientManager] = None
        self.command_manager: Optional[CommandManager] = None
        self.snap_engine: Optional[SnapEngine] = None
        self.tool_manager: Optional[ToolManager] = None
        self.line_tool: Optional[LineTool] = None

        # UI components
        self.scene: Optional[QGraphicsScene] = None
        self.view: Optional[CADGraphicsView] = None
        self.history_panel: Optional[HistoryPanel] = None

        # Status tracking
        self.current_document_id = "demo-doc-123"
        self.current_layer_id = "layer-0"

        # Setup
        self.setup_ui()
        self.initialize_systems()

        # Demo timer for automated demo
        self.demo_timer = QTimer()
        self.demo_step = 0

    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # Left side - graphics view
        self.setup_graphics_area(main_layout)

        # Right side - controls and history
        self.setup_control_area(main_layout)

    def setup_graphics_area(self, main_layout: QHBoxLayout):
        """Setup the graphics drawing area."""
        graphics_layout = QVBoxLayout()

        # Create scene and view
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-500, -400, 1000, 800)

        # Status labels
        status_layout = QHBoxLayout()
        self.coord_label = QLabel("Coordinates: (0, 0)")
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.coord_label)
        status_layout.addStretch()
        status_layout.addWidget(self.status_label)

        graphics_layout.addLayout(status_layout)
        graphics_layout.addWidget(
            QLabel("Graphics View will be added after tool manager initialization")
        )

        main_layout.addLayout(graphics_layout, 2)  # 2/3 of the space

    def setup_control_area(self, main_layout: QHBoxLayout):
        """Setup the control area."""
        control_layout = QVBoxLayout()

        # Tool controls
        tool_group = QWidget()
        tool_layout = QVBoxLayout(tool_group)

        tool_layout.addWidget(QLabel("Line Tool Controls"))

        # Line mode selection
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["single", "polyline"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        tool_layout.addWidget(QLabel("Line Mode:"))
        tool_layout.addWidget(self.mode_combo)

        # Tool options
        self.ortho_checkbox = QCheckBox("Orthogonal Mode")
        self.ortho_checkbox.toggled.connect(self.on_ortho_toggled)
        tool_layout.addWidget(self.ortho_checkbox)

        self.snap_checkbox = QCheckBox("Snap Enabled")
        self.snap_checkbox.setChecked(True)
        self.snap_checkbox.toggled.connect(self.on_snap_toggled)
        tool_layout.addWidget(self.snap_checkbox)

        # Tool buttons
        self.activate_btn = QPushButton("Activate Line Tool")
        self.activate_btn.clicked.connect(self.activate_line_tool)
        tool_layout.addWidget(self.activate_btn)

        self.deactivate_btn = QPushButton("Deactivate Tool")
        self.deactivate_btn.clicked.connect(self.deactivate_tool)
        tool_layout.addWidget(self.deactivate_btn)

        # Demo buttons
        demo_layout = QVBoxLayout()
        demo_layout.addWidget(QLabel("Demo Functions:"))

        self.demo_btn = QPushButton("Run Automated Demo")
        self.demo_btn.clicked.connect(self.start_demo)
        demo_layout.addWidget(self.demo_btn)

        self.clear_btn = QPushButton("Clear Scene")
        self.clear_btn.clicked.connect(self.clear_scene)
        demo_layout.addWidget(self.clear_btn)

        tool_layout.addLayout(demo_layout)
        control_layout.addWidget(tool_group)

        # History panel placeholder
        control_layout.addWidget(
            QLabel("History panel will be added after initialization")
        )

        main_layout.addLayout(control_layout, 1)  # 1/3 of the space

    def initialize_systems(self):
        """Initialize the CAD systems."""
        try:
            # Create API client (in demo mode, might not connect)
            self.api_client = APIClientManager("localhost:50051", self)

            # Create command manager
            self.command_manager = CommandManager(
                self.api_client, max_history=50, parent=self
            )

            # Create snap engine
            self.snap_engine = SnapEngine(self)

            # Create tool manager
            self.tool_manager = ToolManager(
                self.scene,
                self.api_client,
                self.command_manager,
                self.snap_engine,
                self,
            )

            # Create line tool
            self.line_tool = LineTool(
                self.scene,
                self.api_client,
                self.command_manager,
                self.snap_engine,
                self,
            )

            # Register tool
            self.tool_manager.register_tool(self.line_tool)

            # Set document context
            self.tool_manager.set_document_context(
                self.current_document_id, self.current_layer_id
            )

            # Now create the actual graphics view
            self.setup_actual_graphics_view()

            # Setup history panel
            self.setup_history_panel()

            # Connect signals
            self.connect_signals()

            self.status_label.setText("Systems initialized - Ready to draw")

        except Exception as e:
            logging.error(f"Failed to initialize systems: {e}")
            self.status_label.setText(f"Initialization failed: {e}")

    def setup_actual_graphics_view(self):
        """Setup the actual graphics view after tool manager is ready."""
        # Remove placeholder
        central_widget = self.centralWidget()
        main_layout = central_widget.layout()
        graphics_layout = main_layout.itemAt(0).layout()

        # Create actual view
        self.view = CADGraphicsView(self.scene, self.tool_manager, self)
        self.view.setMinimumSize(600, 400)

        # Add to layout (replace placeholder)
        placeholder = graphics_layout.itemAt(1).widget()
        graphics_layout.removeWidget(placeholder)
        placeholder.deleteLater()
        graphics_layout.addWidget(self.view)

    def setup_history_panel(self):
        """Setup the history panel."""
        if not self.command_manager:
            return

        # Remove placeholder
        central_widget = self.centralWidget()
        main_layout = central_widget.layout()
        control_layout = main_layout.itemAt(1).layout()

        # Create history panel
        self.history_panel = HistoryPanel(self.command_manager, self)

        # Replace placeholder
        placeholder = control_layout.itemAt(1).widget()
        control_layout.removeWidget(placeholder)
        placeholder.deleteLater()
        control_layout.addWidget(self.history_panel)

        # Connect history panel signals
        self.history_panel.undo_requested.connect(self.perform_undo)
        self.history_panel.redo_requested.connect(self.perform_redo)

    def connect_signals(self):
        """Connect system signals."""
        if self.line_tool:
            self.line_tool.status_message.connect(self.status_label.setText)
            self.line_tool.coordinates_changed.connect(self.update_coordinates)

    def update_coordinates(self, x: float, y: float):
        """Update coordinate display."""
        self.coord_label.setText(f"Coordinates: ({x:.2f}, {y:.2f})")

    # Control event handlers
    def on_mode_changed(self, mode: str):
        """Handle line mode change."""
        if self.line_tool:
            self.line_tool.set_line_mode(mode)

    def on_ortho_toggled(self, checked: bool):
        """Handle orthogonal mode toggle."""
        if self.line_tool:
            self.line_tool.ortho_mode = checked
            mode_text = "ON" if checked else "OFF"
            self.status_label.setText(f"Orthogonal mode: {mode_text}")

    def on_snap_toggled(self, checked: bool):
        """Handle snap toggle."""
        if self.line_tool:
            self.line_tool.snap_enabled = checked
            snap_text = "ON" if checked else "OFF"
            self.status_label.setText(f"Snap: {snap_text}")

    def activate_line_tool(self):
        """Activate the line tool."""
        if self.tool_manager:
            success = self.tool_manager.activate_tool("line")
            if success:
                self.status_label.setText("Line tool activated")
            else:
                self.status_label.setText("Failed to activate line tool")

    def deactivate_tool(self):
        """Deactivate current tool."""
        if self.tool_manager and self.tool_manager.active_tool:
            self.tool_manager.active_tool.deactivate()
            self.status_label.setText("Tool deactivated")

    def clear_scene(self):
        """Clear the graphics scene."""
        if self.scene:
            self.scene.clear()
            self.status_label.setText("Scene cleared")

    def perform_undo(self):
        """Perform undo operation."""
        # This would be implemented with actual async calls in a real application
        self.status_label.setText("Undo requested (demo mode)")

    def perform_redo(self):
        """Perform redo operation."""
        # This would be implemented with actual async calls in a real application
        self.status_label.setText("Redo requested (demo mode)")

    # Demo functionality
    def start_demo(self):
        """Start automated demo."""
        if not self.line_tool or not self.tool_manager:
            return

        self.demo_step = 0
        self.tool_manager.activate_tool("line")
        self.demo_timer.timeout.connect(self.run_demo_step)
        self.demo_timer.start(2000)  # Demo step every 2 seconds

        self.status_label.setText("Starting automated demo...")

    def run_demo_step(self):
        """Run a demo step."""
        demo_steps = [
            lambda: self.simulate_click(100, 100),  # First line start
            lambda: self.simulate_click(200, 100),  # First line end
            lambda: self.simulate_click(200, 200),  # Second line start
            lambda: self.simulate_click(300, 200),  # Second line end
            lambda: self.switch_to_polyline(),  # Switch to polyline mode
            lambda: self.simulate_click(50, 50),  # Polyline start
            lambda: self.simulate_click(150, 50),  # Polyline point 2
            lambda: self.simulate_click(150, 150),  # Polyline point 3
            lambda: self.simulate_click(50, 150),  # Polyline point 4
            lambda: self.finish_polyline(),  # Finish polyline
        ]

        if self.demo_step < len(demo_steps):
            demo_steps[self.demo_step]()
            self.demo_step += 1
        else:
            self.demo_timer.stop()
            self.status_label.setText("Demo completed!")

    def simulate_click(self, x: float, y: float):
        """Simulate a mouse click at scene coordinates."""
        if self.view and self.line_tool:
            scene_point = self.scene.sceneRect().center()
            scene_point.setX(x)
            scene_point.setY(y)

            # Create mock mouse event
            view_point = self.view.mapFromScene(scene_point)
            mock_event = QMouseEvent(
                QMouseEvent.Type.MouseButtonPress,
                view_point,
                Qt.LeftButton,
                Qt.LeftButton,
                Qt.NoModifier,
            )

            self.line_tool.on_mouse_press(mock_event)
            self.status_label.setText(f"Demo: Clicked at ({x}, {y})")

    def switch_to_polyline(self):
        """Switch to polyline mode for demo."""
        if self.line_tool:
            self.line_tool.set_line_mode(LineMode.POLYLINE)
            self.mode_combo.setCurrentText("polyline")
            self.status_label.setText("Demo: Switched to polyline mode")

    def finish_polyline(self):
        """Finish polyline for demo."""
        if self.line_tool:
            self.line_tool._finish_polyline()
            self.status_label.setText("Demo: Finished polyline")

    def closeEvent(self, event):
        """Handle application close."""
        if self.demo_timer.isActive():
            self.demo_timer.stop()

        if self.api_client:
            self.api_client.shutdown()

        event.accept()


def main():
    """Run the line tool demo."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create Qt application
    app = QApplication(sys.argv)

    # Create and show demo window
    demo = LineToolDemo()
    demo.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
