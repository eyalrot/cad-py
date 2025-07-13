"""
Demo application for circle and arc drawing tools.

This example shows how to use both circle and arc tools with all their
different modes and demonstrates the integration with the CAD system.
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
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.api_client import APIClientManager
from ...core.command_manager import CommandManager
from ...core.snap_engine import SnapEngine
from .arc_tool import ArcMode, ArcTool
from .base_tool import ToolManager
from .circle_tool import CircleMode, CircleTool


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


class CircleArcDemo(QMainWindow):
    """Demo application for circle and arc drawing tools."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAD Circle and Arc Tools Demo")
        self.setGeometry(100, 100, 1400, 900)

        # Initialize systems
        self.api_client: Optional[APIClientManager] = None
        self.command_manager: Optional[CommandManager] = None
        self.snap_engine: Optional[SnapEngine] = None
        self.tool_manager: Optional[ToolManager] = None
        self.circle_tool: Optional[CircleTool] = None
        self.arc_tool: Optional[ArcTool] = None

        # UI components
        self.scene: Optional[QGraphicsScene] = None
        self.view: Optional[CADGraphicsView] = None

        # Status tracking
        self.current_document_id = "demo-doc-123"
        self.current_layer_id = "layer-0"

        # Demo state
        self.demo_timer = QTimer()
        self.demo_step = 0
        self.current_demo_tool = None

        # Setup
        self.setup_ui()
        self.initialize_systems()

    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # Left side - graphics view
        self.setup_graphics_area(main_layout)

        # Right side - tool controls
        self.setup_control_area(main_layout)

    def setup_graphics_area(self, main_layout: QHBoxLayout):
        """Setup the graphics drawing area."""
        graphics_layout = QVBoxLayout()

        # Create scene
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-600, -400, 1200, 800)

        # Status labels
        status_layout = QHBoxLayout()
        self.coord_label = QLabel("Coordinates: (0, 0)")
        self.status_label = QLabel("Ready")
        status_layout.addWidget(self.coord_label)
        status_layout.addStretch()
        status_layout.addWidget(self.status_label)

        graphics_layout.addLayout(status_layout)
        graphics_layout.addWidget(
            QLabel("Graphics view will be added after initialization")
        )

        main_layout.addLayout(graphics_layout, 2)  # 2/3 of the space

    def setup_control_area(self, main_layout: QHBoxLayout):
        """Setup the control area with tabs for different tools."""
        control_widget = QWidget()
        control_layout = QVBoxLayout(control_widget)

        # Create tab widget for tools
        self.tool_tabs = QTabWidget()

        # Circle tool tab
        self.setup_circle_tab()

        # Arc tool tab
        self.setup_arc_tab()

        # General controls tab
        self.setup_general_tab()

        control_layout.addWidget(self.tool_tabs)

        # Demo controls
        demo_group = QGroupBox("Demo Controls")
        demo_layout = QVBoxLayout(demo_group)

        self.demo_circle_btn = QPushButton("Run Circle Demo")
        self.demo_circle_btn.clicked.connect(self.start_circle_demo)
        demo_layout.addWidget(self.demo_circle_btn)

        self.demo_arc_btn = QPushButton("Run Arc Demo")
        self.demo_arc_btn.clicked.connect(self.start_arc_demo)
        demo_layout.addWidget(self.demo_arc_btn)

        self.clear_btn = QPushButton("Clear Scene")
        self.clear_btn.clicked.connect(self.clear_scene)
        demo_layout.addWidget(self.clear_btn)

        control_layout.addWidget(demo_group)

        main_layout.addWidget(control_widget, 1)  # 1/3 of the space

    def setup_circle_tab(self):
        """Setup the circle tool controls tab."""
        circle_widget = QWidget()
        layout = QVBoxLayout(circle_widget)

        # Circle mode selection
        mode_group = QGroupBox("Circle Mode")
        mode_layout = QVBoxLayout(mode_group)

        self.circle_mode_combo = QComboBox()
        self.circle_mode_combo.addItems(["center_radius", "two_point", "three_point"])
        self.circle_mode_combo.currentTextChanged.connect(self.on_circle_mode_changed)
        mode_layout.addWidget(self.circle_mode_combo)

        layout.addWidget(mode_group)

        # Circle tool buttons
        button_group = QGroupBox("Circle Tools")
        button_layout = QVBoxLayout(button_group)

        self.activate_circle_btn = QPushButton("Activate Circle Tool")
        self.activate_circle_btn.clicked.connect(self.activate_circle_tool)
        button_layout.addWidget(self.activate_circle_btn)

        # Mode descriptions
        desc_group = QGroupBox("Mode Descriptions")
        desc_layout = QVBoxLayout(desc_group)

        desc_layout.addWidget(QLabel("Center-Radius: Click center, then radius point"))
        desc_layout.addWidget(QLabel("Two-Point: Click two points for diameter"))
        desc_layout.addWidget(
            QLabel("Three-Point: Click three points on circumference")
        )
        desc_layout.addWidget(QLabel(""))
        desc_layout.addWidget(QLabel("Hotkeys: 1, 2, 3 for modes; M to cycle"))

        layout.addWidget(button_group)
        layout.addWidget(desc_group)
        layout.addStretch()

        self.tool_tabs.addTab(circle_widget, "Circle Tool")

    def setup_arc_tab(self):
        """Setup the arc tool controls tab."""
        arc_widget = QWidget()
        layout = QVBoxLayout(arc_widget)

        # Arc mode selection
        mode_group = QGroupBox("Arc Mode")
        mode_layout = QVBoxLayout(mode_group)

        self.arc_mode_combo = QComboBox()
        self.arc_mode_combo.addItems(
            ["three_point", "start_center_end", "center_start_end"]
        )
        self.arc_mode_combo.currentTextChanged.connect(self.on_arc_mode_changed)
        mode_layout.addWidget(self.arc_mode_combo)

        layout.addWidget(mode_group)

        # Arc tool buttons
        button_group = QGroupBox("Arc Tools")
        button_layout = QVBoxLayout(button_group)

        self.activate_arc_btn = QPushButton("Activate Arc Tool")
        self.activate_arc_btn.clicked.connect(self.activate_arc_tool)
        button_layout.addWidget(self.activate_arc_btn)

        # Mode descriptions
        desc_group = QGroupBox("Mode Descriptions")
        desc_layout = QVBoxLayout(desc_group)

        desc_layout.addWidget(QLabel("Three-Point: Click three points on arc"))
        desc_layout.addWidget(QLabel("Start-Center-End: Start, center, end"))
        desc_layout.addWidget(QLabel("Center-Start-End: Center, start, end"))
        desc_layout.addWidget(QLabel(""))
        desc_layout.addWidget(QLabel("Hotkeys: 1, 2, 3 for modes; M to cycle"))

        layout.addWidget(button_group)
        layout.addWidget(desc_group)
        layout.addStretch()

        self.tool_tabs.addTab(arc_widget, "Arc Tool")

    def setup_general_tab(self):
        """Setup general tool controls."""
        general_widget = QWidget()
        layout = QVBoxLayout(general_widget)

        # General options
        options_group = QGroupBox("Tool Options")
        options_layout = QVBoxLayout(options_group)

        self.ortho_checkbox = QCheckBox("Orthogonal Mode")
        self.ortho_checkbox.toggled.connect(self.on_ortho_toggled)
        options_layout.addWidget(self.ortho_checkbox)

        self.snap_checkbox = QCheckBox("Snap Enabled")
        self.snap_checkbox.setChecked(True)
        self.snap_checkbox.toggled.connect(self.on_snap_toggled)
        options_layout.addWidget(self.snap_checkbox)

        self.preview_checkbox = QCheckBox("Preview Enabled")
        self.preview_checkbox.setChecked(True)
        self.preview_checkbox.toggled.connect(self.on_preview_toggled)
        options_layout.addWidget(self.preview_checkbox)

        layout.addWidget(options_group)

        # Tool actions
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout(actions_group)

        self.deactivate_btn = QPushButton("Deactivate Tool")
        self.deactivate_btn.clicked.connect(self.deactivate_tool)
        actions_layout.addWidget(self.deactivate_btn)

        layout.addWidget(actions_group)
        layout.addStretch()

        self.tool_tabs.addTab(general_widget, "General")

    def initialize_systems(self):
        """Initialize the CAD systems."""
        try:
            # Create API client
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

            # Create tools
            self.circle_tool = CircleTool(
                self.scene,
                self.api_client,
                self.command_manager,
                self.snap_engine,
                self,
            )

            self.arc_tool = ArcTool(
                self.scene,
                self.api_client,
                self.command_manager,
                self.snap_engine,
                self,
            )

            # Register tools
            self.tool_manager.register_tool(self.circle_tool)
            self.tool_manager.register_tool(self.arc_tool)

            # Set document context
            self.tool_manager.set_document_context(
                self.current_document_id, self.current_layer_id
            )

            # Create actual graphics view
            self.setup_actual_graphics_view()

            # Connect signals
            self.connect_signals()

            self.status_label.setText("Systems initialized - Ready to draw")

        except Exception as e:
            logging.error(f"Failed to initialize systems: {e}")
            self.status_label.setText(f"Initialization failed: {e}")

    def setup_actual_graphics_view(self):
        """Setup the actual graphics view."""
        # Remove placeholder
        central_widget = self.centralWidget()
        main_layout = central_widget.layout()
        graphics_layout = main_layout.itemAt(0).layout()

        # Create actual view
        self.view = CADGraphicsView(self.scene, self.tool_manager, self)
        self.view.setMinimumSize(800, 600)

        # Replace placeholder
        placeholder = graphics_layout.itemAt(1).widget()
        graphics_layout.removeWidget(placeholder)
        placeholder.deleteLater()
        graphics_layout.addWidget(self.view)

    def connect_signals(self):
        """Connect system signals."""
        if self.circle_tool:
            self.circle_tool.status_message.connect(self.status_label.setText)
            self.circle_tool.coordinates_changed.connect(self.update_coordinates)

        if self.arc_tool:
            self.arc_tool.status_message.connect(self.status_label.setText)
            self.arc_tool.coordinates_changed.connect(self.update_coordinates)

    def update_coordinates(self, x: float, y: float):
        """Update coordinate display."""
        self.coord_label.setText(f"Coordinates: ({x:.2f}, {y:.2f})")

    # Control event handlers
    def on_circle_mode_changed(self, mode: str):
        """Handle circle mode change."""
        if self.circle_tool:
            self.circle_tool.set_circle_mode(mode)

    def on_arc_mode_changed(self, mode: str):
        """Handle arc mode change."""
        if self.arc_tool:
            self.arc_tool.set_arc_mode(mode)

    def on_ortho_toggled(self, checked: bool):
        """Handle orthogonal mode toggle."""
        if self.tool_manager and self.tool_manager.active_tool:
            self.tool_manager.active_tool.ortho_mode = checked

    def on_snap_toggled(self, checked: bool):
        """Handle snap toggle."""
        if self.tool_manager and self.tool_manager.active_tool:
            self.tool_manager.active_tool.snap_enabled = checked

    def on_preview_toggled(self, checked: bool):
        """Handle preview toggle."""
        if self.tool_manager and self.tool_manager.active_tool:
            self.tool_manager.active_tool.preview_enabled = checked

    def activate_circle_tool(self):
        """Activate the circle tool."""
        if self.tool_manager:
            success = self.tool_manager.activate_tool("circle")
            if success:
                self.status_label.setText("Circle tool activated")
                self.tool_tabs.setCurrentIndex(0)  # Switch to circle tab
            else:
                self.status_label.setText("Failed to activate circle tool")

    def activate_arc_tool(self):
        """Activate the arc tool."""
        if self.tool_manager:
            success = self.tool_manager.activate_tool("arc")
            if success:
                self.status_label.setText("Arc tool activated")
                self.tool_tabs.setCurrentIndex(1)  # Switch to arc tab
            else:
                self.status_label.setText("Failed to activate arc tool")

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

    # Demo functionality
    def start_circle_demo(self):
        """Start automated circle demo."""
        if not self.circle_tool or not self.tool_manager:
            return

        self.current_demo_tool = "circle"
        self.demo_step = 0
        self.tool_manager.activate_tool("circle")
        self.demo_timer.timeout.connect(self.run_circle_demo_step)
        self.demo_timer.start(2500)  # Demo step every 2.5 seconds

        self.status_label.setText("Starting circle demo...")

    def run_circle_demo_step(self):
        """Run a circle demo step."""
        demo_steps = [
            # Center-radius circles
            lambda: self.set_circle_mode_and_message(
                CircleMode.CENTER_RADIUS, "Center-radius mode"
            ),
            lambda: self.simulate_click(0, 0),  # Center
            lambda: self.simulate_click(50, 0),  # Radius point
            # Two-point circle
            lambda: self.set_circle_mode_and_message(
                CircleMode.TWO_POINT, "Two-point diameter mode"
            ),
            lambda: self.simulate_click(-100, 100),  # Diameter point 1
            lambda: self.simulate_click(100, 100),  # Diameter point 2
            # Three-point circle
            lambda: self.set_circle_mode_and_message(
                CircleMode.THREE_POINT, "Three-point mode"
            ),
            lambda: self.simulate_click(-50, -100),  # Point 1
            lambda: self.simulate_click(50, -100),  # Point 2
            lambda: self.simulate_click(0, -50),  # Point 3
        ]

        if self.demo_step < len(demo_steps):
            demo_steps[self.demo_step]()
            self.demo_step += 1
        else:
            self.demo_timer.stop()
            self.demo_timer.timeout.disconnect()
            self.status_label.setText("Circle demo completed!")

    def start_arc_demo(self):
        """Start automated arc demo."""
        if not self.arc_tool or not self.tool_manager:
            return

        self.current_demo_tool = "arc"
        self.demo_step = 0
        self.tool_manager.activate_tool("arc")
        self.demo_timer.timeout.connect(self.run_arc_demo_step)
        self.demo_timer.start(2500)  # Demo step every 2.5 seconds

        self.status_label.setText("Starting arc demo...")

    def run_arc_demo_step(self):
        """Run an arc demo step."""
        demo_steps = [
            # Three-point arc
            lambda: self.set_arc_mode_and_message(
                ArcMode.THREE_POINT, "Three-point arc"
            ),
            lambda: self.simulate_click(-200, 0),  # Point 1
            lambda: self.simulate_click(-150, 50),  # Point 2
            lambda: self.simulate_click(-100, 0),  # Point 3
            # Start-center-end arc
            lambda: self.set_arc_mode_and_message(
                ArcMode.START_CENTER_END, "Start-center-end arc"
            ),
            lambda: self.simulate_click(200, 0),  # Start point
            lambda: self.simulate_click(150, 0),  # Center
            lambda: self.simulate_click(150, 50),  # End point
            # Center-start-end arc
            lambda: self.set_arc_mode_and_message(
                ArcMode.CENTER_START_END, "Center-start-end arc"
            ),
            lambda: self.simulate_click(0, 200),  # Center
            lambda: self.simulate_click(-50, 200),  # Start point
            lambda: self.simulate_click(0, 150),  # End point
        ]

        if self.demo_step < len(demo_steps):
            demo_steps[self.demo_step]()
            self.demo_step += 1
        else:
            self.demo_timer.stop()
            self.demo_timer.timeout.disconnect()
            self.status_label.setText("Arc demo completed!")

    def set_circle_mode_and_message(self, mode: str, message: str):
        """Set circle mode and show message."""
        if self.circle_tool:
            self.circle_tool.set_circle_mode(mode)
            self.circle_mode_combo.setCurrentText(mode)
            self.status_label.setText(f"Demo: {message}")

    def set_arc_mode_and_message(self, mode: str, message: str):
        """Set arc mode and show message."""
        if self.arc_tool:
            self.arc_tool.set_arc_mode(mode)
            self.arc_mode_combo.setCurrentText(mode)
            self.status_label.setText(f"Demo: {message}")

    def simulate_click(self, x: float, y: float):
        """Simulate a mouse click at scene coordinates."""
        if self.view and self.tool_manager.active_tool:
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

            self.tool_manager.active_tool.on_mouse_press(mock_event)
            self.status_label.setText(f"Demo: Clicked at ({x}, {y})")

    def closeEvent(self, event):
        """Handle application close."""
        if self.demo_timer.isActive():
            self.demo_timer.stop()

        if self.api_client:
            self.api_client.shutdown()

        event.accept()


def main():
    """Run the circle and arc tools demo."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create Qt application
    app = QApplication(sys.argv)

    # Create and show demo window
    demo = CircleArcDemo()
    demo.show()

    # Run application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
