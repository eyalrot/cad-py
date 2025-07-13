"""
Rotate tool for CAD drawing operations.

This module provides an interactive rotate tool that allows users to rotate
selected geometry around a specified point with angle input and real-time preview.
"""

import asyncio
import logging
import math
from enum import Enum, auto
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QLineF, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPen, QTransform
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem

from ...core.selection_manager import SelectionManager
from .base_tool import BaseTool, ToolState

logger = logging.getLogger(__name__)


class RotateState(Enum):
    """States for rotate tool operation."""

    WAITING_FOR_SELECTION = auto()
    WAITING_FOR_CENTER = auto()
    WAITING_FOR_REFERENCE = auto()
    WAITING_FOR_ANGLE = auto()
    ROTATING = auto()
    COMPLETED = auto()


class RotateTool(BaseTool):
    """
    Interactive rotate tool for rotating selected geometry.

    Features:
    - Rotate selected objects around a specified center point
    - Reference angle and target angle selection
    - Real-time preview during rotation
    - Angle input with visual feedback
    - Snap integration for precise positioning
    - Visual feedback with rotation guides
    - Undo/redo support through command pattern
    """

    # Signals
    rotate_started = Signal(QPointF)  # center point
    rotate_preview = Signal(QPointF, float)  # center, angle
    rotate_completed = Signal(QPointF, float)  # center, angle
    rotate_cancelled = Signal()

    def __init__(
        self,
        scene,
        api_client,
        command_manager,
        snap_engine,
        selection_manager: SelectionManager,
    ):
        super().__init__(scene, api_client, command_manager, snap_engine)

        self.selection_manager = selection_manager
        self.rotate_state = RotateState.WAITING_FOR_SELECTION

        # Rotation operation data
        self.center_point: Optional[QPointF] = None
        self.reference_point: Optional[QPointF] = None
        self.current_point: Optional[QPointF] = None
        self.selected_items: List[QGraphicsItem] = []

        # Angle calculation
        self.reference_angle = 0.0
        self.current_angle = 0.0
        self.total_rotation = 0.0

        # Preview graphics
        self.preview_items: List[QGraphicsItem] = []
        self.center_marker: Optional[QGraphicsEllipseItem] = None
        self.reference_line: Optional[QGraphicsLineItem] = None
        self.angle_line: Optional[QGraphicsLineItem] = None

        # Visual properties
        self.preview_pen = QPen(QColor(255, 255, 100, 180))  # Yellow for rotate
        self.preview_pen.setWidth(1)
        self.preview_pen.setStyle(Qt.DashLine)

        self.center_pen = QPen(QColor(255, 100, 100, 200))
        self.center_pen.setWidth(2)

        self.reference_pen = QPen(QColor(100, 255, 100, 200))
        self.reference_pen.setWidth(1)
        self.reference_pen.setStyle(Qt.DotLine)

        self.angle_pen = QPen(QColor(255, 150, 0, 200))
        self.angle_pen.setWidth(2)

        logger.debug("Rotate tool initialized")

    def get_tool_name(self) -> str:
        """Get tool display name."""
        return "Rotate"

    def get_status_text(self) -> str:
        """Get current status text."""
        if self.rotate_state == RotateState.WAITING_FOR_SELECTION:
            return "Select objects to rotate"
        elif self.rotate_state == RotateState.WAITING_FOR_CENTER:
            return "Select center point for rotation"
        elif self.rotate_state == RotateState.WAITING_FOR_REFERENCE:
            return "Select reference angle (or press Enter for 0°)"
        elif self.rotate_state == RotateState.WAITING_FOR_ANGLE:
            return f"Select rotation angle (current: {math.degrees(self.total_rotation):.1f}°)"
        elif self.rotate_state == RotateState.ROTATING:
            return "Rotating objects..."
        else:
            return "Rotate tool ready"

    def activate(self) -> bool:
        """Activate the rotate tool."""
        if not super().activate():
            return False

        # Check if there are selected objects
        if self.selection_manager.has_selection():
            self.selected_items = list(self.selection_manager.get_selected_items())
            self.rotate_state = RotateState.WAITING_FOR_CENTER
            logger.debug(
                f"Rotate tool activated with {len(self.selected_items)} selected items"
            )
        else:
            self.rotate_state = RotateState.WAITING_FOR_SELECTION
            logger.debug("Rotate tool activated, waiting for selection")

        return True

    def deactivate(self):
        """Deactivate the rotate tool."""
        self._clear_preview()
        self.rotate_state = RotateState.WAITING_FOR_SELECTION
        self.center_point = None
        self.reference_point = None
        self.current_point = None
        self.selected_items.clear()
        self.reference_angle = 0.0
        self.current_angle = 0.0
        self.total_rotation = 0.0

        super().deactivate()
        logger.debug("Rotate tool deactivated")

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        """Handle mouse press events."""
        world_pos = self.scene_pos_from_event(event)

        # Apply snapping
        snap_result = self.snap_engine.snap_point(world_pos, self.view)
        if snap_result.snapped:
            world_pos = snap_result.point

        if self.rotate_state == RotateState.WAITING_FOR_SELECTION:
            # Let selection manager handle the click
            return False

        elif self.rotate_state == RotateState.WAITING_FOR_CENTER:
            self._set_center_point(world_pos)
            return True

        elif self.rotate_state == RotateState.WAITING_FOR_REFERENCE:
            self._set_reference_point(world_pos)
            return True

        elif self.rotate_state == RotateState.WAITING_FOR_ANGLE:
            self._execute_rotation(world_pos)
            return True

        return False

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        """Handle mouse move events."""
        if self.rotate_state not in [
            RotateState.WAITING_FOR_REFERENCE,
            RotateState.WAITING_FOR_ANGLE,
        ]:
            return False

        world_pos = self.scene_pos_from_event(event)

        # Apply snapping
        snap_result = self.snap_engine.snap_point(
            world_pos, self.view, self.center_point
        )
        if snap_result.snapped:
            world_pos = snap_result.point

        if self.rotate_state == RotateState.WAITING_FOR_REFERENCE:
            self._update_reference_preview(world_pos)
        elif self.rotate_state == RotateState.WAITING_FOR_ANGLE:
            self._update_angle_preview(world_pos)

        return True

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle key press events."""
        if event.key() == Qt.Key_Escape:
            self._cancel_rotation()
            return True
        elif event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            if self.rotate_state == RotateState.WAITING_FOR_REFERENCE:
                # Use 0 degrees as reference
                self._set_reference_angle(0.0)
                return True
            elif (
                self.rotate_state == RotateState.WAITING_FOR_ANGLE
                and self.current_point
            ):
                self._execute_rotation(self.current_point)
                return True

        return super().handle_key_press(event)

    def _set_center_point(self, point: QPointF):
        """Set the center point for rotation."""
        self.center_point = point
        self.rotate_state = RotateState.WAITING_FOR_REFERENCE

        # Create center marker
        self._create_center_marker()

        # Emit signal
        self.rotate_started.emit(self.center_point)

        logger.debug(f"Rotation center set to ({point.x():.2f}, {point.y():.2f})")

    def _set_reference_point(self, point: QPointF):
        """Set the reference point for angle calculation."""
        if not self.center_point:
            return

        self.reference_point = point

        # Calculate reference angle
        reference_vector = QLineF(self.center_point, self.reference_point)
        self.reference_angle = math.radians(reference_vector.angle())

        self.rotate_state = RotateState.WAITING_FOR_ANGLE

        # Create reference line
        self._create_reference_line()

        logger.debug(
            f"Reference angle set to {math.degrees(self.reference_angle):.1f}°"
        )

    def _set_reference_angle(self, angle_degrees: float):
        """Set reference angle directly."""
        self.reference_angle = math.radians(angle_degrees)
        self.rotate_state = RotateState.WAITING_FOR_ANGLE

        # Create reference line at the specified angle
        radius = 50  # Arbitrary radius for visualization
        end_point = QPointF(
            self.center_point.x() + radius * math.cos(self.reference_angle),
            self.center_point.y() + radius * math.sin(self.reference_angle),
        )
        self.reference_point = end_point
        self._create_reference_line()

        logger.debug(f"Reference angle set to {angle_degrees:.1f}°")

    def _update_reference_preview(self, current_point: QPointF):
        """Update reference angle preview."""
        if not self.center_point:
            return

        self.current_point = current_point

        # Update reference line preview
        if self.reference_line:
            self.reference_line.setLine(
                self.center_point.x(),
                self.center_point.y(),
                current_point.x(),
                current_point.y(),
            )

    def _update_angle_preview(self, current_point: QPointF):
        """Update rotation angle preview."""
        if not self.center_point or not self.reference_point:
            return

        self.current_point = current_point

        # Calculate current angle
        current_vector = QLineF(self.center_point, current_point)
        self.current_angle = math.radians(current_vector.angle())

        # Calculate total rotation
        self.total_rotation = self.current_angle - self.reference_angle

        # Normalize angle to [-π, π]
        while self.total_rotation > math.pi:
            self.total_rotation -= 2 * math.pi
        while self.total_rotation < -math.pi:
            self.total_rotation += 2 * math.pi

        # Update angle line
        if self.angle_line:
            self.angle_line.setLine(
                self.center_point.x(),
                self.center_point.y(),
                current_point.x(),
                current_point.y(),
            )
        else:
            self._create_angle_line()

        # Update preview items
        self._update_preview_items()

        # Emit signal
        self.rotate_preview.emit(self.center_point, self.total_rotation)

    def _create_center_marker(self):
        """Create the center point marker."""
        if self.center_marker:
            self.scene.removeItem(self.center_marker)

        size = 6
        self.center_marker = QGraphicsEllipseItem(
            self.center_point.x() - size / 2,
            self.center_point.y() - size / 2,
            size,
            size,
        )
        self.center_marker.setPen(self.center_pen)
        self.center_marker.setZValue(1000)
        self.scene.addItem(self.center_marker)

    def _create_reference_line(self):
        """Create the reference line."""
        if self.reference_line:
            self.scene.removeItem(self.reference_line)

        self.reference_line = QGraphicsLineItem()
        self.reference_line.setPen(self.reference_pen)
        self.reference_line.setZValue(999)
        self.scene.addItem(self.reference_line)

        if self.reference_point:
            self.reference_line.setLine(
                self.center_point.x(),
                self.center_point.y(),
                self.reference_point.x(),
                self.reference_point.y(),
            )

    def _create_angle_line(self):
        """Create the angle line."""
        if self.angle_line:
            self.scene.removeItem(self.angle_line)

        self.angle_line = QGraphicsLineItem()
        self.angle_line.setPen(self.angle_pen)
        self.angle_line.setZValue(998)
        self.scene.addItem(self.angle_line)

    def _update_preview_items(self):
        """Update preview items showing rotated positions."""
        if not self.center_point or self.total_rotation == 0.0:
            return

        # Remove existing preview items
        self._clear_preview_items()

        # Create rotation transform
        transform = QTransform()
        transform.translate(self.center_point.x(), self.center_point.y())
        transform.rotate(math.degrees(self.total_rotation))
        transform.translate(-self.center_point.x(), -self.center_point.y())

        # Create preview items for each selected item
        for item in self.selected_items:
            preview_item = self._create_preview_item(item, transform)
            if preview_item:
                self.preview_items.append(preview_item)
                self.scene.addItem(preview_item)

    def _create_preview_item(
        self, original_item: QGraphicsItem, transform: QTransform
    ) -> Optional[QGraphicsItem]:
        """Create a preview item for the given original item."""
        try:
            # Clone the item's geometry with rotation
            if hasattr(original_item, "rect"):
                # Rectangle item
                from PySide6.QtWidgets import QGraphicsRectItem

                rect = original_item.rect()
                transformed_rect = transform.mapRect(rect)
                preview = QGraphicsRectItem(transformed_rect)

            elif hasattr(original_item, "line"):
                # Line item
                from PySide6.QtWidgets import QGraphicsLineItem

                line = original_item.line()
                transformed_line = transform.map(line)
                preview = QGraphicsLineItem(transformed_line)

            elif hasattr(original_item, "path"):
                # Path item
                from PySide6.QtWidgets import QGraphicsPathItem

                path = original_item.path()
                transformed_path = transform.map(path)
                preview = QGraphicsPathItem(transformed_path)

            else:
                # Generic item - use bounding rect
                from PySide6.QtWidgets import QGraphicsRectItem

                rect = original_item.boundingRect()
                transformed_rect = transform.mapRect(rect)
                preview = QGraphicsRectItem(transformed_rect)

            # Set preview appearance
            preview.setPen(self.preview_pen)
            preview.setOpacity(0.7)
            preview.setZValue(997)

            return preview

        except Exception as e:
            logger.warning(f"Could not create preview for item: {e}")
            return None

    def _clear_preview_items(self):
        """Clear all preview items."""
        for item in self.preview_items:
            if item.scene():
                self.scene.removeItem(item)
        self.preview_items.clear()

    def _clear_preview(self):
        """Clear all preview graphics."""
        self._clear_preview_items()

        for item in [self.center_marker, self.reference_line, self.angle_line]:
            if item and item.scene():
                self.scene.removeItem(item)

        self.center_marker = None
        self.reference_line = None
        self.angle_line = None

    async def _execute_rotation(self, angle_point: QPointF):
        """Execute the rotation operation."""
        if not self.center_point or not self.selected_items:
            return

        # Update final angle
        self._update_angle_preview(angle_point)

        self.rotate_state = RotateState.ROTATING

        try:
            # Clear preview
            self._clear_preview()

            # Create rotate command
            from ...core.commands import RotateCommand

            # Get entity IDs from selected items
            entity_ids = []
            for item in self.selected_items:
                if hasattr(item, "entity_id"):
                    entity_ids.append(item.entity_id)

            if entity_ids:
                # Create and execute rotate command
                rotate_command = RotateCommand(
                    self.api_client,
                    entity_ids,
                    self.center_point.x(),
                    self.center_point.y(),
                    math.degrees(self.total_rotation),
                )

                # Execute through command manager for undo support
                success = await self.command_manager.execute_command(rotate_command)

                if success:
                    # Emit completion signal
                    self.rotate_completed.emit(self.center_point, self.total_rotation)

                    logger.info(
                        f"Rotated {len(entity_ids)} objects by {math.degrees(self.total_rotation):.1f}°"
                    )

                    # Reset tool state
                    self._reset_tool()
                else:
                    logger.error("Rotate command execution failed")
                    self._cancel_rotation()
            else:
                logger.warning("No valid entities found for rotation")
                self._cancel_rotation()

        except Exception as e:
            logger.error(f"Error executing rotation: {e}")
            self._cancel_rotation()

    def _cancel_rotation(self):
        """Cancel the current rotation operation."""
        self._clear_preview()

        if self.rotate_state != RotateState.WAITING_FOR_SELECTION:
            self.rotate_state = (
                RotateState.WAITING_FOR_CENTER
                if self.selected_items
                else RotateState.WAITING_FOR_SELECTION
            )

        self.center_point = None
        self.reference_point = None
        self.current_point = None
        self.reference_angle = 0.0
        self.current_angle = 0.0
        self.total_rotation = 0.0

        # Emit cancellation signal
        self.rotate_cancelled.emit()

        logger.debug("Rotation operation cancelled")

    def _reset_tool(self):
        """Reset tool to initial state."""
        self.rotate_state = RotateState.WAITING_FOR_SELECTION
        self.center_point = None
        self.reference_point = None
        self.current_point = None
        self.selected_items.clear()
        self.reference_angle = 0.0
        self.current_angle = 0.0
        self.total_rotation = 0.0

        # Clear selection
        self.selection_manager.clear_selection()

    def selection_changed(self, selected_items: List[QGraphicsItem]):
        """Handle selection changes."""
        if self.rotate_state == RotateState.WAITING_FOR_SELECTION and selected_items:
            self.selected_items = selected_items
            self.rotate_state = RotateState.WAITING_FOR_CENTER
            logger.debug(
                f"Rotate tool updated with {len(selected_items)} selected items"
            )

    def get_tool_info(self) -> Dict[str, Any]:
        """Get current tool information."""
        return {
            **super().get_tool_info(),
            "rotate_state": self.rotate_state.name,
            "center_point": {"x": self.center_point.x(), "y": self.center_point.y()}
            if self.center_point
            else None,
            "reference_angle_deg": math.degrees(self.reference_angle),
            "current_angle_deg": math.degrees(self.current_angle),
            "total_rotation_deg": math.degrees(self.total_rotation),
            "selected_count": len(self.selected_items),
        }
