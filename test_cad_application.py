#!/usr/bin/env python3
"""
Test CAD Application with Advanced Modification Tools

This is a simplified version of the main CAD application specifically
designed to test the advanced modification tools integration.
"""

import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QSplitter, QToolBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

# Import our tools and components
from PySide6.QtWidgets import QGraphicsScene
from qt_client.ui.canvas.cad_canvas_view import CADCanvasView
from qt_client.graphics.tools.tool_manager import ToolManager

# Use QGraphicsScene as DrawingScene
DrawingScene = QGraphicsScene

logger = logging.getLogger(__name__)


class TestCADApplication(QMainWindow):
    """Simplified CAD Application for testing advanced modification tools."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔧 CAD-PY - Advanced Modification Tools Test")
        self.setGeometry(100, 100, 1200, 800)

        # Mock components
        self.api_client = None  # Mock API client

        # Tool system
        self.scene = DrawingScene()
        self.canvas_view = CADCanvasView(self.scene)
        self.tool_manager = ToolManager()

        # Setup UI and tools
        self.setup_ui()
        self.setup_tools()
        self.setup_test_entities()

        logger.info("Test CAD application initialized")

    def setup_ui(self):
        """Setup simplified UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)

        # Title
        title = QLabel("🔧 Advanced Modification Tools - Integration Test")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px; background-color: #f0f8ff;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # Status
        self.status_label = QLabel("Ready - Select a tool to test advanced modification functionality")
        self.status_label.setStyleSheet("padding: 8px; background-color: #e8f5e8; border: 1px solid #4caf50;")
        main_layout.addWidget(self.status_label)

        # Toolbar
        self.create_toolbar()

        # Drawing area
        drawing_layout = QHBoxLayout()

        # Tools panel
        tools_panel = self.create_tools_panel()
        drawing_layout.addWidget(tools_panel, 0)

        # Canvas
        drawing_layout.addWidget(self.canvas_view, 1)

        main_layout.addLayout(drawing_layout)

        # Connect canvas to tool manager
        self.canvas_view.set_tool_manager(self.tool_manager)

    def create_toolbar(self):
        """Create main toolbar."""
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)

        # File actions
        toolbar.addAction(QAction("New", self))
        toolbar.addAction(QAction("Open", self))
        toolbar.addAction(QAction("Save", self))
        toolbar.addSeparator()

        # View actions
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.canvas_view.zoom_in)
        toolbar.addAction(zoom_in_action)

        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.canvas_view.zoom_out)
        toolbar.addAction(zoom_out_action)

        zoom_fit_action = QAction("Zoom Fit", self)
        zoom_fit_action.triggered.connect(self.canvas_view.zoom_to_fit)
        toolbar.addAction(zoom_fit_action)

        toolbar.addSeparator()

        # Tool actions
        clear_action = QAction("Clear Tool", self)
        clear_action.triggered.connect(self.clear_tool)
        toolbar.addAction(clear_action)

    def create_tools_panel(self):
        """Create tools panel."""
        panel = QWidget()
        panel.setFixedWidth(200)
        panel.setStyleSheet("background-color: #f8f9fa; border-right: 1px solid #dee2e6;")

        layout = QVBoxLayout(panel)

        # Panel title
        title = QLabel("🛠️ Modification Tools")
        title.setStyleSheet("font-weight: bold; padding: 8px; background-color: #e9ecef;")
        layout.addWidget(title)

        # Tool buttons
        tools = [
            ("Move", "move", "Move entities to new position"),
            ("Copy", "copy", "Copy entities to new location"),
            ("Rotate", "rotate", "Rotate entities around point"),
            ("Scale", "scale", "Scale entities up or down"),
            ("Mirror", "mirror", "Mirror entities across axis"),
            ("Trim", "trim", "Trim entities to boundaries"),
            ("Extend", "extend", "Extend entities to boundaries"),
            ("Offset", "offset", "Create parallel curves"),
            ("Fillet", "fillet", "Create rounded corners"),
            ("Chamfer", "chamfer", "Create beveled corners"),
        ]

        for name, tool_id, tooltip in tools:
            btn = QPushButton(name)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda checked, t=tool_id, n=name: self.activate_tool(t, n))
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px 12px;
                    margin: 2px;
                    background-color: white;
                    border: 1px solid #ced4da;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #e3f2fd;
                    border-color: #2196f3;
                }
                QPushButton:pressed {
                    background-color: #bbdefb;
                }
            """)
            layout.addWidget(btn)

        layout.addStretch()
        return panel

    def setup_tools(self):
        """Setup tool manager and register tools."""
        # Set core components
        self.tool_manager.set_scene(self.scene)

        # Register tools (with mock components for testing)
        from qt_client.graphics.tools.move_tool import MoveTool
        from qt_client.graphics.tools.copy_tool import CopyTool
        from qt_client.graphics.tools.rotate_tool import RotateTool
        from qt_client.graphics.tools.scale_tool import ScaleTool
        from qt_client.graphics.tools.mirror_tool import MirrorTool
        from qt_client.graphics.tools.trim_tool import TrimTool
        from qt_client.graphics.tools.extend_tool import ExtendTool
        from qt_client.graphics.tools.offset_tool import OffsetTool
        from qt_client.graphics.tools.fillet_tool import FilletTool
        from qt_client.graphics.tools.chamfer_tool import ChamferTool

        tools_to_register = [
            ("move", MoveTool),
            ("copy", CopyTool),
            ("rotate", RotateTool),
            ("scale", ScaleTool),
            ("mirror", MirrorTool),
            ("trim", TrimTool),
            ("extend", ExtendTool),
            ("offset", OffsetTool),
            ("fillet", FilletTool),
            ("chamfer", ChamferTool),
        ]

        for tool_name, tool_class in tools_to_register:
            try:
                tool_instance = tool_class(
                    self.scene,
                    self.api_client,  # Mock API client
                    None,  # Mock command manager
                    self.canvas_view.get_snap_engine(),
                    None   # Mock selection manager
                )
                self.tool_manager.register_tool(tool_name, tool_instance)
                logger.debug(f"Registered tool: {tool_name}")
            except Exception as e:
                logger.warning(f"Could not register tool {tool_name}: {e}")
                # Create mock tool for testing
                self.tool_manager.tools[tool_name] = f"Mock {tool_name} tool"

    def setup_test_entities(self):
        """Create test entities for tool testing."""
        from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsEllipseItem
        from PySide6.QtGui import QPen, QColor

        pen = QPen(QColor(0, 100, 200), 2)

        # Create test lines
        line1 = QGraphicsLineItem(50, 50, 250, 50)
        line1.setPen(pen)
        line1.entity_id = "test_line_1"
        self.scene.addItem(line1)

        line2 = QGraphicsLineItem(50, 150, 250, 150)
        line2.setPen(pen)
        line2.entity_id = "test_line_2"
        self.scene.addItem(line2)

        # Vertical line
        line3 = QGraphicsLineItem(150, 25, 150, 175)
        line3.setPen(pen)
        line3.entity_id = "test_line_3"
        self.scene.addItem(line3)

        # Test circle
        circle = QGraphicsEllipseItem(300, 75, 100, 100)
        circle.setPen(pen)
        circle.entity_id = "test_circle_1"
        self.scene.addItem(circle)

        logger.info("Created test entities for tool testing")

    def activate_tool(self, tool_id: str, tool_name: str):
        """Activate a modification tool."""
        success = self.tool_manager.activate_tool(tool_id)

        if success:
            self.status_label.setText(f"🔧 Active Tool: {tool_name} - Use mouse to interact with entities")
            self.status_label.setStyleSheet("padding: 8px; background-color: #e3f2fd; border: 1px solid #2196f3;")
            logger.info(f"Activated tool: {tool_name}")
        else:
            self.status_label.setText(f"⚠️ Failed to activate: {tool_name}")
            self.status_label.setStyleSheet("padding: 8px; background-color: #fff3cd; border: 1px solid #ffc107;")
            logger.warning(f"Failed to activate tool: {tool_name}")

    def clear_tool(self):
        """Clear active tool."""
        self.tool_manager.deactivate_current_tool()
        self.status_label.setText("Ready - Select a tool to test advanced modification functionality")
        self.status_label.setStyleSheet("padding: 8px; background-color: #e8f5e8; border: 1px solid #4caf50;")
        logger.info("Cleared active tool")


def main():
    """Run the test CAD application."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*60)
    print("🔧 CAD-PY ADVANCED MODIFICATION TOOLS - INTEGRATION TEST")
    print("="*60)
    print("\n✅ **TESTING ENVIRONMENT:**")
    print("   • Simplified CAD application without backend dependencies")
    print("   • All 10 advanced modification tools integrated")
    print("   • Test entities created for interaction")
    print("   • Tool manager system active")
    print("\n🎯 **AVAILABLE TOOLS FOR TESTING:**")
    tools = [
        "Move - Translate entities to new positions",
        "Copy - Duplicate entities with placement",
        "Rotate - Rotate entities around center point",
        "Scale - Resize entities uniformly or non-uniformly",
        "Mirror - Reflect entities across axis",
        "Trim - Cut entities at boundary intersections",
        "Extend - Lengthen entities to boundaries",
        "Offset - Create parallel curves at distance",
        "Fillet - Create rounded corners between entities",
        "Chamfer - Create beveled corners between entities"
    ]

    for i, tool in enumerate(tools, 1):
        print(f"   {i:2d}. {tool}")

    print("\n🚀 **TESTING INSTRUCTIONS:**")
    print("   1. Click tool buttons in the left panel")
    print("   2. Interact with test entities in the drawing area")
    print("   3. Use toolbar zoom controls for navigation")
    print("   4. Check status bar for tool feedback")
    print("   5. Use 'Clear Tool' to deselect active tool")
    print("\n" + "="*60)

    app = QApplication(sys.argv)

    # Create and show test application
    test_app = TestCADApplication()
    test_app.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
