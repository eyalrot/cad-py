"""
Line drawing tool implementation.

This module provides interactive line drawing functionality with support for
single lines, polylines, orthogonal constraints, and visual preview feedback.
"""

import asyncio
import logging
from typing import List, Optional

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QPen
from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsScene

from ...core.api_client import APIClientManager
from ...core.command_manager import CommandManager
from ...core.commands import create_draw_line_command
from ...core.snap_engine import SnapEngine
from .base_tool import BaseTool, ToolMode, ToolState


class LineMode:
    """Line drawing modes."""

    SINGLE = "single"  # Draw single line segments
    POLYLINE = "polyline"  # Draw connected line segments
    CONTINUOUS = "continuous"  # Continuous line drawing


class LineTool(BaseTool):
    """
    Interactive line drawing tool.

    Supports:
    - Single line drawing
    - Polyline drawing (connected segments)
    - Orthogonal constraints
    - Visual preview
    - Snap integration
    - Undo/redo via command pattern
    """

    def __init__(
        self,
        scene: QGraphicsScene,
        api_client: APIClientManager,
        command_manager: CommandManager,
        snap_engine: SnapEngine,
        parent=None,
    ):
        """
        Initialize line tool.

        Args:
            scene: Graphics scene for drawing
            api_client: API client for backend communication
            command_manager: Command manager for undo/redo
            snap_engine: Snap engine for point snapping
            parent: Qt parent object
        """
        super().__init__(
            "line", scene, api_client, command_manager, snap_engine, parent
        )

        # Line-specific state
        self.line_mode = LineMode.SINGLE
        self.start_point: Optional[QPointF] = None
        self.current_preview: Optional[QGraphicsLineItem] = None

        # Polyline state
        self.polyline_points: List[QPointF] = []
        self.polyline_preview_lines: List[QGraphicsLineItem] = []

        # Styling for preview
        self.preview_pen = QPen()
        self.preview_pen.setColor(Qt.cyan)
        self.preview_pen.setWidth(1)
        self.preview_pen.setStyle(Qt.DashLine)

        # Polyline preview pen
        self.polyline_pen = QPen()
        self.polyline_pen.setColor(Qt.yellow)
        self.polyline_pen.setWidth(1)
        self.polyline_pen.setStyle(Qt.DotLine)

        self.logger = logging.getLogger(__name__)

    def activate(self):
        """Activate the line tool."""
        self.start_tool()
        self.update_status_message(f"Line tool activated - Mode: {self.line_mode}")

        # Provide usage instructions
        if self.line_mode == LineMode.SINGLE:
            self.update_status_message("Click two points to draw a line")
        elif self.line_mode == LineMode.POLYLINE:
            self.update_status_message(
                "Click points to draw polyline, Enter to finish, Esc to cancel"
            )

    def deactivate(self):
        """Deactivate the line tool."""
        self.cancel()
        self.update_status_message("Line tool deactivated")

    def on_mouse_press(self, event: QMouseEvent) -> bool:
        """Handle mouse press events."""
        if event.button() != Qt.LeftButton:
            return False

        # Get snapped point
        scene_pos = (
            self.scene.views()[0].mapToScene(event.pos())
            if self.scene.views()
            else QPointF(event.pos())
        )
        snapped_point = self.snap_point(scene_pos)

        # Apply orthogonal constraint if needed
        if self.ortho_mode and self.points:
            snapped_point = self.constrain_orthogonal(self.points[-1], snapped_point)

        self.update_coordinates(snapped_point)

        if self.line_mode == LineMode.SINGLE:
            return self._handle_single_line_click(snapped_point)
        elif self.line_mode == LineMode.POLYLINE:
            return self._handle_polyline_click(snapped_point)

        return False

    def on_mouse_move(self, event: QMouseEvent) -> bool:
        """Handle mouse move events."""
        if not self.points and self.line_mode == LineMode.SINGLE:
            return False

        # Get current position
        scene_pos = (
            self.scene.views()[0].mapToScene(event.pos())
            if self.scene.views()
            else QPointF(event.pos())
        )
        current_point = self.snap_point(scene_pos)

        # Apply orthogonal constraint if needed
        if self.ortho_mode and self.points:
            current_point = self.constrain_orthogonal(self.points[-1], current_point)

        self.update_coordinates(current_point)

        if self.line_mode == LineMode.SINGLE:
            self._update_single_line_preview(current_point)
        elif self.line_mode == LineMode.POLYLINE:
            self._update_polyline_preview(current_point)

        return True

    def on_mouse_release(self, event: QMouseEvent) -> bool:
        """Handle mouse release events."""
        # Line tool primarily uses mouse press events
        return False

    def on_key_press(self, event: QKeyEvent) -> bool:
        """Handle key press events."""
        # Handle base tool keys first
        if super().on_key_press(event):
            return True

        # Line-specific key handling
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            if self.line_mode == LineMode.POLYLINE:
                self._finish_polyline()
                return True
        elif event.key() == Qt.Key_Backspace:
            if self.line_mode == LineMode.POLYLINE and self.polyline_points:
                self._remove_last_polyline_point()
                return True
        elif event.key() == Qt.Key_M:
            self._cycle_line_mode()
            return True

        return False

    def _handle_single_line_click(self, point: QPointF) -> bool:
        """Handle mouse click for single line mode."""
        if len(self.points) == 0:
            # First point - start line
            self.points.append(point)
            self.start_point = point
            self.state = ToolState.DRAWING
            self.update_status_message("Click second point to complete line")

        elif len(self.points) == 1:
            # Second point - complete line
            end_point = point
            self._create_line(self.points[0], end_point)
            self.reset()

        return True

    def _handle_polyline_click(self, point: QPointF) -> bool:
        """Handle mouse click for polyline mode."""
        if len(self.polyline_points) == 0:
            # First point of polyline
            self.polyline_points.append(point)
            self.points.append(point)  # For base tool tracking
            self.state = ToolState.DRAWING
            self.update_status_message("Continue clicking points, Enter to finish")

        else:
            # Additional points
            prev_point = self.polyline_points[-1]
            self.polyline_points.append(point)
            self.points.append(point)

            # Create line segment immediately
            self._create_line(prev_point, point)

            self.update_status_message(
                f"Polyline: {len(self.polyline_points)} points, Enter to finish"
            )

        return True

    def _create_line(self, start: QPointF, end: QPointF):
        """
        Create a line using the command pattern.

        Args:
            start: Start point
            end: End point
        """
        if not self.current_document_id:
            self.logger.warning("No document context set for line creation")
            return

        # Convert QPointF to dict format
        start_dict = {"x": start.x(), "y": start.y(), "z": 0.0}
        end_dict = {"x": end.x(), "y": end.y(), "z": 0.0}

        # Create command
        command = create_draw_line_command(
            self.api_client,
            self.current_document_id,
            start_dict,
            end_dict,
            layer_id=self.current_layer_id,
        )

        # Execute command asynchronously
        asyncio.create_task(self._execute_command(command))

        self.logger.info(
            f"Created line from ({start.x():.2f}, {start.y():.2f}) to ({end.x():.2f}, {end.y():.2f})"
        )

    async def _execute_command(self, command):
        """Execute a command asynchronously."""
        try:
            success = await self.command_manager.execute_command(command)
            if not success:
                self.logger.warning(
                    f"Command execution failed: {command.get_description()}"
                )
        except Exception as e:
            self.logger.error(f"Error executing command: {e}")

    def _update_single_line_preview(self, current_point: QPointF):
        """Update preview for single line mode."""
        if not self.points or not self.preview_enabled:
            return

        # Remove existing preview
        if self.current_preview:
            self.scene.removeItem(self.current_preview)
            self.current_preview = None

        # Create new preview line
        start_point = self.points[0]
        self.current_preview = self.scene.addLine(
            start_point.x(),
            start_point.y(),
            current_point.x(),
            current_point.y(),
            self.preview_pen,
        )

        # Add to preview items for cleanup
        self.preview_items.append(self.current_preview)

    def _update_polyline_preview(self, current_point: QPointF):
        """Update preview for polyline mode."""
        if not self.polyline_points or not self.preview_enabled:
            return

        # Remove existing preview
        if self.current_preview:
            self.scene.removeItem(self.current_preview)
            self.current_preview = None

        # Create preview line from last point to current position
        last_point = self.polyline_points[-1]
        self.current_preview = self.scene.addLine(
            last_point.x(),
            last_point.y(),
            current_point.x(),
            current_point.y(),
            self.preview_pen,
        )

        # Add to preview items for cleanup
        self.preview_items.append(self.current_preview)

    def _finish_polyline(self):
        """Finish the current polyline."""
        if len(self.polyline_points) >= 2:
            self.update_status_message(
                f"Polyline completed with {len(self.polyline_points)} points"
            )
        else:
            self.update_status_message("Polyline cancelled - need at least 2 points")

        self._reset_polyline()
        self.reset()

    def _remove_last_polyline_point(self):
        """Remove the last point from the current polyline."""
        if self.polyline_points:
            removed_point = self.polyline_points.pop()
            if self.points:
                self.points.pop()

            self.update_status_message(
                f"Removed point ({removed_point.x():.2f}, {removed_point.y():.2f})"
            )

            # TODO: If we want to undo the last line segment creation,
            # we'd need to track individual line commands and undo them

    def _reset_polyline(self):
        """Reset polyline state."""
        self.polyline_points.clear()

        # Clear polyline preview items
        for item in self.polyline_preview_lines:
            if item.scene():
                self.scene.removeItem(item)
        self.polyline_preview_lines.clear()

    def _cycle_line_mode(self):
        """Cycle through line drawing modes."""
        modes = [LineMode.SINGLE, LineMode.POLYLINE]
        current_index = modes.index(self.line_mode)
        next_index = (current_index + 1) % len(modes)

        old_mode = self.line_mode
        self.line_mode = modes[next_index]

        # Reset current operation
        self.cancel()
        self.activate()

        self.update_status_message(f"Line mode changed: {old_mode} -> {self.line_mode}")

    def set_line_mode(self, mode: str):
        """
        Set the line drawing mode.

        Args:
            mode: Line mode (single, polyline, continuous)
        """
        if mode in [LineMode.SINGLE, LineMode.POLYLINE, LineMode.CONTINUOUS]:
            old_mode = self.line_mode
            self.line_mode = mode

            # Reset if mode changed
            if old_mode != mode:
                self.cancel()
                if self.state != ToolState.INACTIVE:
                    self.activate()

                self.update_status_message(f"Line mode set to: {mode}")

    def complete_current_operation(self):
        """Complete the current drawing operation."""
        if self.line_mode == LineMode.POLYLINE and len(self.polyline_points) >= 2:
            self._finish_polyline()
        elif self.line_mode == LineMode.SINGLE and len(self.points) == 1:
            # Cancel incomplete single line
            self.cancel()

    def reset(self):
        """Reset tool to initial state for next operation."""
        super().reset()
        self.start_point = None

        # Clear preview
        if self.current_preview:
            self.scene.removeItem(self.current_preview)
            self.current_preview = None

        # Reset polyline for single mode
        if self.line_mode == LineMode.SINGLE:
            self._reset_polyline()

        # Update status based on mode
        if self.line_mode == LineMode.SINGLE:
            self.update_status_message("Click first point to start line")
        elif self.line_mode == LineMode.POLYLINE:
            if not self.polyline_points:
                self.update_status_message("Click first point to start polyline")

    def cancel(self):
        """Cancel the current tool operation."""
        # Clear preview
        if self.current_preview:
            self.scene.removeItem(self.current_preview)
            self.current_preview = None

        # Reset polyline
        self._reset_polyline()

        super().cancel()

    def get_tool_info(self):
        """Get tool information including line-specific data."""
        info = super().get_tool_info()
        info.update(
            {
                "line_mode": self.line_mode,
                "polyline_points": len(self.polyline_points),
                "has_preview": self.current_preview is not None,
            }
        )
        return info
