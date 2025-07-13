"""
Arc drawing tool implementation.

This module provides interactive arc drawing functionality with multiple
input methods including 3-point arc and start-center-end arc creation.
"""

import asyncio
import logging
import math
from typing import List, Optional, Tuple

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsScene,
)

from ...core.api_client import APIClientManager
from ...core.command_manager import CommandManager
from ...core.commands import create_draw_arc_command
from ...core.snap_engine import SnapEngine
from .base_tool import BaseTool, ToolMode, ToolState


class ArcMode:
    """Arc drawing modes."""

    THREE_POINT = "three_point"  # Three points on arc
    START_CENTER_END = "start_center_end"  # Start point, center, end point
    CENTER_START_END = "center_start_end"  # Center, start point, end point


class ArcTool(BaseTool):
    """
    Interactive arc drawing tool.

    Supports multiple arc creation methods:
    - 3-Point: Three points on the arc
    - Start-Center-End: Start point, center, then end point
    - Center-Start-End: Center, start point, then end point
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
        Initialize arc tool.

        Args:
            scene: Graphics scene for drawing
            api_client: API client for backend communication
            command_manager: Command manager for undo/redo
            snap_engine: Snap engine for point snapping
            parent: Qt parent object
        """
        super().__init__("arc", scene, api_client, command_manager, snap_engine, parent)

        # Arc-specific state
        self.arc_mode = ArcMode.THREE_POINT

        # 3-point mode state
        self.arc_points: List[QPointF] = []

        # Center-based mode state
        self.center_point: Optional[QPointF] = None
        self.start_point: Optional[QPointF] = None
        self.end_point: Optional[QPointF] = None

        # Arc geometry
        self.arc_center: Optional[QPointF] = None
        self.arc_radius = 0.0
        self.start_angle = 0.0
        self.end_angle = 0.0
        self.arc_length = 0.0

        # Preview elements
        self.preview_arc: Optional[QGraphicsPathItem] = None
        self.preview_circle: Optional[QGraphicsEllipseItem] = None
        self.center_marker: Optional[QGraphicsEllipseItem] = None
        self.radius_lines: List[QGraphicsLineItem] = []
        self.point_markers: List[QGraphicsEllipseItem] = []

        # Styling
        self.preview_pen = QPen()
        self.preview_pen.setColor(Qt.cyan)
        self.preview_pen.setWidth(1)
        self.preview_pen.setStyle(Qt.DashLine)

        self.circle_pen = QPen()
        self.circle_pen.setColor(Qt.gray)
        self.circle_pen.setWidth(1)
        self.circle_pen.setStyle(Qt.DotLine)

        self.marker_pen = QPen()
        self.marker_pen.setColor(Qt.red)
        self.marker_pen.setWidth(2)

        self.logger = logging.getLogger(__name__)

    def activate(self):
        """Activate the arc tool."""
        self.start_tool()
        self.update_status_message(f"Arc tool activated - Mode: {self.arc_mode}")
        self._update_instructions()

    def deactivate(self):
        """Deactivate the arc tool."""
        self.cancel()
        self.update_status_message("Arc tool deactivated")

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

        if self.arc_mode == ArcMode.THREE_POINT:
            return self._handle_three_point_click(snapped_point)
        elif self.arc_mode == ArcMode.START_CENTER_END:
            return self._handle_start_center_end_click(snapped_point)
        elif self.arc_mode == ArcMode.CENTER_START_END:
            return self._handle_center_start_end_click(snapped_point)

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

        if self.arc_mode == ArcMode.THREE_POINT:
            self._update_three_point_preview(current_point)
        elif self.arc_mode == ArcMode.START_CENTER_END:
            self._update_start_center_end_preview(current_point)
        elif self.arc_mode == ArcMode.CENTER_START_END:
            self._update_center_start_end_preview(current_point)

        return True

    def on_mouse_release(self, event: QMouseEvent) -> bool:
        """Handle mouse release events."""
        return False

    def on_key_press(self, event: QKeyEvent) -> bool:
        """Handle key press events."""
        # Handle base tool keys first
        if super().on_key_press(event):
            return True

        # Arc-specific key handling
        if event.key() == Qt.Key_M:
            self._cycle_arc_mode()
            return True
        elif event.key() == Qt.Key_1:
            self.set_arc_mode(ArcMode.THREE_POINT)
            return True
        elif event.key() == Qt.Key_2:
            self.set_arc_mode(ArcMode.START_CENTER_END)
            return True
        elif event.key() == Qt.Key_3:
            self.set_arc_mode(ArcMode.CENTER_START_END)
            return True

        return False

    def _handle_three_point_click(self, point: QPointF) -> bool:
        """Handle mouse click for three-point mode."""
        self.arc_points.append(point)
        self.points.append(point)
        self._add_point_marker(point)

        if len(self.arc_points) == 1:
            self.state = ToolState.DRAWING
            self.update_status_message("Click second point on arc")

        elif len(self.arc_points) == 2:
            self.update_status_message("Click third point on arc")

        elif len(self.arc_points) == 3:
            # Calculate and create arc from three points
            try:
                (
                    center,
                    radius,
                    start_angle,
                    end_angle,
                ) = self._calculate_arc_from_three_points(
                    self.arc_points[0], self.arc_points[1], self.arc_points[2]
                )
                self._create_arc(center, radius, start_angle, end_angle)
                self.reset()
            except ValueError as e:
                self.update_status_message(f"Cannot create arc: {e}")
                self._remove_last_point_marker()
                self.arc_points.pop()
                self.points.pop()

        return True

    def _handle_start_center_end_click(self, point: QPointF) -> bool:
        """Handle mouse click for start-center-end mode."""
        if not self.start_point:
            # First click - start point
            self.start_point = point
            self.points.append(point)
            self._add_point_marker(point)
            self.state = ToolState.DRAWING
            self.update_status_message("Click center point")

        elif not self.center_point:
            # Second click - center point
            self.center_point = point
            self.points.append(point)
            self._add_center_marker(point)
            self.update_status_message("Click end point")

        else:
            # Third click - end point
            self.end_point = point
            radius = self._calculate_distance(self.center_point, self.start_point)
            start_angle, end_angle = self._calculate_angles_from_points(
                self.center_point, self.start_point, self.end_point
            )
            self._create_arc(self.center_point, radius, start_angle, end_angle)
            self.reset()

        return True

    def _handle_center_start_end_click(self, point: QPointF) -> bool:
        """Handle mouse click for center-start-end mode."""
        if not self.center_point:
            # First click - center point
            self.center_point = point
            self.points.append(point)
            self._add_center_marker(point)
            self.state = ToolState.DRAWING
            self.update_status_message("Click start point")

        elif not self.start_point:
            # Second click - start point
            self.start_point = point
            self.points.append(point)
            self._add_point_marker(point)
            self.update_status_message("Click end point")

        else:
            # Third click - end point
            self.end_point = point
            radius = self._calculate_distance(self.center_point, self.start_point)
            start_angle, end_angle = self._calculate_angles_from_points(
                self.center_point, self.start_point, self.end_point
            )
            self._create_arc(self.center_point, radius, start_angle, end_angle)
            self.reset()

        return True

    def _create_arc(
        self, center: QPointF, radius: float, start_angle: float, end_angle: float
    ):
        """
        Create an arc using the command pattern.

        Args:
            center: Arc center point
            radius: Arc radius
            start_angle: Start angle in radians
            end_angle: End angle in radians
        """
        if not self.current_document_id:
            self.logger.warning("No document context set for arc creation")
            return

        if radius <= 0:
            self.logger.warning("Invalid radius for arc creation")
            return

        # Convert QPointF to dict format
        center_dict = {"x": center.x(), "y": center.y(), "z": 0.0}

        # Create command
        command = create_draw_arc_command(
            self.api_client,
            self.current_document_id,
            center_dict,
            radius,
            start_angle,
            end_angle,
            layer_id=self.current_layer_id,
        )

        # Execute command asynchronously
        asyncio.create_task(self._execute_command(command))

        self.logger.info(
            f"Created arc at ({center.x():.2f}, {center.y():.2f}) "
            f"radius {radius:.2f} from {math.degrees(start_angle):.1f}° "
            f"to {math.degrees(end_angle):.1f}°"
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

    def _update_three_point_preview(self, current_point: QPointF):
        """Update preview for three-point mode."""
        if len(self.arc_points) < 2:
            return

        try:
            if len(self.arc_points) == 2:
                # Preview with current mouse position as third point
                (
                    center,
                    radius,
                    start_angle,
                    end_angle,
                ) = self._calculate_arc_from_three_points(
                    self.arc_points[0], self.arc_points[1], current_point
                )
                self._update_arc_preview(center, radius, start_angle, end_angle)

        except ValueError:
            # Points are collinear or too close - clear preview
            self._clear_arc_preview()

    def _update_start_center_end_preview(self, current_point: QPointF):
        """Update preview for start-center-end mode."""
        if self.start_point and self.center_point:
            # Preview arc with current mouse position as end point
            radius = self._calculate_distance(self.center_point, self.start_point)
            start_angle, end_angle = self._calculate_angles_from_points(
                self.center_point, self.start_point, current_point
            )
            self._update_arc_preview(self.center_point, radius, start_angle, end_angle)
            self._update_construction_lines()

        elif self.start_point:
            # Show line from start to current point (future center)
            self._update_radius_line(self.start_point, current_point)

    def _update_center_start_end_preview(self, current_point: QPointF):
        """Update preview for center-start-end mode."""
        if self.center_point and self.start_point:
            # Preview arc with current mouse position as end point
            radius = self._calculate_distance(self.center_point, self.start_point)
            start_angle, end_angle = self._calculate_angles_from_points(
                self.center_point, self.start_point, current_point
            )
            self._update_arc_preview(self.center_point, radius, start_angle, end_angle)
            self._update_construction_lines()

        elif self.center_point:
            # Show radius line from center to current point
            self._update_radius_line(self.center_point, current_point)

    def _update_arc_preview(
        self, center: QPointF, radius: float, start_angle: float, end_angle: float
    ):
        """Update the preview arc."""
        # Clear existing preview
        self._clear_arc_preview()

        if radius > 0:
            # Create arc path
            path = QPainterPath()

            # Calculate arc span
            span_angle = end_angle - start_angle

            # Normalize span to be positive and <= 2π
            while span_angle <= 0:
                span_angle += 2 * math.pi
            while span_angle > 2 * math.pi:
                span_angle -= 2 * math.pi

            # Create arc
            rect_x = center.x() - radius
            rect_y = center.y() - radius
            rect_width = radius * 2
            rect_height = radius * 2

            # Convert angles to degrees for Qt (Qt uses degrees, with 0° at 3 o'clock)
            start_deg = -math.degrees(
                start_angle
            )  # Negative because Qt Y-axis is flipped
            span_deg = -math.degrees(span_angle)  # Negative for counterclockwise

            path.arcMoveTo(rect_x, rect_y, rect_width, rect_height, start_deg)
            path.arcTo(rect_x, rect_y, rect_width, rect_height, start_deg, span_deg)

            # Create preview item
            self.preview_arc = self.scene.addPath(path, self.preview_pen)
            self.preview_items.append(self.preview_arc)

            # Show full circle faintly for reference
            if self.arc_mode != ArcMode.THREE_POINT:
                self.preview_circle = self.scene.addEllipse(
                    rect_x, rect_y, rect_width, rect_height, self.circle_pen
                )
                self.preview_items.append(self.preview_circle)

    def _update_construction_lines(self):
        """Update construction lines for center-based modes."""
        if not self.center_point:
            return

        # Clear existing radius lines
        for line in self.radius_lines:
            if line.scene():
                self.scene.removeItem(line)
        self.radius_lines.clear()

        # Add radius lines
        if self.start_point:
            line = self.scene.addLine(
                self.center_point.x(),
                self.center_point.y(),
                self.start_point.x(),
                self.start_point.y(),
                self.circle_pen,
            )
            self.radius_lines.append(line)
            self.preview_items.append(line)

    def _update_radius_line(self, start: QPointF, end: QPointF):
        """Update a single radius line."""
        # Clear existing radius lines
        for line in self.radius_lines:
            if line.scene():
                self.scene.removeItem(line)
        self.radius_lines.clear()

        # Add new line
        line = self.scene.addLine(
            start.x(), start.y(), end.x(), end.y(), self.preview_pen
        )
        self.radius_lines.append(line)
        self.preview_items.append(line)

    def _clear_arc_preview(self):
        """Clear the arc preview."""
        if self.preview_arc:
            self.scene.removeItem(self.preview_arc)
            self.preview_arc = None

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

    def _calculate_angle(self, center: QPointF, point: QPointF) -> float:
        """Calculate angle from center to point in radians."""
        dx = point.x() - center.x()
        dy = point.y() - center.y()
        return math.atan2(dy, dx)

    def _calculate_angles_from_points(
        self, center: QPointF, start: QPointF, end: QPointF
    ) -> Tuple[float, float]:
        """
        Calculate start and end angles from points.

        Args:
            center: Arc center
            start: Start point
            end: End point

        Returns:
            Tuple of (start_angle, end_angle) in radians
        """
        start_angle = self._calculate_angle(center, start)
        end_angle = self._calculate_angle(center, end)

        # Ensure end_angle > start_angle for counterclockwise arc
        if end_angle <= start_angle:
            end_angle += 2 * math.pi

        return start_angle, end_angle

    def _calculate_arc_from_three_points(
        self, p1: QPointF, p2: QPointF, p3: QPointF
    ) -> Tuple[QPointF, float, float, float]:
        """
        Calculate arc center, radius, and angles from three points.

        Args:
            p1: First point on arc
            p2: Second point on arc
            p3: Third point on arc

        Returns:
            Tuple of (center, radius, start_angle, end_angle)

        Raises:
            ValueError: If points are collinear
        """
        # First calculate the circle center and radius
        center, radius = self._calculate_circle_from_three_points(p1, p2, p3)

        # Calculate angles for each point
        angle1 = self._calculate_angle(center, p1)
        angle2 = self._calculate_angle(center, p2)
        angle3 = self._calculate_angle(center, p3)

        # Determine the arc direction and order
        # We want the arc to go from p1 to p3 passing through p2
        angles = [(angle1, 1), (angle2, 2), (angle3, 3)]

        # Normalize angles to [0, 2π]
        normalized_angles = []
        for angle, point_num in angles:
            while angle < 0:
                angle += 2 * math.pi
            while angle >= 2 * math.pi:
                angle -= 2 * math.pi
            normalized_angles.append((angle, point_num))

        # Sort by angle
        normalized_angles.sort(key=lambda x: x[0])

        # Find the order that puts p2 between p1 and p3
        for i in range(3):
            for j in range(3):
                for k in range(3):
                    if i != j and j != k and i != k:
                        order = [
                            normalized_angles[i],
                            normalized_angles[j],
                            normalized_angles[k],
                        ]
                        if order[0][1] == 1 and order[1][1] == 2 and order[2][1] == 3:
                            return center, radius, order[0][0], order[2][0]

        # If we can't find a good order, use p1 to p3
        return center, radius, angle1, angle3

    def _calculate_circle_from_three_points(
        self, p1: QPointF, p2: QPointF, p3: QPointF
    ) -> Tuple[QPointF, float]:
        """Calculate circle center and radius from three points."""
        x1, y1 = p1.x(), p1.y()
        x2, y2 = p2.x(), p2.y()
        x3, y3 = p3.x(), p3.y()

        # Check for collinear points
        area = abs((x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2)) / 2)
        if area < 1e-6:
            raise ValueError("Points are collinear")

        # Calculate circumcenter
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

    def _cycle_arc_mode(self):
        """Cycle through arc drawing modes."""
        modes = [
            ArcMode.THREE_POINT,
            ArcMode.START_CENTER_END,
            ArcMode.CENTER_START_END,
        ]
        current_index = modes.index(self.arc_mode)
        next_index = (current_index + 1) % len(modes)

        old_mode = self.arc_mode
        self.arc_mode = modes[next_index]

        # Reset current operation
        self.cancel()
        self.activate()

        self.update_status_message(f"Arc mode changed: {old_mode} -> {self.arc_mode}")

    def set_arc_mode(self, mode: str):
        """
        Set the arc drawing mode.

        Args:
            mode: Arc mode
        """
        if mode in [
            ArcMode.THREE_POINT,
            ArcMode.START_CENTER_END,
            ArcMode.CENTER_START_END,
        ]:
            old_mode = self.arc_mode
            self.arc_mode = mode

            # Reset if mode changed
            if old_mode != mode:
                self.cancel()
                if self.state != ToolState.INACTIVE:
                    self.activate()

                self.update_status_message(f"Arc mode set to: {mode}")

    def _update_instructions(self):
        """Update status with current mode instructions."""
        if self.arc_mode == ArcMode.THREE_POINT:
            self.update_status_message("Click three points on the arc")
        elif self.arc_mode == ArcMode.START_CENTER_END:
            self.update_status_message("Click start point, center, then end point")
        elif self.arc_mode == ArcMode.CENTER_START_END:
            self.update_status_message("Click center, start point, then end point")

    def reset(self):
        """Reset tool to initial state for next operation."""
        super().reset()

        # Clear arc-specific state
        self.arc_points.clear()
        self.center_point = None
        self.start_point = None
        self.end_point = None
        self.arc_center = None
        self.arc_radius = 0.0
        self.start_angle = 0.0
        self.end_angle = 0.0

        # Clear visual elements
        self._clear_all_visuals()

        self._update_instructions()

    def cancel(self):
        """Cancel the current tool operation."""
        self._clear_all_visuals()
        super().cancel()

    def _clear_all_visuals(self):
        """Clear all visual elements."""
        # Clear preview
        if self.preview_arc:
            if self.preview_arc.scene():
                self.scene.removeItem(self.preview_arc)
            self.preview_arc = None

        if self.preview_circle:
            if self.preview_circle.scene():
                self.scene.removeItem(self.preview_circle)
            self.preview_circle = None

        # Clear markers
        if self.center_marker:
            if self.center_marker.scene():
                self.scene.removeItem(self.center_marker)
            self.center_marker = None

        for marker in self.point_markers:
            if marker.scene():
                self.scene.removeItem(marker)
        self.point_markers.clear()

        # Clear radius lines
        for line in self.radius_lines:
            if line.scene():
                self.scene.removeItem(line)
        self.radius_lines.clear()

    def get_tool_info(self):
        """Get tool information including arc-specific data."""
        info = super().get_tool_info()
        info.update(
            {
                "arc_mode": self.arc_mode,
                "arc_points": len(self.arc_points),
                "center_point": self.center_point is not None,
                "start_point": self.start_point is not None,
                "end_point": self.end_point is not None,
                "arc_radius": self.arc_radius,
                "start_angle_deg": math.degrees(self.start_angle)
                if self.start_angle
                else 0,
                "end_angle_deg": math.degrees(self.end_angle) if self.end_angle else 0,
                "has_preview": self.preview_arc is not None,
            }
        )
        return info
