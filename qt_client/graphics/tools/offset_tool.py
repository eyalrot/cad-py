"""
Offset tool for CAD drawing operations.

This module provides an interactive offset tool that allows users to create
parallel curves at a specified distance with side selection and real-time preview.
"""

import asyncio
import logging
from enum import Enum, auto
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsLineItem

from ...core.selection_manager import SelectionManager
from .base_tool import BaseTool, ToolState

logger = logging.getLogger(__name__)


class OffsetState(Enum):
    """States for offset tool operation."""

    SELECT_ENTITY = auto()
    SET_DISTANCE = auto()
    SELECT_SIDE = auto()
    OFFSETTING = auto()
    COMPLETED = auto()


class OffsetTool(BaseTool):
    """
    Interactive offset tool for creating parallel curves.

    Features:
    - Select entity to offset
    - Input distance via point selection or direct input
    - Visual side selection with preview
    - Real-time preview of offset curve
    - Support for lines, arcs, and circles
    - Snap integration for precise distance input
    - Undo/redo support through command pattern
    """

    # Signals
    entity_selected = Signal(QGraphicsItem)
    distance_set = Signal(float)
    side_selected = Signal(QPointF)
    offset_completed = Signal(QGraphicsItem, float, QPointF)  # entity, distance, side
    offset_cancelled = Signal()

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
        self.offset_state = OffsetState.SELECT_ENTITY

        # Offset operation data
        self.selected_entity: Optional[QGraphicsItem] = None
        self.offset_distance = 10.0  # Default distance
        self.reference_point: Optional[QPointF] = None
        self.side_point: Optional[QPointF] = None

        # Preview graphics
        self.preview_line: Optional[QGraphicsLineItem] = []
        self.reference_line: Optional[QGraphicsLineItem] = None

        # Visual properties
        self.preview_pen = QPen(QColor(255, 200, 0, 180))  # Orange for offset
        self.preview_pen.setWidth(2)
        self.preview_pen.setStyle(Qt.DashLine)

        self.reference_pen = QPen(QColor(100, 200, 255, 180))
        self.reference_pen.setWidth(1)
        self.reference_pen.setStyle(Qt.DotLine)

        self.distance_pen = QPen(QColor(255, 100, 100, 200))
        self.distance_pen.setWidth(2)

        # Settings
        self.show_distance_preview = True
        self.auto_confirm_side = False  # Auto-confirm when distance is set by point

        logger.debug("Offset tool initialized")

    def get_tool_name(self) -> str:
        """Get tool display name."""
        return "Offset"

    def get_status_text(self) -> str:
        """Get current status text."""
        if self.offset_state == OffsetState.SELECT_ENTITY:
            return "Select entity to offset"
        elif self.offset_state == OffsetState.SET_DISTANCE:
            return f"Set offset distance (current: {self.offset_distance:.2f}) - click point or press Enter"
        elif self.offset_state == OffsetState.SELECT_SIDE:
            return f"Select side for offset (distance: {self.offset_distance:.2f})"
        elif self.offset_state == OffsetState.OFFSETTING:
            return "Creating offset curve..."
        else:
            return "Offset tool ready"

    def activate(self) -> bool:
        """Activate the offset tool."""
        if not super().activate():
            return False

        # Check if there's a selected entity to offset
        if self.selection_manager.has_selection():
            selected_items = self.selection_manager.get_selected_items()
            if len(selected_items) == 1:
                self.selected_entity = selected_items[0]
                self.offset_state = OffsetState.SET_DISTANCE
                logger.debug(
                    f"Offset tool activated with selected entity: {getattr(self.selected_entity, 'entity_id', 'unknown')}"
                )
            else:
                self.offset_state = OffsetState.SELECT_ENTITY
                logger.debug("Offset tool activated, multiple entities selected")
        else:
            self.offset_state = OffsetState.SELECT_ENTITY
            logger.debug("Offset tool activated, waiting for entity selection")

        return True

    def deactivate(self):
        """Deactivate the offset tool."""
        self._clear_preview()
        self.selected_entity = None
        self.reference_point = None
        self.side_point = None
        self.offset_state = OffsetState.SELECT_ENTITY

        super().deactivate()
        logger.debug("Offset tool deactivated")

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        """Handle mouse press events."""
        world_pos = self.scene_pos_from_event(event)

        # Apply snapping
        snap_result = self.snap_engine.snap_point(world_pos, self.view)
        if snap_result.snapped:
            world_pos = snap_result.point

        if self.offset_state == OffsetState.SELECT_ENTITY:
            # Find item at click position
            clicked_item = self.scene.itemAt(world_pos, self.view.transform())
            if clicked_item and self._is_valid_offset_entity(clicked_item):
                self._select_entity(clicked_item)
                return True

        elif self.offset_state == OffsetState.SET_DISTANCE:
            if self.selected_entity:
                self._set_distance_by_point(world_pos)
                return True

        elif self.offset_state == OffsetState.SELECT_SIDE:
            self._select_side(world_pos)
            return True

        return False

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        """Handle mouse move events."""
        world_pos = self.scene_pos_from_event(event)

        # Apply snapping
        snap_result = self.snap_engine.snap_point(world_pos, self.view)
        if snap_result.snapped:
            world_pos = snap_result.point

        if self.offset_state == OffsetState.SET_DISTANCE and self.show_distance_preview:
            self._update_distance_preview(world_pos)
            return True
        elif self.offset_state == OffsetState.SELECT_SIDE:
            self._update_side_preview(world_pos)
            return True

        return False

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle key press events."""
        if event.key() == Qt.Key_Escape:
            self._cancel_offset()
            return True
        elif event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            if self.offset_state == OffsetState.SET_DISTANCE:
                self._confirm_distance()
                return True
            elif self.offset_state == OffsetState.SELECT_SIDE:
                # Use last mouse position as side point
                if self.side_point:
                    self._execute_offset()
                return True
        elif event.key() == Qt.Key_D and event.modifiers() & Qt.ControlModifier:
            # Toggle distance preview
            self.show_distance_preview = not self.show_distance_preview
            if not self.show_distance_preview:
                self._clear_distance_preview()
            return True

        return super().handle_key_press(event)

    def _is_valid_offset_entity(self, item: QGraphicsItem) -> bool:
        """Check if item can be offset."""
        # Check if item is not a preview item
        if item in [self.preview_line, self.reference_line]:
            return False

        # Check if item has entity_id (is a CAD entity)
        if not hasattr(item, "entity_id"):
            return False

        # In a real implementation, check if entity type supports offset
        # (lines, arcs, circles, etc.)
        return True

    def _select_entity(self, entity: QGraphicsItem):
        """Select entity for offset operation."""
        self.selected_entity = entity
        self.offset_state = OffsetState.SET_DISTANCE

        # Clear selection to avoid confusion
        self.selection_manager.clear_selection()

        # Emit signal
        self.entity_selected.emit(entity)

        logger.debug(
            f"Selected entity for offset: {getattr(entity, 'entity_id', 'unknown')}"
        )

    def _set_distance_by_point(self, point: QPointF):
        """Set offset distance by clicking a point."""
        if not self.selected_entity:
            return

        # Calculate distance from entity to point
        entity_bounds = self.selected_entity.boundingRect()
        entity_center = entity_bounds.center()

        # For now, use distance from entity center
        # In a real implementation, calculate perpendicular distance to entity
        distance = (
            (point.x() - entity_center.x()) ** 2 + (point.y() - entity_center.y()) ** 2
        ) ** 0.5

        self.offset_distance = max(0.1, distance)  # Minimum distance
        self.reference_point = point

        # Clear distance preview
        self._clear_distance_preview()

        # Move to side selection
        if self.auto_confirm_side:
            self.side_point = point
            self._execute_offset()
        else:
            self.offset_state = OffsetState.SELECT_SIDE

        # Emit signal
        self.distance_set.emit(self.offset_distance)

        logger.debug(f"Offset distance set to: {self.offset_distance:.2f}")

    def _confirm_distance(self):
        """Confirm current distance and move to side selection."""
        if self.selected_entity:
            self.offset_state = OffsetState.SELECT_SIDE
            self._clear_distance_preview()

            logger.debug(f"Confirmed offset distance: {self.offset_distance:.2f}")

    def _select_side(self, point: QPointF):
        """Select side for offset."""
        self.side_point = point

        # Execute offset
        asyncio.create_task(self._execute_offset())

        # Emit signal
        self.side_selected.emit(point)

        logger.debug(f"Selected offset side at: ({point.x():.2f}, {point.y():.2f})")

    def _update_distance_preview(self, current_point: QPointF):
        """Update distance preview."""
        if not self.selected_entity:
            return

        # Clear existing preview
        self._clear_distance_preview()

        # Calculate current distance
        entity_bounds = self.selected_entity.boundingRect()
        entity_center = entity_bounds.center()

        current_distance = (
            (current_point.x() - entity_center.x()) ** 2
            + (current_point.y() - entity_center.y()) ** 2
        ) ** 0.5

        # Create reference line showing distance
        self.reference_line = QGraphicsLineItem(
            entity_center.x(), entity_center.y(), current_point.x(), current_point.y()
        )
        self.reference_line.setPen(self.reference_pen)
        self.reference_line.setZValue(999)

        self.scene.addItem(self.reference_line)

        # Update current distance for display
        self.offset_distance = max(0.1, current_distance)

    def _update_side_preview(self, current_point: QPointF):
        """Update offset side preview."""
        if not self.selected_entity:
            return

        # Clear existing preview
        self._clear_preview()

        # Create preview of offset entity
        self._create_offset_preview(current_point)

    def _create_offset_preview(self, side_point: QPointF):
        """Create preview of offset entity."""
        if not self.selected_entity:
            return

        try:
            # This is a simplified preview - in reality, would use geometry operations
            entity_bounds = self.selected_entity.boundingRect()

            # Calculate offset direction based on side point
            entity_center = entity_bounds.center()
            to_side = QPointF(
                side_point.x() - entity_center.x(), side_point.y() - entity_center.y()
            )

            # Normalize direction
            length = (to_side.x() ** 2 + to_side.y() ** 2) ** 0.5
            if length > 0:
                to_side = QPointF(to_side.x() / length, to_side.y() / length)

            # Create offset preview based on entity type
            if hasattr(self.selected_entity, "line"):
                # Line entity
                line = self.selected_entity.line()

                # Calculate perpendicular offset
                line_dir = QPointF(line.dx(), line.dy())
                line_length = (line_dir.x() ** 2 + line_dir.y() ** 2) ** 0.5

                if line_length > 0:
                    line_dir = QPointF(
                        line_dir.x() / line_length, line_dir.y() / line_length
                    )
                    perpendicular = QPointF(-line_dir.y(), line_dir.x())

                    # Determine offset side
                    side_factor = (
                        1
                        if (
                            perpendicular.x() * to_side.x()
                            + perpendicular.y() * to_side.y()
                        )
                        > 0
                        else -1
                    )

                    offset_vector = QPointF(
                        perpendicular.x() * self.offset_distance * side_factor,
                        perpendicular.y() * self.offset_distance * side_factor,
                    )

                    # Create offset line
                    offset_start = QPointF(
                        line.p1().x() + offset_vector.x(),
                        line.p1().y() + offset_vector.y(),
                    )
                    offset_end = QPointF(
                        line.p2().x() + offset_vector.x(),
                        line.p2().y() + offset_vector.y(),
                    )

                    self.preview_line = QGraphicsLineItem(
                        offset_start.x(),
                        offset_start.y(),
                        offset_end.x(),
                        offset_end.y(),
                    )
                    self.preview_line.setPen(self.preview_pen)
                    self.preview_line.setZValue(998)

                    self.scene.addItem(self.preview_line)

            else:
                # Generic entity - create a rough preview
                offset_center = QPointF(
                    entity_center.x() + to_side.x() * self.offset_distance,
                    entity_center.y() + to_side.y() * self.offset_distance,
                )

                # Create a simple line indicating offset direction
                self.preview_line = QGraphicsLineItem(
                    entity_center.x(),
                    entity_center.y(),
                    offset_center.x(),
                    offset_center.y(),
                )
                self.preview_line.setPen(self.preview_pen)
                self.preview_line.setZValue(998)

                self.scene.addItem(self.preview_line)

        except Exception as e:
            logger.warning(f"Error creating offset preview: {e}")

    def _clear_distance_preview(self):
        """Clear distance preview."""
        if self.reference_line and self.reference_line.scene():
            self.scene.removeItem(self.reference_line)
            self.reference_line = None

    def _clear_preview(self):
        """Clear all preview graphics."""
        self._clear_distance_preview()

        if self.preview_line and self.preview_line.scene():
            self.scene.removeItem(self.preview_line)
            self.preview_line = None

    async def _execute_offset(self):
        """Execute the offset operation."""
        if not self.selected_entity or not self.side_point:
            return

        self.offset_state = OffsetState.OFFSETTING

        try:
            # Clear preview
            self._clear_preview()

            # Create offset command
            from ...core.commands import OffsetCommand

            # Get entity ID
            entity_id = getattr(self.selected_entity, "entity_id", None)

            if not entity_id:
                logger.error("Invalid entity ID for offset operation")
                self._reset_tool()
                return

            # Create and execute offset command
            offset_command = OffsetCommand(
                self.api_client,
                entity_id,
                self.offset_distance,
                self.side_point.x(),
                self.side_point.y(),
            )

            # Execute through command manager for undo support
            success = await self.command_manager.execute_command(offset_command)

            if success:
                # Emit completion signal
                self.offset_completed.emit(
                    self.selected_entity, self.offset_distance, self.side_point
                )

                logger.info(
                    f"Offset entity {entity_id} by distance {self.offset_distance:.2f}"
                )

                # Reset for next operation
                self._reset_tool()
            else:
                logger.error("Offset command execution failed")
                self._reset_tool()

        except Exception as e:
            logger.error(f"Error executing offset: {e}")
            self._reset_tool()

    def _cancel_offset(self):
        """Cancel the current offset operation."""
        self._clear_preview()
        self._reset_tool()

        # Emit cancellation signal
        self.offset_cancelled.emit()

        logger.debug("Offset operation cancelled")

    def _reset_tool(self):
        """Reset tool to initial state."""
        self.offset_state = OffsetState.SELECT_ENTITY
        self.selected_entity = None
        self.reference_point = None
        self.side_point = None

    def set_offset_distance(self, distance: float):
        """Set offset distance directly."""
        self.offset_distance = max(0.1, distance)

        if self.offset_state == OffsetState.SET_DISTANCE:
            self._confirm_distance()

        logger.debug(f"Offset distance set to: {self.offset_distance:.2f}")

    def set_show_distance_preview(self, show_preview: bool):
        """Set whether to show distance preview."""
        self.show_distance_preview = show_preview
        if not show_preview:
            self._clear_distance_preview()

    def set_auto_confirm_side(self, auto_confirm: bool):
        """Set whether to auto-confirm side when distance is set by point."""
        self.auto_confirm_side = auto_confirm

    def selection_changed(self, selected_items: List[QGraphicsItem]):
        """Handle selection changes."""
        if self.offset_state == OffsetState.SELECT_ENTITY and len(selected_items) == 1:
            if self._is_valid_offset_entity(selected_items[0]):
                self._select_entity(selected_items[0])

    def get_tool_info(self) -> Dict[str, Any]:
        """Get current tool information."""
        return {
            **super().get_tool_info(),
            "offset_state": self.offset_state.name,
            "selected_entity": getattr(self.selected_entity, "entity_id", None)
            if self.selected_entity
            else None,
            "offset_distance": self.offset_distance,
            "reference_point": {
                "x": self.reference_point.x(),
                "y": self.reference_point.y(),
            }
            if self.reference_point
            else None,
            "side_point": {"x": self.side_point.x(), "y": self.side_point.y()}
            if self.side_point
            else None,
            "show_distance_preview": self.show_distance_preview,
            "auto_confirm_side": self.auto_confirm_side,
        }
