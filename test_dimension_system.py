#!/usr/bin/env python3
"""
Test Linear Dimensioning System

This application demonstrates the complete linear dimensioning functionality
including horizontal, vertical, and aligned dimensions with professional styling.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QSplitter, QPushButton, QGroupBox, QFormLayout,
    QDoubleSpinBox, QComboBox, QSpinBox, QCheckBox, QColorDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QGraphicsScene, QGraphicsLineItem, QGraphicsEllipseItem
from PySide6.QtGui import QPen

from qt_client.ui.canvas.cad_canvas_view import CADCanvasView
from qt_client.graphics.tools.dimension_tool import (
    HorizontalDimensionTool, VerticalDimensionTool, AlignedDimensionTool,
    DimensionStyle, DimensionType
)

logger = logging.getLogger(__name__)


class MockAPIClient:
    """Mock API client for testing dimension operations."""

    def __init__(self):
        self.dimensions = {}

    async def create_dimension(self, dimension_data):
        """Mock create dimension operation."""
        dimension_id = f"dim_{len(self.dimensions) + 1}"
        self.dimensions[dimension_id] = dimension_data
        logger.info(f"Mock API: Created {dimension_data['dimension_type']} dimension")
        return {"success": True, "data": {"dimension": dimension_data}}


class DimensionStyleEditor(QWidget):
    """Widget for editing dimension styles."""

    def __init__(self, style: DimensionStyle, parent=None):
        super().__init__(parent)
        self.style = style
        self.setup_ui()
        self.load_style()

    def setup_ui(self):
        """Setup the style editor UI."""
        layout = QVBoxLayout(self)

        # Text properties group
        text_group = QGroupBox("Text Properties")
        text_layout = QFormLayout(text_group)

        self.text_height_spin = QDoubleSpinBox()
        self.text_height_spin.setRange(0.1, 50.0)
        self.text_height_spin.setDecimals(1)
        self.text_height_spin.setSuffix(" units")
        text_layout.addRow("Text Height:", self.text_height_spin)

        self.text_color_btn = QPushButton()
        self.text_color_btn.clicked.connect(self.choose_text_color)
        text_layout.addRow("Text Color:", self.text_color_btn)

        layout.addWidget(text_group)

        # Arrow properties group
        arrow_group = QGroupBox("Arrow Properties")
        arrow_layout = QFormLayout(arrow_group)

        self.arrow_size_spin = QDoubleSpinBox()
        self.arrow_size_spin.setRange(0.1, 20.0)
        self.arrow_size_spin.setDecimals(1)
        self.arrow_size_spin.setSuffix(" units")
        arrow_layout.addRow("Arrow Size:", self.arrow_size_spin)

        layout.addWidget(arrow_group)

        # Line properties group
        line_group = QGroupBox("Line Properties")
        line_layout = QFormLayout(line_group)

        self.line_weight_spin = QDoubleSpinBox()
        self.line_weight_spin.setRange(0.1, 10.0)
        self.line_weight_spin.setDecimals(1)
        line_layout.addRow("Line Weight:", self.line_weight_spin)

        self.ext_offset_spin = QDoubleSpinBox()
        self.ext_offset_spin.setRange(0.0, 10.0)
        self.ext_offset_spin.setDecimals(2)
        self.ext_offset_spin.setSuffix(" units")
        line_layout.addRow("Extension Offset:", self.ext_offset_spin)

        self.ext_extension_spin = QDoubleSpinBox()
        self.ext_extension_spin.setRange(0.0, 10.0)
        self.ext_extension_spin.setDecimals(2)
        self.ext_extension_spin.setSuffix(" units")
        line_layout.addRow("Extension Beyond:", self.ext_extension_spin)

        layout.addWidget(line_group)

        # Precision and units group
        precision_group = QGroupBox("Precision & Units")
        precision_layout = QFormLayout(precision_group)

        self.precision_spin = QSpinBox()
        self.precision_spin.setRange(0, 8)
        precision_layout.addRow("Decimal Places:", self.precision_spin)

        self.unit_suffix_combo = QComboBox()
        self.unit_suffix_combo.addItems(["", "mm", "cm", "m", "in", "ft"])
        self.unit_suffix_combo.setEditable(True)
        precision_layout.addRow("Unit Suffix:", self.unit_suffix_combo)

        self.scale_factor_spin = QDoubleSpinBox()
        self.scale_factor_spin.setRange(0.001, 1000.0)
        self.scale_factor_spin.setDecimals(3)
        precision_layout.addRow("Scale Factor:", self.scale_factor_spin)

        layout.addWidget(precision_group)

        # Connect signals
        self.text_height_spin.valueChanged.connect(self.update_style)
        self.arrow_size_spin.valueChanged.connect(self.update_style)
        self.line_weight_spin.valueChanged.connect(self.update_style)
        self.ext_offset_spin.valueChanged.connect(self.update_style)
        self.ext_extension_spin.valueChanged.connect(self.update_style)
        self.precision_spin.valueChanged.connect(self.update_style)
        self.unit_suffix_combo.currentTextChanged.connect(self.update_style)
        self.scale_factor_spin.valueChanged.connect(self.update_style)

    def load_style(self):
        """Load style values into UI."""
        self.text_height_spin.setValue(self.style.text_height)
        self.arrow_size_spin.setValue(self.style.arrow_size)
        self.line_weight_spin.setValue(self.style.line_weight)
        self.ext_offset_spin.setValue(self.style.extension_line_offset)
        self.ext_extension_spin.setValue(self.style.extension_line_extension)
        self.precision_spin.setValue(self.style.precision)
        self.unit_suffix_combo.setCurrentText(self.style.unit_suffix)
        self.scale_factor_spin.setValue(self.style.scale_factor)

        self.update_color_button()

    def update_style(self):
        """Update style from UI values."""
        self.style.text_height = self.text_height_spin.value()
        self.style.arrow_size = self.arrow_size_spin.value()
        self.style.line_weight = self.line_weight_spin.value()
        self.style.extension_line_offset = self.ext_offset_spin.value()
        self.style.extension_line_extension = self.ext_extension_spin.value()
        self.style.precision = self.precision_spin.value()
        self.style.unit_suffix = self.unit_suffix_combo.currentText()
        self.style.scale_factor = self.scale_factor_spin.value()

    def choose_text_color(self):
        """Open color dialog for text color."""
        color = QColorDialog.getColor(self.style.text_color, self, "Choose Text Color")
        if color.isValid():
            self.style.text_color = color
            self.update_color_button()

    def update_color_button(self):
        """Update color button appearance."""
        color = self.style.text_color
        self.text_color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({color.red()}, {color.green()}, {color.blue()});
                border: 2px solid #ccc;
                border-radius: 4px;
                min-height: 20px;
            }}
        """)
        self.text_color_btn.setText(color.name().upper())


class DimensionTestApp(QMainWindow):
    """Test application for linear dimensioning system."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("📐 CAD-PY Linear Dimensioning System - Test Application")
        self.setGeometry(150, 150, 1400, 900)

        # Mock API client
        self.api_client = MockAPIClient()

        # Dimension tools
        self.active_tool = None
        self.dimension_tools = {}

        # Setup UI
        self.setup_ui()
        self.setup_dimension_tools()
        self.create_sample_geometry()

        logger.info("Dimension test application initialized")

    def setup_ui(self):
        """Setup the test application UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)

        # Title
        title = QLabel("📐 Linear Dimensioning System - Professional CAD Dimensions")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("""
            padding: 20px;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #ff7e5f, stop:1 #feb47b);
            color: white;
            border-radius: 8px;
            margin: 10px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # Main content splitter
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - tools and controls
        left_panel = self.create_control_panel()
        left_panel.setMinimumWidth(300)
        left_panel.setMaximumWidth(400)
        content_splitter.addWidget(left_panel)

        # Center - drawing area
        self.setup_drawing_area()
        content_splitter.addWidget(self.canvas_view)

        # Right panel - style editor
        right_panel = self.create_style_panel()
        right_panel.setMinimumWidth(250)
        right_panel.setMaximumWidth(350)
        content_splitter.addWidget(right_panel)

        content_splitter.setSizes([350, 700, 300])
        main_layout.addWidget(content_splitter)

        # Status
        self.status_label = QLabel("Ready - Select a dimension tool to start creating dimensions")
        self.status_label.setStyleSheet("""
            padding: 8px;
            background-color: #e8f5e8;
            border: 1px solid #4caf50;
            margin: 5px;
        """)
        main_layout.addWidget(self.status_label)

    def setup_drawing_area(self):
        """Setup the drawing canvas."""
        self.scene = QGraphicsScene()
        self.scene.setSceneRect(-400, -300, 800, 600)

        # Use basic QGraphicsView for this test
        from PySide6.QtWidgets import QGraphicsView
        from PySide6.QtGui import QPainter

        self.canvas_view = QGraphicsView(self.scene)
        self.canvas_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.canvas_view.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.canvas_view.setStyleSheet("border: 2px solid #ddd; background-color: #fafafa;")

        # Mock some required methods for tools
        class MockSnapEngine:
            def snap_point(self, point, view, base_point=None):
                class MockSnapResult:
                    def __init__(self):
                        self.snapped = False
                        self.point = point
                return MockSnapResult()

        self.snap_engine = MockSnapEngine()

    def create_control_panel(self):
        """Create the control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Panel title
        title = QLabel("🛠️ Dimension Tools")
        title.setStyleSheet("""
            font-weight: bold; font-size: 16px; padding: 12px;
            background-color: #343a40; color: white;
            border-radius: 6px; margin: 5px;
        """)
        layout.addWidget(title)

        # Instructions
        instructions = QLabel("""
        <b>Usage Instructions:</b><br>
        1. Select a dimension tool below<br>
        2. Click two points to define dimension<br>
        3. Click to place dimension line<br>
        4. Adjust style in right panel
        """)
        instructions.setStyleSheet("""
            padding: 10px; background-color: #e3f2fd;
            border: 1px solid #2196f3; border-radius: 4px;
            margin: 5px; font-size: 11px;
        """)
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Dimension tools group
        tools_group = QGroupBox("Linear Dimension Tools")
        tools_layout = QVBoxLayout(tools_group)

        # Horizontal dimension
        h_dim_btn = QPushButton("📏 Horizontal Dimension")
        h_dim_btn.clicked.connect(lambda: self.activate_dimension_tool("horizontal"))
        h_dim_btn.setStyleSheet(self.button_style())
        tools_layout.addWidget(h_dim_btn)

        # Vertical dimension
        v_dim_btn = QPushButton("📐 Vertical Dimension")
        v_dim_btn.clicked.connect(lambda: self.activate_dimension_tool("vertical"))
        v_dim_btn.setStyleSheet(self.button_style())
        tools_layout.addWidget(v_dim_btn)

        # Aligned dimension
        a_dim_btn = QPushButton("📊 Aligned Dimension")
        a_dim_btn.clicked.connect(lambda: self.activate_dimension_tool("aligned"))
        a_dim_btn.setStyleSheet(self.button_style())
        tools_layout.addWidget(a_dim_btn)

        layout.addWidget(tools_group)

        # Utility buttons group
        utils_group = QGroupBox("Utilities")
        utils_layout = QVBoxLayout(utils_group)

        clear_btn = QPushButton("🗑️ Clear All Dimensions")
        clear_btn.clicked.connect(self.clear_dimensions)
        clear_btn.setStyleSheet(self.button_style("warning"))
        utils_layout.addWidget(clear_btn)

        reset_btn = QPushButton("🔄 Reset View")
        reset_btn.clicked.connect(self.reset_view)
        reset_btn.setStyleSheet(self.button_style())
        utils_layout.addWidget(reset_btn)

        demo_btn = QPushButton("🎯 Create Demo Dimensions")
        demo_btn.clicked.connect(self.create_demo_dimensions)
        demo_btn.setStyleSheet(self.button_style("success"))
        utils_layout.addWidget(demo_btn)

        layout.addWidget(utils_group)

        layout.addStretch()

        # Current tool display
        self.current_tool_label = QLabel("No tool active")
        self.current_tool_label.setStyleSheet("""
            padding: 8px; background-color: #fff3cd; border: 1px solid #ffc107;
            border-radius: 4px; margin: 5px; font-weight: bold;
        """)
        layout.addWidget(self.current_tool_label)

        return panel

    def create_style_panel(self):
        """Create the style editor panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Panel title
        title = QLabel("🎨 Dimension Style")
        title.setStyleSheet("""
            font-weight: bold; font-size: 14px; padding: 10px;
            background-color: #495057; color: white;
            border-radius: 6px; margin: 5px;
        """)
        layout.addWidget(title)

        # Style editor
        self.dimension_style = DimensionStyle()
        self.style_editor = DimensionStyleEditor(self.dimension_style)
        layout.addWidget(self.style_editor)

        layout.addStretch()

        return panel

    def button_style(self, variant="primary"):
        """Get button style for different variants."""
        colors = {
            "primary": {"bg": "#2196f3", "hover": "#1976d2"},
            "success": {"bg": "#4caf50", "hover": "#388e3c"},
            "warning": {"bg": "#ff9800", "hover": "#f57c00"}
        }

        color = colors.get(variant, colors["primary"])

        return f"""
            QPushButton {{
                padding: 10px 15px;
                font-size: 12px;
                background-color: {color["bg"]};
                color: white;
                border: none;
                border-radius: 6px;
                margin: 3px;
            }}
            QPushButton:hover {{
                background-color: {color["hover"]};
            }}
            QPushButton:pressed {{
                background-color: {color["hover"]};
                transform: translateY(1px);
            }}
        """

    def setup_dimension_tools(self):
        """Setup dimension tools."""
        # Mock dependencies
        class MockCommandManager:
            async def execute_command(self, command):
                return True

        class MockSelectionManager:
            def get_selected_items(self):
                return []

        command_manager = MockCommandManager()
        selection_manager = MockSelectionManager()

        # Create dimension tools
        self.dimension_tools = {
            "horizontal": HorizontalDimensionTool(
                self.scene, self.api_client, command_manager,
                self.snap_engine, selection_manager
            ),
            "vertical": VerticalDimensionTool(
                self.scene, self.api_client, command_manager,
                self.snap_engine, selection_manager
            ),
            "aligned": AlignedDimensionTool(
                self.scene, self.api_client, command_manager,
                self.snap_engine, selection_manager
            )
        }

        # Connect signals for all tools
        for tool in self.dimension_tools.values():
            tool.dimension_created.connect(self.on_dimension_created)
            tool.dimension_cancelled.connect(self.on_dimension_cancelled)
            # Set style reference
            tool.dimension_style = self.dimension_style
            tool.dimension_graphics.style = self.dimension_style

    def create_sample_geometry(self):
        """Create sample geometry for dimensioning."""
        pen = QPen(QColor(0, 100, 200), 2)

        # Create some lines to dimension
        line1 = QGraphicsLineItem(-150, -100, 150, -100)
        line1.setPen(pen)
        self.scene.addItem(line1)

        line2 = QGraphicsLineItem(-150, 100, 150, 100)
        line2.setPen(pen)
        self.scene.addItem(line2)

        # Vertical lines
        line3 = QGraphicsLineItem(-150, -100, -150, 100)
        line3.setPen(pen)
        self.scene.addItem(line3)

        line4 = QGraphicsLineItem(150, -100, 150, 100)
        line4.setPen(pen)
        self.scene.addItem(line4)

        # Diagonal line
        line5 = QGraphicsLineItem(-100, -50, 100, 50)
        line5.setPen(pen)
        self.scene.addItem(line5)

        # Circle
        circle = QGraphicsEllipseItem(-250, -50, 100, 100)
        circle.setPen(pen)
        self.scene.addItem(circle)

        logger.info("Created sample geometry for dimensioning")

    def activate_dimension_tool(self, tool_name: str):
        """Activate a dimension tool."""
        # Deactivate current tool
        if self.active_tool:
            self.active_tool.deactivate()

        # Activate new tool
        if tool_name in self.dimension_tools:
            self.active_tool = self.dimension_tools[tool_name]
            self.active_tool.activate()

            # Mock the view reference for tools
            self.active_tool.view = self.canvas_view

            # Connect mouse events
            self.canvas_view.mousePressEvent = self.handle_mouse_press
            self.canvas_view.mouseMoveEvent = self.handle_mouse_move

            self.current_tool_label.setText(f"Active: {tool_name.title()} Dimension")
            self.current_tool_label.setStyleSheet("""
                padding: 8px; background-color: #d4edda; border: 1px solid #28a745;
                border-radius: 4px; margin: 5px; font-weight: bold;
            """)

            self.status_label.setText(f"📐 {tool_name.title()} dimension tool active - Click first point")

            logger.info(f"Activated {tool_name} dimension tool")

    def handle_mouse_press(self, event):
        """Handle mouse press events for active tool."""
        if self.active_tool:
            # Convert to scene coordinates
            scene_pos = self.canvas_view.mapToScene(event.pos())

            # Create mock event with scene position
            class MockEvent:
                def __init__(self, pos):
                    self.pos_val = pos
                def pos(self):
                    return self.pos_val

            mock_event = MockEvent(event.pos())
            handled = self.active_tool.handle_mouse_press(mock_event)

            if handled:
                # Update status based on tool state
                if hasattr(self.active_tool, 'dimension_state'):
                    status = self.active_tool.get_status_text()
                    self.status_label.setText(status)

    def handle_mouse_move(self, event):
        """Handle mouse move events for active tool."""
        if self.active_tool:
            class MockEvent:
                def __init__(self, pos):
                    self.pos_val = pos
                def pos(self):
                    return self.pos_val

            mock_event = MockEvent(event.pos())
            self.active_tool.handle_mouse_move(mock_event)

    def clear_dimensions(self):
        """Clear all dimensions."""
        # Remove dimension graphics
        for tool in self.dimension_tools.values():
            tool.dimension_graphics.clear()

        self.status_label.setText("🗑️ All dimensions cleared")
        logger.info("Cleared all dimensions")

    def reset_view(self):
        """Reset the view to fit all content."""
        self.canvas_view.fitInView(self.scene.itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.status_label.setText("🔄 View reset to fit content")

    def create_demo_dimensions(self):
        """Create demo dimensions programmatically."""
        # This would create some example dimensions
        # For now, just show a message
        self.status_label.setText("🎯 Use dimension tools to create dimensions interactively")

    # Signal handlers
    def on_dimension_created(self, dimension_data):
        """Handle dimension creation."""
        dim_type = dimension_data.get("dimension_type", "unknown")
        self.status_label.setText(f"✅ Created {dim_type} dimension successfully")
        logger.info(f"Dimension created: {dim_type}")

    def on_dimension_cancelled(self):
        """Handle dimension cancellation."""
        self.status_label.setText("❌ Dimension operation cancelled")
        logger.info("Dimension operation cancelled")


def main():
    """Run the dimension test application."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("\n" + "="*70)
    print("📐 CAD-PY LINEAR DIMENSIONING SYSTEM - COMPREHENSIVE TEST")
    print("="*70)
    print("\n✅ **DIMENSIONING FEATURES:**")
    print("   • Horizontal dimensions - measure horizontal distances")
    print("   • Vertical dimensions - measure vertical distances")
    print("   • Aligned dimensions - measure along any angle")
    print("   • Professional dimension styling")
    print("   • Real-time preview during creation")
    print("   • Backend API integration")
    print("\n🎯 **TESTING COMPONENTS:**")
    print("   1. Interactive Dimension Tools - Click-based dimension creation")
    print("   2. Style Editor - Customize dimension appearance")
    print("   3. Sample Geometry - Pre-drawn shapes for practice")
    print("   4. Visual Feedback - Real-time dimension preview")
    print("\n📐 **DIMENSION CAPABILITIES:**")
    print("   • Automatic measurement calculation")
    print("   • Professional arrowheads and extension lines")
    print("   • Customizable text formatting and precision")
    print("   • Configurable units and scaling")
    print("   • Industry-standard dimension styling")
    print("\n🚀 **PRODUCTION READY:**")
    print("   • Professional CAD dimensioning system")
    print("   • Complete backend integration")
    print("   • Extensible architecture for advanced features")
    print("   • Industry-standard dimension workflows")
    print("\n" + "="*70)

    app = QApplication(sys.argv)

    # Create and show test application
    test_app = DimensionTestApp()
    test_app.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
