#!/usr/bin/env python3
"""
Advanced Modification Tools Demo

This demo showcases all the advanced modification tools implemented in Task 14:
- TrimTool: Trim entities to boundaries
- ExtendTool: Extend entities to boundaries
- OffsetTool: Create parallel curves
- FilletTool: Create rounded corners
- ChamferTool: Create beveled corners

Run this demo to see interactive examples of each tool's capabilities.
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer

from qt_client.graphics.drawing_view import DrawingView
from qt_client.graphics.drawing_scene import DrawingScene
from qt_client.core.api_client import APIClient
from qt_client.core.command_manager import CommandManager
from qt_client.core.snap_engine import SnapEngine
from qt_client.core.selection_manager import SelectionManager

# Import all advanced modification tools
from qt_client.graphics.tools.trim_tool import TrimTool
from qt_client.graphics.tools.extend_tool import ExtendTool
from qt_client.graphics.tools.offset_tool import OffsetTool
from qt_client.graphics.tools.fillet_tool import FilletTool
from qt_client.graphics.tools.chamfer_tool import ChamferTool

logger = logging.getLogger(__name__)


class AdvancedToolsDemo(QMainWindow):
    """Demo application for advanced modification tools."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced Modification Tools Demo - CAD-PY")
        self.setGeometry(100, 100, 1200, 800)

        # Initialize core components
        self.api_client = APIClient("http://localhost:8000")
        self.command_manager = CommandManager()
        self.snap_engine = SnapEngine()
        self.selection_manager = SelectionManager()

        # Create scene and view
        self.scene = DrawingScene()
        self.view = DrawingView(self.scene)

        # Initialize tools
        self.tools = {
            'trim': TrimTool(self.scene, self.api_client, self.command_manager,
                           self.snap_engine, self.selection_manager),
            'extend': ExtendTool(self.scene, self.api_client, self.command_manager,
                               self.snap_engine, self.selection_manager),
            'offset': OffsetTool(self.scene, self.api_client, self.command_manager,
                               self.snap_engine, self.selection_manager),
            'fillet': FilletTool(self.scene, self.api_client, self.command_manager,
                               self.snap_engine, self.selection_manager),
            'chamfer': ChamferTool(self.scene, self.api_client, self.command_manager,
                                 self.snap_engine, self.selection_manager)
        }

        self.current_tool = None
        self.setup_ui()
        self.create_demo_entities()

        logger.info("Advanced modification tools demo initialized")

    def setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Tool selection buttons
        tool_layout = QHBoxLayout()

        # Title
        title = QLabel("Advanced Modification Tools Demo")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)

        # Tool buttons
        tool_buttons = [
            ("Trim Tool", "trim", "Trim entities to cutting boundaries"),
            ("Extend Tool", "extend", "Extend entities to boundary limits"),
            ("Offset Tool", "offset", "Create parallel curves at distance"),
            ("Fillet Tool", "fillet", "Create rounded corners between entities"),
            ("Chamfer Tool", "chamfer", "Create beveled corners between entities")
        ]

        for name, tool_key, tooltip in tool_buttons:
            btn = QPushButton(name)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda checked, t=tool_key: self.select_tool(t))
            tool_layout.addWidget(btn)

        # Clear tool button
        clear_btn = QPushButton("Clear Tool")
        clear_btn.clicked.connect(self.clear_tool)
        tool_layout.addWidget(clear_btn)

        layout.addLayout(tool_layout)

        # Status label
        self.status_label = QLabel("Select a tool to begin demonstration")
        self.status_label.setStyleSheet("padding: 5px; background-color: #f0f0f0;")
        layout.addWidget(self.status_label)

        # Drawing view
        layout.addWidget(self.view)

        # Instructions
        instructions = QLabel(
            "Instructions:\n"
            "• Select a tool from the buttons above\n"
            "• Follow the status text for tool-specific guidance\n"
            "• Use Escape to cancel operations\n"
            "• Use Ctrl+Z/Ctrl+Y for undo/redo"
        )
        instructions.setStyleSheet("padding: 10px; background-color: #e8f4f8; border: 1px solid #b8d4e3;")
        layout.addWidget(instructions)

        # Setup timer for status updates
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(100)  # Update every 100ms

    def create_demo_entities(self):
        """Create some demo entities for testing the tools."""
        # This would normally create actual entities through the API
        # For demo purposes, we'll create placeholder graphics items
        from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsEllipseItem
        from PySide6.QtGui import QPen, QColor
        from PySide6.QtCore import QPointF

        # Create some demo lines for testing
        pen = QPen(QColor(0, 0, 255), 2)

        # Horizontal lines
        line1 = QGraphicsLineItem(50, 100, 250, 100)
        line1.setPen(pen)
        line1.entity_id = "demo_line_1"
        self.scene.addItem(line1)

        line2 = QGraphicsLineItem(50, 200, 250, 200)
        line2.setPen(pen)
        line2.entity_id = "demo_line_2"
        self.scene.addItem(line2)

        # Vertical lines
        line3 = QGraphicsLineItem(150, 50, 150, 250)
        line3.setPen(pen)
        line3.entity_id = "demo_line_3"
        self.scene.addItem(line3)

        # Diagonal line
        line4 = QGraphicsLineItem(300, 50, 400, 150)
        line4.setPen(pen)
        line4.entity_id = "demo_line_4"
        self.scene.addItem(line4)

        # Circle for testing
        circle = QGraphicsEllipseItem(350, 180, 80, 80)
        circle.setPen(pen)
        circle.entity_id = "demo_circle_1"
        self.scene.addItem(circle)

        logger.info("Created demo entities for testing advanced tools")

    def select_tool(self, tool_name: str):
        """Select and activate a tool."""
        # Deactivate current tool
        if self.current_tool:
            self.current_tool.deactivate()

        # Activate new tool
        self.current_tool = self.tools[tool_name]
        self.current_tool.activate()

        # Connect tool to view
        self.view.set_active_tool(self.current_tool)

        logger.info(f"Activated {tool_name} tool")

    def clear_tool(self):
        """Clear the current tool."""
        if self.current_tool:
            self.current_tool.deactivate()
            self.current_tool = None

        self.view.set_active_tool(None)
        logger.info("Cleared active tool")

    def update_status(self):
        """Update status display."""
        if self.current_tool:
            status_text = f"{self.current_tool.get_tool_name()}: {self.current_tool.get_status_text()}"
        else:
            status_text = "No tool selected - Choose a tool to begin"

        self.status_label.setText(status_text)


async def main():
    """Main demo function."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create application
    app = QApplication(sys.argv)

    # Create and show demo window
    demo = AdvancedToolsDemo()
    demo.show()

    logger.info("Advanced Modification Tools Demo started")
    logger.info("Available tools: Trim, Extend, Offset, Fillet, Chamfer")

    # Show tool capabilities
    print("\n" + "="*60)
    print("ADVANCED MODIFICATION TOOLS DEMO")
    print("="*60)
    print("\n🔧 IMPLEMENTED TOOLS:")
    print("  • TrimTool    - Trim entities to boundaries with visual feedback")
    print("  • ExtendTool  - Extend entities to boundaries with preview")
    print("  • OffsetTool  - Create parallel curves with distance input")
    print("  • FilletTool  - Create rounded corners with radius control")
    print("  • ChamferTool - Create beveled corners with distance settings")

    print("\n⚡ KEY FEATURES:")
    print("  • Interactive state management")
    print("  • Real-time visual previews")
    print("  • Snap integration for precision")
    print("  • Command pattern for undo/redo")
    print("  • Comprehensive error handling")

    print("\n🎯 USAGE:")
    print("  1. Click a tool button to activate")
    print("  2. Follow the status text instructions")
    print("  3. Use demo entities to test functionality")
    print("  4. Press Escape to cancel operations")

    print("\n📋 DEMO ENTITIES CREATED:")
    print("  • Horizontal lines for trimming/extending")
    print("  • Vertical lines for intersection testing")
    print("  • Diagonal line for angle operations")
    print("  • Circle for offset testing")

    print("\n" + "="*60)

    # Run the application
    app.exec()


if __name__ == "__main__":
    asyncio.run(main())
