"""
Circle drawing tool implementation.

This module provides interactive circle drawing functionality with multiple
input methods including center-radius, 2-point diameter, and 3-point circle creation.
"""

import asyncio
import logging
import math
from typing import List, Optional, Tuple

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsScene

from ...core.api_client import APIClientManager
from ...core.command_manager import CommandManager
from ...core.commands import create_draw_circle_command
from ...core.snap_engine import SnapEngine
from .base_tool import BaseTool, ToolMode, ToolState


class CircleMode:
    """Circle drawing modes."""

    CENTER_RADIUS = "center_radius"  # Click center, then radius point
    TWO_POINT = "two_point"  # Two points define diameter
    THREE_POINT = "three_point"  # Three points on circumference


class CircleTool(BaseTool):
    """
    Interactive circle drawing tool.

    Supports multiple circle creation methods:
    - Center-Radius: Click center point, then radius point
    - 2-Point: Two points define the diameter
    - 3-Point: Three points on the circumference
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
        Initialize circle tool.

        Args:
            scene: Graphics scene for drawing
            api_client: API client for backend communication
            command_manager: Command manager for undo/redo
            snap_engine: Snap engine for point snapping
            parent: Qt parent object
        """
        super().__init__(
            "circle", scene, api_client, command_manager, snap_engine, parent
        )

        # Circle-specific state
        self.circle_mode = CircleMode.CENTER_RADIUS
        self.center_point: Optional[QPointF] = None
        self.radius_point: Optional[QPointF] = None
        self.current_radius = 0.0

        # 2-point mode state
        self.diameter_points: List[QPointF] = []

        # 3-point mode state
        self.circumference_points: List[QPointF] = []

        # Preview elements
        self.preview_circle: Optional[QGraphicsEllipseItem] = None
        self.center_marker: Optional[QGraphicsEllipseItem] = None
        self.radius_line: Optional[QGraphicsLineItem] = None
        self.point_markers: List[QGraphicsEllipseItem] = []

        # Styling
        self.preview_pen = QPen()
        self.preview_pen.setColor(Qt.cyan)
        self.preview_pen.setWidth(1)
        self.preview_pen.setStyle(Qt.DashLine)

        self.marker_pen = QPen()
        self.marker_pen.setColor(Qt.red)
        self.marker_pen.setWidth(2)

        self.logger = logging.getLogger(__name__)

    def activate(self):
        """Activate the circle tool."""
        self.start_tool()
        self.update_status_message(f"Circle tool activated - Mode: {self.circle_mode}")
        self._update_instructions()

    def deactivate(self):
        """Deactivate the circle tool."""
        self.cancel()
        self.update_status_message("Circle tool deactivated")

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

        self.update_coordinates(snapped_point)

        if self.circle_mode == CircleMode.CENTER_RADIUS:
            return self._handle_center_radius_click(snapped_point)
        elif self.circle_mode == CircleMode.TWO_POINT:
            return self._handle_two_point_click(snapped_point)
        elif self.circle_mode == CircleMode.THREE_POINT:
            return self._handle_three_point_click(snapped_point)

        return False

    def on_mouse_move(self, event: QMouseEvent) -> bool:
        """Handle mouse move events."""
        if not self.preview_enabled:
            return False

        # Get current position
        scene_pos = (
            self.scene.views()[0].mapToScene(event.pos())
            if self.scene.views()
            else QPointF(event.pos())
        )
        current_point = self.snap_point(scene_pos)

        self.update_coordinates(current_point)

        if self.circle_mode == CircleMode.CENTER_RADIUS:
            self._update_center_radius_preview(current_point)
        elif self.circle_mode == CircleMode.TWO_POINT:
            self._update_two_point_preview(current_point)
        elif self.circle_mode == CircleMode.THREE_POINT:
            self._update_three_point_preview(current_point)

        return True

    def on_mouse_release(self, event: QMouseEvent) -> bool:
        """Handle mouse release events."""
        return False

    def on_key_press(self, event: QKeyEvent) -> bool:
        """Handle key press events."""
        # Handle base tool keys first
        if super().on_key_press(event):
            return True

        # Circle-specific key handling
        if event.key() == Qt.Key_M:
            self._cycle_circle_mode()
            return True
        elif event.key() == Qt.Key_1:
            self.set_circle_mode(CircleMode.CENTER_RADIUS)
            return True
        elif event.key() == Qt.Key_2:
            self.set_circle_mode(CircleMode.TWO_POINT)
            return True
        elif event.key() == Qt.Key_3:
            self.set_circle_mode(CircleMode.THREE_POINT)
            return True

        return False

    def _handle_center_radius_click(self, point: QPointF) -> bool:
        """Handle mouse click for center-radius mode."""
        if not self.center_point:
            # First click - set center
            self.center_point = point
            self.points.append(point)
            self.state = ToolState.DRAWING
            self._add_center_marker(point)
            self.update_status_message("Click point on circumference to set radius")

        else:
            # Second click - set radius and create circle
            self.radius_point = point
            radius = self._calculate_distance(self.center_point, point)
            self._create_circle(self.center_point, radius)
            self.reset()

        return True

    def _handle_two_point_click(self, point: QPointF) -> bool:
        """Handle mouse click for two-point diameter mode."""
        self.diameter_points.append(point)
        self.points.append(point)
        self._add_point_marker(point)

        if len(self.diameter_points) == 1:
            self.state = ToolState.DRAWING
            self.update_status_message("Click second point to define diameter")

        elif len(self.diameter_points) == 2:
            # Calculate circle from diameter
            center, radius = self._calculate_circle_from_diameter(
                self.diameter_points[0], self.diameter_points[1]
            )
            self._create_circle(center, radius)
            self.reset()

        return True

    def _handle_three_point_click(self, point: QPointF) -> bool:
        """Handle mouse click for three-point mode."""
        self.circumference_points.append(point)
        self.points.append(point)
        self._add_point_marker(point)

        if len(self.circumference_points) == 1:
            self.state = ToolState.DRAWING
            self.update_status_message("Click second point on circumference")

        elif len(self.circumference_points) == 2:
            self.update_status_message("Click third point on circumference")

        elif len(self.circumference_points) == 3:
            # Calculate circle from three points
            try:
                center, radius = self._calculate_circle_from_three_points(
                    self.circumference_points[0],
                    self.circumference_points[1],
                    self.circumference_points[2],
                )
                self._create_circle(center, radius)
                self.reset()
            except ValueError as e:
                self.update_status_message(f"Cannot create circle: {e}")
                self._remove_last_point_marker()
                self.circumference_points.pop()
                self.points.pop()

        return True

    def _create_circle(self, center: QPointF, radius: float):
        """
        Create a circle using the command pattern.

        Args:
            center: Circle center point
            radius: Circle radius
        """
        if not self.current_document_id:
            self.logger.warning("No document context set for circle creation")
            return

        if radius <= 0:
            self.logger.warning("Invalid radius for circle creation")
            return

        # Convert QPointF to dict format
        center_dict = {"x": center.x(), "y": center.y(), "z": 0.0}

        # Create command
        command = create_draw_circle_command(
            self.api_client,
            self.current_document_id,
            center_dict,
            radius,
            layer_id=self.current_layer_id,
        )

        # Execute command asynchronously
        asyncio.create_task(self._execute_command(command))

        self.logger.info(
            f"Created circle at ({center.x():.2f}, {center.y():.2f}) with radius {radius:.2f}"
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

    def _update_center_radius_preview(self, current_point: QPointF):
        """Update preview for center-radius mode."""
        if not self.center_point:
            return

        # Calculate current radius
        radius = self._calculate_distance(self.center_point, current_point)
        self.current_radius = radius

        # Update preview circle
        self._update_circle_preview(self.center_point, radius)

        # Update radius line
        self._update_radius_line(self.center_point, current_point)

    def _update_two_point_preview(self, current_point: QPointF):
        """Update preview for two-point mode."""
        if len(self.diameter_points) != 1:
            return

        # Calculate circle from diameter
        center, radius = self._calculate_circle_from_diameter(
            self.diameter_points[0], current_point
        )

        # Update preview circle
        self._update_circle_preview(center, radius)

        # Update diameter line
        self._update_radius_line(self.diameter_points[0], current_point)

    def _update_three_point_preview(self, current_point: QPointF):
        """Update preview for three-point mode."""
        if len(self.circumference_points) < 2:
            return

        try:
            # For 2 points, show preview with current mouse position
            if len(self.circumference_points) == 2:
                center, radius = self._calculate_circle_from_three_points(
                    self.circumference_points[0],
                    self.circumference_points[1],
                    current_point,
                )
                self._update_circle_preview(center, radius)

        except ValueError:
            # Points are collinear or too close - don't show preview
            self._clear_circle_preview()

    def _update_circle_preview(self, center: QPointF, radius: float):
        """Update the preview circle."""
        # Remove existing preview
        if self.preview_circle:
            self.scene.removeItem(self.preview_circle)
            self.preview_circle = None

        if radius > 0:
            # Create new preview circle
            self.preview_circle = self.scene.addEllipse(
                center.x() - radius,
                center.y() - radius,
                radius * 2,
                radius * 2,
                self.preview_pen,
            )

            # Add to preview items for cleanup
            self.preview_items.append(self.preview_circle)

    def _update_radius_line(self, start: QPointF, end: QPointF):
        """Update the radius/diameter line preview."""
        # Remove existing line
        if self.radius_line:
            self.scene.removeItem(self.radius_line)
            self.radius_line = None

        # Create new line
        self.radius_line = self.scene.addLine(
            start.x(), start.y(), end.x(), end.y(), self.preview_pen
        )

        # Add to preview items for cleanup
        self.preview_items.append(self.radius_line)

    def _clear_circle_preview(self):
        """Clear the circle preview."""
        if self.preview_circle:
            self.scene.removeItem(self.preview_circle)
            self.preview_circle = None

    def _add_center_marker(self, point: QPointF):
        """Add a center point marker."""
        marker_size = 3
        self.center_marker = self.scene.addEllipse(
            point.x() - marker_size,
            point.y() - marker_size,
            marker_size * 2,
            marker_size * 2,
            self.marker_pen,
        )

        # Add to temporary items for cleanup
        self.temporary_items.append(self.center_marker)

    def _add_point_marker(self, point: QPointF):
        """Add a point marker."""
        marker_size = 2
        marker = self.scene.addEllipse(
            point.x() - marker_size,
            point.y() - marker_size,
            marker_size * 2,
            marker_size * 2,
            self.marker_pen,
        )

        self.point_markers.append(marker)
        self.temporary_items.append(marker)

    def _remove_last_point_marker(self):
        """Remove the last point marker."""
        if self.point_markers:
            marker = self.point_markers.pop()
            if marker.scene():
                self.scene.removeItem(marker)
            if marker in self.temporary_items:
                self.temporary_items.remove(marker)

    def _calculate_distance(self, p1: QPointF, p2: QPointF) -> float:
        """Calculate distance between two points."""
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        return math.sqrt(dx * dx + dy * dy)

    def _calculate_circle_from_diameter(
        self, p1: QPointF, p2: QPointF
    ) -> Tuple[QPointF, float]:
        """
        Calculate circle center and radius from two diameter points.

        Args:
            p1: First diameter point
            p2: Second diameter point

        Returns:
            Tuple of (center_point, radius)
        """
        center_x = (p1.x() + p2.x()) / 2
        center_y = (p1.y() + p2.y()) / 2
        center = QPointF(center_x, center_y)

        radius = self._calculate_distance(p1, p2) / 2

        return center, radius

    def _calculate_circle_from_three_points(
        self, p1: QPointF, p2: QPointF, p3: QPointF
    ) -> Tuple[QPointF, float]:
        """
        Calculate circle center and radius from three points on circumference.

        Args:
            p1: First point
            p2: Second point
            p3: Third point

        Returns:
            Tuple of (center_point, radius)

        Raises:
            ValueError: If points are collinear or coincident
        """
        x1, y1 = p1.x(), p1.y()
        x2, y2 = p2.x(), p2.y()
        x3, y3 = p3.x(), p3.y()

        # Check for collinear points
        area = abs((x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)) / 2)
        if area < 1e-6:  # Very small area indicates collinear points
            raise ValueError("Points are collinear")

        # Calculate circumcenter using the perpendicular bisector method
        d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))

        if abs(d) < 1e-10:
            raise ValueError("Points are collinear")

        ux = (
            (x1 * x1 + y1 * y1) * (y2 - y3)
            + (x2 * x2 + y2 * y2) * (y3 - y1)
            + (x3 * x3 + y3 * y3) * (y1 - y2)
        ) / d
        uy = (
            (x1 * x1 + y1 * y1) * (x3 - x2)
            + (x2 * x2 + y2 * y2) * (x1 - y3)
            + (x3 * x3 + y3 * y3) * (y2 - y1)
        ) / d

        center = QPointF(ux, uy)
        radius = self._calculate_distance(center, p1)

        return center, radius

    def _cycle_circle_mode(self):
        """Cycle through circle drawing modes."""
        modes = [CircleMode.CENTER_RADIUS, CircleMode.TWO_POINT, CircleMode.THREE_POINT]
        current_index = modes.index(self.circle_mode)
        next_index = (current_index + 1) % len(modes)

        old_mode = self.circle_mode
        self.circle_mode = modes[next_index]

        # Reset current operation
        self.cancel()
        self.activate()

        self.update_status_message(
            f"Circle mode changed: {old_mode} -> {self.circle_mode}"
        )

    def set_circle_mode(self, mode: str):
        """
        Set the circle drawing mode.

        Args:
            mode: Circle mode (center_radius, two_point, three_point)
        """
        if mode in [
            CircleMode.CENTER_RADIUS,
            CircleMode.TWO_POINT,
            CircleMode.THREE_POINT,
        ]:
            old_mode = self.circle_mode
            self.circle_mode = mode

            # Reset if mode changed
            if old_mode != mode:
                self.cancel()
                if self.state != ToolState.INACTIVE:
                    self.activate()

                self.update_status_message(f"Circle mode set to: {mode}")

    def _update_instructions(self):
        """Update status with current mode instructions."""
        if self.circle_mode == CircleMode.CENTER_RADIUS:
            self.update_status_message("Click center point, then radius point")
        elif self.circle_mode == CircleMode.TWO_POINT:
            self.update_status_message("Click two points to define diameter")
        elif self.circle_mode == CircleMode.THREE_POINT:
            self.update_status_message("Click three points on circumference")

    def reset(self):
        """Reset tool to initial state for next operation."""
        super().reset()

        # Clear circle-specific state
        self.center_point = None
        self.radius_point = None
        self.current_radius = 0.0
        self.diameter_points.clear()
        self.circumference_points.clear()

        # Clear markers
        if self.center_marker:
            if self.center_marker.scene():
                self.scene.removeItem(self.center_marker)
            self.center_marker = None

        for marker in self.point_markers:
            if marker.scene():
                self.scene.removeItem(marker)
        self.point_markers.clear()

        # Clear preview elements
        if self.preview_circle:
            if self.preview_circle.scene():
                self.scene.removeItem(self.preview_circle)
            self.preview_circle = None

        if self.radius_line:
            if self.radius_line.scene():
                self.scene.removeItem(self.radius_line)
            self.radius_line = None

        self._update_instructions()

    def cancel(self):
        """Cancel the current tool operation."""
        # Clear all preview and temporary items
        if self.preview_circle:
            if self.preview_circle.scene():
                self.scene.removeItem(self.preview_circle)
            self.preview_circle = None

        if self.radius_line:
            if self.radius_line.scene():
                self.scene.removeItem(self.radius_line)
            self.radius_line = None

        if self.center_marker:
            if self.center_marker.scene():
                self.scene.removeItem(self.center_marker)
            self.center_marker = None

        for marker in self.point_markers:
            if marker.scene():
                self.scene.removeItem(marker)
        self.point_markers.clear()

        super().cancel()

    def get_tool_info(self):
        """Get tool information including circle-specific data."""
        info = super().get_tool_info()
        info.update(
            {
                "circle_mode": self.circle_mode,
                "center_point": self.center_point is not None,
                "current_radius": self.current_radius,
                "diameter_points": len(self.diameter_points),
                "circumference_points": len(self.circumference_points),
                "has_preview": self.preview_circle is not None,
            }
        )
        return info
