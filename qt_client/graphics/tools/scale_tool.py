"""
Scale tool for CAD drawing operations.

This module provides an interactive scale tool that allows users to scale
selected geometry with base point selection and real-time preview.
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


class ScaleState(Enum):
    """States for scale tool operation."""

    WAITING_FOR_SELECTION = auto()
    WAITING_FOR_BASE_POINT = auto()
    WAITING_FOR_REFERENCE = auto()
    WAITING_FOR_SCALE = auto()
    SCALING = auto()
    COMPLETED = auto()


class ScaleMode(Enum):
    """Scaling modes."""

    UNIFORM = auto()  # Uniform scaling in both directions
    NON_UNIFORM = auto()  # Different scaling in X and Y
    REFERENCE = auto()  # Scale based on reference distance


class ScaleTool(BaseTool):
    """
    Interactive scale tool for scaling selected geometry.

    Features:
    - Scale selected objects from a specified base point
    - Uniform and non-uniform scaling modes
    - Reference-based scaling
    - Real-time preview during scaling
    - Scale factor input with visual feedback
    - Snap integration for precise positioning
    - Visual feedback with scaling guides
    - Undo/redo support through command pattern
    """

    # Signals
    scale_started = Signal(QPointF)  # base point
    scale_preview = Signal(QPointF, float, float)  # base, scale_x, scale_y
    scale_completed = Signal(QPointF, float, float)  # base, scale_x, scale_y
    scale_cancelled = Signal()

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
        self.scale_state = ScaleState.WAITING_FOR_SELECTION
        self.scale_mode = ScaleMode.UNIFORM

        # Scale operation data
        self.base_point: Optional[QPointF] = None
        self.reference_point: Optional[QPointF] = None
        self.current_point: Optional[QPointF] = None
        self.selected_items: List[QGraphicsItem] = []

        # Scale factors
        self.reference_distance = 1.0
        self.current_distance = 1.0
        self.scale_factor_x = 1.0
        self.scale_factor_y = 1.0

        # Preview graphics
        self.preview_items: List[QGraphicsItem] = []
        self.base_marker: Optional[QGraphicsEllipseItem] = None
        self.reference_line: Optional[QGraphicsLineItem] = None
        self.scale_line: Optional[QGraphicsLineItem] = None

        # Visual properties
        self.preview_pen = QPen(QColor(255, 100, 255, 180))  # Magenta for scale
        self.preview_pen.setWidth(1)
        self.preview_pen.setStyle(Qt.DashLine)

        self.base_pen = QPen(QColor(255, 100, 100, 200))
        self.base_pen.setWidth(2)

        self.reference_pen = QPen(QColor(100, 255, 100, 200))
        self.reference_pen.setWidth(1)
        self.reference_pen.setStyle(Qt.DotLine)

        self.scale_pen = QPen(QColor(100, 150, 255, 200))
        self.scale_pen.setWidth(2)

        logger.debug("Scale tool initialized")

    def get_tool_name(self) -> str:
        """Get tool display name."""
        return f"Scale ({self.scale_mode.name.title()})"

    def get_status_text(self) -> str:
        """Get current status text."""
        if self.scale_state == ScaleState.WAITING_FOR_SELECTION:
            return "Select objects to scale"
        elif self.scale_state == ScaleState.WAITING_FOR_BASE_POINT:
            return "Select base point for scaling"
        elif self.scale_state == ScaleState.WAITING_FOR_REFERENCE:
            return "Select reference point (or press Enter for scale factor input)"
        elif self.scale_state == ScaleState.WAITING_FOR_SCALE:
            if self.scale_mode == ScaleMode.REFERENCE:
                return f"Select scale point (factor: {self.scale_factor_x:.2f})"
            else:
                return f"Select scale point (factor: {self.scale_factor_x:.2f})"
        elif self.scale_state == ScaleState.SCALING:
            return "Scaling objects..."
        else:
            return "Scale tool ready"

    def activate(self) -> bool:
        """Activate the scale tool."""
        if not super().activate():
            return False

        # Check if there are selected objects
        if self.selection_manager.has_selection():
            self.selected_items = list(self.selection_manager.get_selected_items())
            self.scale_state = ScaleState.WAITING_FOR_BASE_POINT
            logger.debug(
                f"Scale tool activated with {len(self.selected_items)} selected items"
            )
        else:
            self.scale_state = ScaleState.WAITING_FOR_SELECTION
            logger.debug("Scale tool activated, waiting for selection")

        return True

    def deactivate(self):
        """Deactivate the scale tool."""
        self._clear_preview()
        self.scale_state = ScaleState.WAITING_FOR_SELECTION
        self.base_point = None
        self.reference_point = None
        self.current_point = None
        self.selected_items.clear()
        self.reference_distance = 1.0
        self.current_distance = 1.0
        self.scale_factor_x = 1.0
        self.scale_factor_y = 1.0

        super().deactivate()
        logger.debug("Scale tool deactivated")

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        """Handle mouse press events."""
        world_pos = self.scene_pos_from_event(event)

        # Apply snapping
        snap_result = self.snap_engine.snap_point(world_pos, self.view)
        if snap_result.snapped:
            world_pos = snap_result.point

        if self.scale_state == ScaleState.WAITING_FOR_SELECTION:
            # Let selection manager handle the click
            return False

        elif self.scale_state == ScaleState.WAITING_FOR_BASE_POINT:
            self._set_base_point(world_pos)
            return True

        elif self.scale_state == ScaleState.WAITING_FOR_REFERENCE:
            self._set_reference_point(world_pos)
            return True

        elif self.scale_state == ScaleState.WAITING_FOR_SCALE:
            self._execute_scale(world_pos)
            return True

        return False

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        """Handle mouse move events."""
        if self.scale_state not in [
            ScaleState.WAITING_FOR_REFERENCE,
            ScaleState.WAITING_FOR_SCALE,
        ]:
            return False

        world_pos = self.scene_pos_from_event(event)

        # Apply snapping
        snap_result = self.snap_engine.snap_point(world_pos, self.view, self.base_point)
        if snap_result.snapped:
            world_pos = snap_result.point

        if self.scale_state == ScaleState.WAITING_FOR_REFERENCE:
            self._update_reference_preview(world_pos)
        elif self.scale_state == ScaleState.WAITING_FOR_SCALE:
            self._update_scale_preview(world_pos)

        return True

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle key press events."""
        if event.key() == Qt.Key_Escape:
            self._cancel_scale()
            return True
        elif event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            if self.scale_state == ScaleState.WAITING_FOR_REFERENCE:
                # Skip reference point, use direct scale factor
                self._skip_reference_point()
                return True
            elif (
                self.scale_state == ScaleState.WAITING_FOR_SCALE and self.current_point
            ):
                self._execute_scale(self.current_point)
                return True
        elif event.key() == Qt.Key_U and event.modifiers() & Qt.ControlModifier:
            # Toggle uniform/non-uniform scaling
            self._toggle_scale_mode()
            return True

        return super().handle_key_press(event)

    def _set_base_point(self, point: QPointF):
        """Set the base point for scaling."""
        self.base_point = point
        self.scale_state = ScaleState.WAITING_FOR_REFERENCE

        # Create base marker
        self._create_base_marker()

        # Emit signal
        self.scale_started.emit(self.base_point)

        logger.debug(f"Scale base point set to ({point.x():.2f}, {point.y():.2f})")

    def _set_reference_point(self, point: QPointF):
        """Set the reference point for scale calculation."""
        if not self.base_point:
            return

        self.reference_point = point

        # Calculate reference distance
        reference_vector = QLineF(self.base_point, self.reference_point)
        self.reference_distance = reference_vector.length()

        if self.reference_distance < 0.001:  # Avoid division by zero
            self.reference_distance = 1.0

        self.scale_state = ScaleState.WAITING_FOR_SCALE
        self.scale_mode = ScaleMode.REFERENCE

        # Create reference line
        self._create_reference_line()

        logger.debug(f"Reference distance set to {self.reference_distance:.2f}")

    def _skip_reference_point(self):
        """Skip reference point and use direct scale factor."""
        self.scale_state = ScaleState.WAITING_FOR_SCALE
        self.scale_mode = ScaleMode.UNIFORM
        self.reference_distance = 1.0

        logger.debug("Using direct scale factor mode")

    def _update_reference_preview(self, current_point: QPointF):
        """Update reference point preview."""
        if not self.base_point:
            return

        self.current_point = current_point

        # Update reference line preview
        if self.reference_line:
            self.reference_line.setLine(
                self.base_point.x(),
                self.base_point.y(),
                current_point.x(),
                current_point.y(),
            )
        else:
            self._create_reference_line()
            self.reference_line.setLine(
                self.base_point.x(),
                self.base_point.y(),
                current_point.x(),
                current_point.y(),
            )

    def _update_scale_preview(self, current_point: QPointF):
        """Update scale preview."""
        if not self.base_point:
            return

        self.current_point = current_point

        # Calculate scale factors
        if self.scale_mode == ScaleMode.REFERENCE and self.reference_point:
            # Scale based on reference distance
            current_vector = QLineF(self.base_point, current_point)
            self.current_distance = current_vector.length()

            if self.reference_distance > 0.001:
                self.scale_factor_x = self.current_distance / self.reference_distance
                self.scale_factor_y = self.scale_factor_x  # Uniform for reference mode
            else:
                self.scale_factor_x = 1.0
                self.scale_factor_y = 1.0
        else:
            # Direct scale factor based on distance from base point
            distance_vector = QLineF(self.base_point, current_point)
            distance = distance_vector.length()

            # Scale factor is proportional to distance (with 100 units = 1.0 scale)
            base_distance = 100.0
            self.scale_factor_x = max(0.01, distance / base_distance)

            if self.scale_mode == ScaleMode.UNIFORM:
                self.scale_factor_y = self.scale_factor_x
            else:
                # Non-uniform scaling - y factor based on angle or separate input
                self.scale_factor_y = self.scale_factor_x

        # Update scale line
        if self.scale_line:
            self.scale_line.setLine(
                self.base_point.x(),
                self.base_point.y(),
                current_point.x(),
                current_point.y(),
            )
        else:
            self._create_scale_line()

        # Update preview items
        self._update_preview_items()

        # Emit signal
        self.scale_preview.emit(
            self.base_point, self.scale_factor_x, self.scale_factor_y
        )

    def _create_base_marker(self):
        """Create the base point marker."""
        if self.base_marker:
            self.scene.removeItem(self.base_marker)

        size = 6
        self.base_marker = QGraphicsEllipseItem(
            self.base_point.x() - size / 2, self.base_point.y() - size / 2, size, size
        )
        self.base_marker.setPen(self.base_pen)
        self.base_marker.setZValue(1000)
        self.scene.addItem(self.base_marker)

    def _create_reference_line(self):
        """Create the reference line."""
        if self.reference_line:
            self.scene.removeItem(self.reference_line)

        self.reference_line = QGraphicsLineItem()
        self.reference_line.setPen(self.reference_pen)
        self.reference_line.setZValue(999)
        self.scene.addItem(self.reference_line)

    def _create_scale_line(self):
        """Create the scale line."""
        if self.scale_line:
            self.scene.removeItem(self.scale_line)

        self.scale_line = QGraphicsLineItem()
        self.scale_line.setPen(self.scale_pen)
        self.scale_line.setZValue(998)
        self.scene.addItem(self.scale_line)

    def _update_preview_items(self):
        """Update preview items showing scaled positions."""
        if not self.base_point or (
            self.scale_factor_x == 1.0 and self.scale_factor_y == 1.0
        ):
            self._clear_preview_items()
            return

        # Remove existing preview items
        self._clear_preview_items()

        # Create scale transform
        transform = QTransform()
        transform.translate(self.base_point.x(), self.base_point.y())
        transform.scale(self.scale_factor_x, self.scale_factor_y)
        transform.translate(-self.base_point.x(), -self.base_point.y())

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
            # Clone the item's geometry with scaling
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

        for item in [self.base_marker, self.reference_line, self.scale_line]:
            if item and item.scene():
                self.scene.removeItem(item)

        self.base_marker = None
        self.reference_line = None
        self.scale_line = None

    def _toggle_scale_mode(self):
        """Toggle between uniform and non-uniform scaling."""
        if self.scale_mode == ScaleMode.UNIFORM:
            self.scale_mode = ScaleMode.NON_UNIFORM
        else:
            self.scale_mode = ScaleMode.UNIFORM

        logger.debug(f"Scale mode changed to {self.scale_mode.name}")

    async def _execute_scale(self, scale_point: QPointF):
        """Execute the scale operation."""
        if not self.base_point or not self.selected_items:
            return

        # Update final scale factors
        self._update_scale_preview(scale_point)

        self.scale_state = ScaleState.SCALING

        try:
            # Clear preview
            self._clear_preview()

            # Create scale command
            from ...core.commands import ScaleCommand

            # Get entity IDs from selected items
            entity_ids = []
            for item in self.selected_items:
                if hasattr(item, "entity_id"):
                    entity_ids.append(item.entity_id)

            if entity_ids:
                # Create and execute scale command
                scale_command = ScaleCommand(
                    self.api_client,
                    entity_ids,
                    self.base_point.x(),
                    self.base_point.y(),
                    self.scale_factor_x,
                    self.scale_factor_y,
                )

                # Execute through command manager for undo support
                success = await self.command_manager.execute_command(scale_command)

                if success:
                    # Emit completion signal
                    self.scale_completed.emit(
                        self.base_point, self.scale_factor_x, self.scale_factor_y
                    )

                    logger.info(
                        f"Scaled {len(entity_ids)} objects by ({self.scale_factor_x:.2f}, {self.scale_factor_y:.2f})"
                    )

                    # Reset tool state
                    self._reset_tool()
                else:
                    logger.error("Scale command execution failed")
                    self._cancel_scale()
            else:
                logger.warning("No valid entities found for scaling")
                self._cancel_scale()

        except Exception as e:
            logger.error(f"Error executing scale: {e}")
            self._cancel_scale()

    def _cancel_scale(self):
        """Cancel the current scale operation."""
        self._clear_preview()

        if self.scale_state != ScaleState.WAITING_FOR_SELECTION:
            self.scale_state = (
                ScaleState.WAITING_FOR_BASE_POINT
                if self.selected_items
                else ScaleState.WAITING_FOR_SELECTION
            )

        self.base_point = None
        self.reference_point = None
        self.current_point = None
        self.reference_distance = 1.0
        self.current_distance = 1.0
        self.scale_factor_x = 1.0
        self.scale_factor_y = 1.0

        # Emit cancellation signal
        self.scale_cancelled.emit()

        logger.debug("Scale operation cancelled")

    def _reset_tool(self):
        """Reset tool to initial state."""
        self.scale_state = ScaleState.WAITING_FOR_SELECTION
        self.base_point = None
        self.reference_point = None
        self.current_point = None
        self.selected_items.clear()
        self.reference_distance = 1.0
        self.current_distance = 1.0
        self.scale_factor_x = 1.0
        self.scale_factor_y = 1.0

        # Clear selection
        self.selection_manager.clear_selection()

    def selection_changed(self, selected_items: List[QGraphicsItem]):
        """Handle selection changes."""
        if self.scale_state == ScaleState.WAITING_FOR_SELECTION and selected_items:
            self.selected_items = selected_items
            self.scale_state = ScaleState.WAITING_FOR_BASE_POINT
            logger.debug(
                f"Scale tool updated with {len(selected_items)} selected items"
            )

    def get_tool_info(self) -> Dict[str, Any]:
        """Get current tool information."""
        return {
            **super().get_tool_info(),
            "scale_state": self.scale_state.name,
            "scale_mode": self.scale_mode.name,
            "base_point": {"x": self.base_point.x(), "y": self.base_point.y()}
            if self.base_point
            else None,
            "scale_factor_x": self.scale_factor_x,
            "scale_factor_y": self.scale_factor_y,
            "reference_distance": self.reference_distance,
            "current_distance": self.current_distance,
            "selected_count": len(self.selected_items),
        }
