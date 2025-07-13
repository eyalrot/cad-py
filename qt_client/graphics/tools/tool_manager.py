"""
Tool Manager for CAD drawing tools.

This module provides centralized management of all drawing tools,
including tool registration, activation, and event routing.
"""

import logging
from typing import Dict, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QGraphicsScene

from .base_tool import BaseTool

logger = logging.getLogger(__name__)


class ToolManager(QObject):
    """
    Central manager for all CAD drawing tools.

    Handles tool registration, activation, deactivation,
    and event routing to the active tool.
    """

    # Signals
    tool_activated = Signal(str)  # tool_name
    tool_deactivated = Signal(str)  # tool_name
    tool_changed = Signal(str, str)  # old_tool, new_tool

    def __init__(self, parent=None):
        super().__init__(parent)

        self.tools: Dict[str, BaseTool] = {}
        self.active_tool: Optional[BaseTool] = None
        self.scene: Optional[QGraphicsScene] = None

        # Core components (set later)
        self.command_manager = None
        self.snap_engine = None
        self.selection_manager = None

        logger.debug("ToolManager initialized")

    def set_scene(self, scene: QGraphicsScene):
        """Set the graphics scene for tools."""
        self.scene = scene

        # Update all registered tools
        for tool in self.tools.values():
            tool.scene = scene

    def set_command_manager(self, command_manager):
        """Set the command manager for tools."""
        self.command_manager = command_manager

        # Update all registered tools
        for tool in self.tools.values():
            tool.command_manager = command_manager

    def set_snap_engine(self, snap_engine):
        """Set the snap engine for tools."""
        self.snap_engine = snap_engine

        # Update all registered tools
        for tool in self.tools.values():
            tool.snap_engine = snap_engine

    def set_selection_manager(self, selection_manager):
        """Set the selection manager for tools."""
        self.selection_manager = selection_manager

        # Update all registered tools
        for tool in self.tools.values():
            if hasattr(tool, "selection_manager"):
                tool.selection_manager = selection_manager

    def register_tool(self, name: str, tool: BaseTool):
        """Register a tool with the manager."""
        if name in self.tools:
            logger.warning(f"Tool '{name}' already registered, replacing")

        # Set tool properties
        tool.scene = self.scene
        tool.command_manager = self.command_manager
        tool.snap_engine = self.snap_engine

        if hasattr(tool, "selection_manager") and self.selection_manager:
            tool.selection_manager = self.selection_manager

        self.tools[name] = tool
        logger.debug(f"Registered tool: {name}")

    def unregister_tool(self, name: str):
        """Unregister a tool from the manager."""
        if name in self.tools:
            if self.active_tool == self.tools[name]:
                self.deactivate_current_tool()
            del self.tools[name]
            logger.debug(f"Unregistered tool: {name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a registered tool by name."""
        return self.tools.get(name)

    def get_active_tool(self) -> Optional[BaseTool]:
        """Get the currently active tool."""
        return self.active_tool

    def get_active_tool_name(self) -> Optional[str]:
        """Get the name of the currently active tool."""
        if self.active_tool:
            for name, tool in self.tools.items():
                if tool == self.active_tool:
                    return name
        return None

    def activate_tool(self, name: str) -> bool:
        """Activate a tool by name."""
        if name not in self.tools:
            logger.error(f"Tool '{name}' not found")
            return False

        tool = self.tools[name]

        # Deactivate current tool if any
        old_tool_name = self.get_active_tool_name()
        if self.active_tool:
            self.deactivate_current_tool()

        # Activate new tool
        try:
            if hasattr(tool, "activate"):
                success = tool.activate()
            else:
                success = True

            if success:
                self.active_tool = tool
                self.tool_activated.emit(name)

                if old_tool_name:
                    self.tool_changed.emit(old_tool_name, name)

                logger.debug(f"Activated tool: {name}")
                return True
            else:
                logger.error(f"Failed to activate tool: {name}")
                return False

        except Exception as e:
            logger.error(f"Error activating tool '{name}': {e}")
            return False

    def deactivate_current_tool(self):
        """Deactivate the currently active tool."""
        if self.active_tool:
            tool_name = self.get_active_tool_name()

            try:
                if hasattr(self.active_tool, "deactivate"):
                    self.active_tool.deactivate()

                self.active_tool = None

                if tool_name:
                    self.tool_deactivated.emit(tool_name)
                    logger.debug(f"Deactivated tool: {tool_name}")

            except Exception as e:
                logger.error(f"Error deactivating tool: {e}")
                self.active_tool = None

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        """Route mouse press event to active tool."""
        if self.active_tool and hasattr(self.active_tool, "handle_mouse_press"):
            try:
                return self.active_tool.handle_mouse_press(event)
            except Exception as e:
                logger.error(f"Error in tool mouse press handler: {e}")
        return False

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        """Route mouse move event to active tool."""
        if self.active_tool and hasattr(self.active_tool, "handle_mouse_move"):
            try:
                return self.active_tool.handle_mouse_move(event)
            except Exception as e:
                logger.error(f"Error in tool mouse move handler: {e}")
        return False

    def handle_mouse_release(self, event: QMouseEvent) -> bool:
        """Route mouse release event to active tool."""
        if self.active_tool and hasattr(self.active_tool, "handle_mouse_release"):
            try:
                return self.active_tool.handle_mouse_release(event)
            except Exception as e:
                logger.error(f"Error in tool mouse release handler: {e}")
        return False

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Route key press event to active tool."""
        if self.active_tool and hasattr(self.active_tool, "handle_key_press"):
            try:
                return self.active_tool.handle_key_press(event)
            except Exception as e:
                logger.error(f"Error in tool key press handler: {e}")
        return False

    def get_tool_list(self) -> list:
        """Get list of all registered tool names."""
        return list(self.tools.keys())

    def get_tool_info(self) -> dict:
        """Get information about all registered tools."""
        info = {
            "total_tools": len(self.tools),
            "active_tool": self.get_active_tool_name(),
            "available_tools": list(self.tools.keys()),
        }
        return info
