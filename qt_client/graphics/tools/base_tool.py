"""
Base tool interface and framework for CAD drawing tools.

This module provides the foundation for all drawing tools including
event handling, state management, and integration with the CAD system.
"""

import math
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QPointF, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent, QPen
from PySide6.QtWidgets import QGraphicsScene

# Handle imports gracefully for testing
try:
    from ...core.api_client import APIClientManager
except ImportError:
    # Mock for testing
    class APIClientManager:
        pass


try:
    from ...core.command_manager import CommandManager
except ImportError:
    # Mock for testing
    class CommandManager:
        pass


try:
    from ...core.snap_engine import SnapEngine, SnapPoint
except ImportError:
    # Mock for testing
    class SnapEngine:
        pass

    class SnapPoint:
        pass


# Create a compatible metaclass for QObject + ABC
class QObjectABCMeta(type(QObject), type(ABC)):
    """Metaclass that combines QObject and ABC metaclasses."""

    pass


class ToolState(Enum):
    """Tool execution states."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    DRAWING = "drawing"
    WAITING_INPUT = "waiting_input"
    COMPLETED = "completed"


class ToolMode(Enum):
    """Tool operation modes."""

    SINGLE = "single"
    CONTINUOUS = "continuous"
    POLYLINE = "polyline"


class BaseTool(QObject, ABC, metaclass=QObjectABCMeta):
    """
    Abstract base class for all CAD drawing tools.

    Provides common functionality for tool state management,
    event handling, and integration with the CAD system.
    """

    # Signals
    tool_started = Signal(str)  # tool_name
    tool_finished = Signal(str)  # tool_name
    tool_cancelled = Signal(str)  # tool_name
    status_message = Signal(str)  # status message
    coordinates_changed = Signal(float, float)  # x, y coordinates

    def __init__(
        self,
        name: str,
        scene: QGraphicsScene,
        api_client: APIClientManager,
        command_manager: CommandManager,
        snap_engine: SnapEngine,
        parent=None,
    ):
        """
        Initialize base tool.

        Args:
            name: Tool name/identifier
            scene: Graphics scene for drawing
            api_client: API client for backend communication
            command_manager: Command manager for undo/redo
            snap_engine: Snap engine for point snapping
            parent: Qt parent object
        """
        super().__init__(parent)

        self.name = name
        self.scene = scene
        self.api_client = api_client
        self.command_manager = command_manager
        self.snap_engine = snap_engine

        # Tool state
        self.state = ToolState.INACTIVE
        self.mode = ToolMode.SINGLE

        # Current document context
        self.current_document_id: Optional[str] = None
        self.current_layer_id: Optional[str] = None

        # Input points and data
        self.points: List[QPointF] = []
        self.input_data: Dict[str, Any] = {}

        # Visual feedback elements
        self.preview_items: List[Any] = []  # Graphics items for preview
        self.temporary_items: List[Any] = []  # Temporary graphics items

        # Tool settings
        self.ortho_mode = False
        self.snap_enabled = True
        self.preview_enabled = True

        # Styling
        self.preview_pen = QPen()
        self.preview_pen.setWidth(1)
        self.preview_pen.setColor("cyan")
        self.preview_pen.setStyle(2)  # DashLine

    @abstractmethod
    def activate(self):
        """Activate the tool."""
        pass

    @abstractmethod
    def deactivate(self):
        """Deactivate the tool."""
        pass

    @abstractmethod
    def on_mouse_press(self, event: QMouseEvent) -> bool:
        """
        Handle mouse press events.

        Args:
            event: Mouse event

        Returns:
            True if event was handled
        """
        pass

    @abstractmethod
    def on_mouse_move(self, event: QMouseEvent) -> bool:
        """
        Handle mouse move events.

        Args:
            event: Mouse event

        Returns:
            True if event was handled
        """
        pass

    @abstractmethod
    def on_mouse_release(self, event: QMouseEvent) -> bool:
        """
        Handle mouse release events.

        Args:
            event: Mouse event

        Returns:
            True if event was handled
        """
        pass

    def on_key_press(self, event: QKeyEvent) -> bool:
        """
        Handle key press events.

        Args:
            event: Key event

        Returns:
            True if event was handled
        """
        # Common key handling
        if event.key() == 16777216:  # Escape key
            self.cancel()
            return True
        elif event.key() == 16777220:  # Enter key
            self.complete_current_operation()
            return True
        elif event.key() == 79:  # 'O' key - toggle orthogonal mode
            self.toggle_ortho_mode()
            return True
        elif event.key() == 83:  # 'S' key - toggle snap
            self.toggle_snap()
            return True

        return False

    def snap_point(self, scene_pos: QPointF) -> QPointF:
        """
        Apply snapping to a scene position.

        Args:
            scene_pos: Scene position to snap

        Returns:
            Snapped point
        """
        if not self.snap_enabled or not self.snap_engine:
            return scene_pos

        # Get snap point from snap engine
        snap_result = self.snap_engine.find_snap_point(scene_pos, self.points)

        if snap_result:
            return snap_result.point

        return scene_pos

    def constrain_orthogonal(
        self, base_point: QPointF, current_point: QPointF
    ) -> QPointF:
        """
        Apply orthogonal constraint to a point.

        Args:
            base_point: Base point for constraint
            current_point: Point to constrain

        Returns:
            Constrained point
        """
        if not self.ortho_mode:
            return current_point

        dx = current_point.x() - base_point.x()
        dy = current_point.y() - base_point.y()

        # Determine which axis to constrain to
        if abs(dx) > abs(dy):
            # Constrain to horizontal
            return QPointF(current_point.x(), base_point.y())
        else:
            # Constrain to vertical
            return QPointF(base_point.x(), current_point.y())

    def constrain_angle(
        self, base_point: QPointF, current_point: QPointF, angle_increment: float = 15.0
    ) -> QPointF:
        """
        Constrain point to specific angle increments.

        Args:
            base_point: Base point for constraint
            current_point: Point to constrain
            angle_increment: Angle increment in degrees

        Returns:
            Constrained point
        """
        dx = current_point.x() - base_point.x()
        dy = current_point.y() - base_point.y()

        distance = math.sqrt(dx * dx + dy * dy)
        current_angle = math.degrees(math.atan2(dy, dx))

        # Round to nearest angle increment
        constrained_angle = round(current_angle / angle_increment) * angle_increment
        constrained_angle_rad = math.radians(constrained_angle)

        new_x = base_point.x() + distance * math.cos(constrained_angle_rad)
        new_y = base_point.y() + distance * math.sin(constrained_angle_rad)

        return QPointF(new_x, new_y)

    def start_tool(self):
        """Start the tool operation."""
        if self.state == ToolState.INACTIVE:
            self.state = ToolState.ACTIVE
            self.points.clear()
            self.input_data.clear()
            self.clear_preview()
            self.tool_started.emit(self.name)
            self.update_status_message("Tool started")

    def finish_tool(self):
        """Finish the tool operation."""
        self.clear_preview()
        self.clear_temporary_items()
        self.points.clear()
        self.input_data.clear()
        self.state = ToolState.COMPLETED
        self.tool_finished.emit(self.name)
        self.update_status_message("Tool completed")

    def cancel(self):
        """Cancel the current tool operation."""
        self.clear_preview()
        self.clear_temporary_items()
        self.points.clear()
        self.input_data.clear()
        self.state = ToolState.INACTIVE
        self.tool_cancelled.emit(self.name)
        self.update_status_message("Tool cancelled")

    def reset(self):
        """Reset tool to initial state for next operation."""
        self.points.clear()
        self.input_data.clear()
        self.clear_preview()
        self.clear_temporary_items()

        if self.mode == ToolMode.SINGLE:
            self.state = ToolState.ACTIVE
        else:
            # For continuous modes, stay active
            self.state = ToolState.ACTIVE

    def complete_current_operation(self):
        """Complete the current drawing operation."""
        # To be implemented by specific tools
        pass

    def clear_preview(self):
        """Clear all preview graphics items."""
        for item in self.preview_items:
            if item.scene():
                self.scene.removeItem(item)
        self.preview_items.clear()

    def clear_temporary_items(self):
        """Clear all temporary graphics items."""
        for item in self.temporary_items:
            if item.scene():
                self.scene.removeItem(item)
        self.temporary_items.clear()

    def toggle_ortho_mode(self):
        """Toggle orthogonal constraint mode."""
        self.ortho_mode = not self.ortho_mode
        mode_text = "ON" if self.ortho_mode else "OFF"
        self.update_status_message(f"Orthogonal mode: {mode_text}")

    def toggle_snap(self):
        """Toggle snap mode."""
        self.snap_enabled = not self.snap_enabled
        snap_text = "ON" if self.snap_enabled else "OFF"
        self.update_status_message(f"Snap: {snap_text}")

    def set_mode(self, mode: ToolMode):
        """Set tool operation mode."""
        self.mode = mode
        self.update_status_message(f"Mode: {mode.value}")

    def set_document_context(self, document_id: str, layer_id: Optional[str] = None):
        """
        Set the current document context.

        Args:
            document_id: Current document ID
            layer_id: Current layer ID (optional)
        """
        self.current_document_id = document_id
        self.current_layer_id = layer_id

    def update_status_message(self, message: str):
        """
        Update status message.

        Args:
            message: Status message to display
        """
        self.status_message.emit(f"{self.name}: {message}")

    def update_coordinates(self, point: QPointF):
        """
        Update coordinate display.

        Args:
            point: Current coordinates
        """
        self.coordinates_changed.emit(point.x(), point.y())

    def get_tool_info(self) -> Dict[str, Any]:
        """
        Get tool information and current state.

        Returns:
            Dictionary with tool information
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "mode": self.mode.value,
            "ortho_mode": self.ortho_mode,
            "snap_enabled": self.snap_enabled,
            "preview_enabled": self.preview_enabled,
            "points_count": len(self.points),
            "document_id": self.current_document_id,
            "layer_id": self.current_layer_id,
        }


class ToolManager(QObject):
    """
    Manager for handling multiple drawing tools.

    Provides tool registration, activation, and event routing.
    """

    # Signals
    tool_changed = Signal(str)  # new tool name
    tool_activated = Signal(str)  # tool name
    tool_deactivated = Signal(str)  # tool name

    def __init__(
        self,
        scene: QGraphicsScene,
        api_client: APIClientManager,
        command_manager: CommandManager,
        snap_engine: SnapEngine,
        parent=None,
    ):
        """
        Initialize tool manager.

        Args:
            scene: Graphics scene
            api_client: API client
            command_manager: Command manager
            snap_engine: Snap engine
            parent: Qt parent
        """
        super().__init__(parent)

        self.scene = scene
        self.api_client = api_client
        self.command_manager = command_manager
        self.snap_engine = snap_engine

        # Tool registry
        self.tools: Dict[str, BaseTool] = {}
        self.active_tool: Optional[BaseTool] = None

        # Default tool (selection)
        self.default_tool_name = "select"

    def register_tool(self, tool: BaseTool):
        """
        Register a tool with the manager.

        Args:
            tool: Tool to register
        """
        self.tools[tool.name] = tool

        # Connect tool signals
        tool.tool_started.connect(self.on_tool_started)
        tool.tool_finished.connect(self.on_tool_finished)
        tool.tool_cancelled.connect(self.on_tool_cancelled)

    def activate_tool(self, tool_name: str) -> bool:
        """
        Activate a tool by name.

        Args:
            tool_name: Name of tool to activate

        Returns:
            True if tool was activated successfully
        """
        if tool_name not in self.tools:
            return False

        # Deactivate current tool
        if self.active_tool:
            self.active_tool.deactivate()
            self.tool_deactivated.emit(self.active_tool.name)

        # Activate new tool
        new_tool = self.tools[tool_name]
        new_tool.activate()
        self.active_tool = new_tool

        self.tool_activated.emit(tool_name)
        self.tool_changed.emit(tool_name)

        return True

    def get_active_tool(self) -> Optional[BaseTool]:
        """Get the currently active tool."""
        return self.active_tool

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self.tools.get(tool_name)

    def get_tool_names(self) -> List[str]:
        """Get list of registered tool names."""
        return list(self.tools.keys())

    def route_mouse_press(self, event: QMouseEvent) -> bool:
        """Route mouse press event to active tool."""
        if self.active_tool:
            return self.active_tool.on_mouse_press(event)
        return False

    def route_mouse_move(self, event: QMouseEvent) -> bool:
        """Route mouse move event to active tool."""
        if self.active_tool:
            return self.active_tool.on_mouse_move(event)
        return False

    def route_mouse_release(self, event: QMouseEvent) -> bool:
        """Route mouse release event to active tool."""
        if self.active_tool:
            return self.active_tool.on_mouse_release(event)
        return False

    def route_key_press(self, event: QKeyEvent) -> bool:
        """Route key press event to active tool."""
        if self.active_tool:
            return self.active_tool.on_key_press(event)
        return False

    def set_document_context(self, document_id: str, layer_id: Optional[str] = None):
        """Set document context for all tools."""
        for tool in self.tools.values():
            tool.set_document_context(document_id, layer_id)

    # Signal handlers
    def on_tool_started(self, tool_name: str):
        """Handle tool started signal."""
        pass

    def on_tool_finished(self, tool_name: str):
        """Handle tool finished signal."""
        # Auto-switch to default tool after completion
        if self.active_tool and self.active_tool.mode == ToolMode.SINGLE:
            self.activate_tool(self.default_tool_name)

    def on_tool_cancelled(self, tool_name: str):
        """Handle tool cancelled signal."""
        # Auto-switch to default tool after cancellation
        self.activate_tool(self.default_tool_name)
