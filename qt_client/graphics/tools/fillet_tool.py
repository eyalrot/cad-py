"""
Fillet tool for CAD drawing operations.

This module provides an interactive fillet tool that allows users to create
rounded corners between entities with radius input and real-time preview.
"""

import asyncio
import logging
import math
from enum import Enum, auto
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem

from ...core.selection_manager import SelectionManager
from .base_tool import BaseTool, ToolState

logger = logging.getLogger(__name__)


class FilletState(Enum):
    """States for fillet tool operation."""

    SELECT_FIRST_ENTITY = auto()
    SELECT_SECOND_ENTITY = auto()
    SET_RADIUS = auto()
    FILLETING = auto()
    COMPLETED = auto()


class FilletTool(BaseTool):
    """
    Interactive fillet tool for creating rounded corners.

    Features:
    - Select two entities to fillet between
    - Set fillet radius via point selection or direct input
    - Real-time preview of fillet arc
    - Visual feedback for entity selection
    - Support for line-line fillets
    - Snap integration for precise radius input
    - Undo/redo support through command pattern
    """

    # Signals
    first_entity_selected = Signal(QGraphicsItem)
    second_entity_selected = Signal(QGraphicsItem)
    radius_set = Signal(float)
    fillet_completed = Signal(
        QGraphicsItem, QGraphicsItem, float
    )  # entity1, entity2, radius
    fillet_cancelled = Signal()

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
        self.fillet_state = FilletState.SELECT_FIRST_ENTITY

        # Fillet operation data
        self.first_entity: Optional[QGraphicsItem] = None
        self.second_entity: Optional[QGraphicsItem] = None
        self.fillet_radius = 5.0  # Default radius
        self.reference_point: Optional[QPointF] = None

        # Preview graphics
        self.first_marker: Optional[QGraphicsEllipseItem] = None
        self.second_marker: Optional[QGraphicsEllipseItem] = None
        self.preview_arc: Optional[QGraphicsEllipseItem] = None
        self.radius_line: Optional[QGraphicsLineItem] = None

        # Visual properties
        self.entity_marker_pen = QPen(
            QColor(100, 255, 150, 200)
        )  # Light green for fillet
        self.entity_marker_pen.setWidth(3)

        self.preview_pen = QPen(QColor(100, 255, 150, 180))
        self.preview_pen.setWidth(2)
        self.preview_pen.setStyle(Qt.DashLine)

        self.radius_pen = QPen(QColor(255, 200, 100, 180))
        self.radius_pen.setWidth(1)
        self.radius_pen.setStyle(Qt.DotLine)

        # Settings
        self.show_radius_preview = True
        self.auto_select_from_selection = True

        logger.debug("Fillet tool initialized")

    def get_tool_name(self) -> str:
        """Get tool display name."""
        return "Fillet"

    def get_status_text(self) -> str:
        """Get current status text."""
        if self.fillet_state == FilletState.SELECT_FIRST_ENTITY:
            return "Select first entity for fillet"
        elif self.fillet_state == FilletState.SELECT_SECOND_ENTITY:
            return "Select second entity for fillet"
        elif self.fillet_state == FilletState.SET_RADIUS:
            return f"Set fillet radius (current: {self.fillet_radius:.2f}) - click point or press Enter"
        elif self.fillet_state == FilletState.FILLETING:
            return "Creating fillet..."
        else:
            return "Fillet tool ready"

    def activate(self) -> bool:
        """Activate the fillet tool."""
        if not super().activate():
            return False

        # Check if there are two selected entities
        if self.selection_manager.has_selection() and self.auto_select_from_selection:
            selected_items = self.selection_manager.get_selected_items()
            valid_items = [
                item for item in selected_items if self._is_valid_fillet_entity(item)
            ]

            if len(valid_items) >= 2:
                self._select_first_entity(valid_items[0])
                self._select_second_entity(valid_items[1])
                logger.debug("Fillet tool activated with two selected entities")
            elif len(valid_items) == 1:
                self._select_first_entity(valid_items[0])
                logger.debug("Fillet tool activated with one selected entity")
            else:
                self.fillet_state = FilletState.SELECT_FIRST_ENTITY
                logger.debug("Fillet tool activated, waiting for entity selection")
        else:
            self.fillet_state = FilletState.SELECT_FIRST_ENTITY
            logger.debug("Fillet tool activated, waiting for entity selection")

        return True

    def deactivate(self):
        """Deactivate the fillet tool."""
        self._clear_preview()
        self._clear_markers()
        self.first_entity = None
        self.second_entity = None
        self.reference_point = None
        self.fillet_state = FilletState.SELECT_FIRST_ENTITY

        super().deactivate()
        logger.debug("Fillet tool deactivated")

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        """Handle mouse press events."""
        world_pos = self.scene_pos_from_event(event)

        # Apply snapping
        snap_result = self.snap_engine.snap_point(world_pos, self.view)
        if snap_result.snapped:
            world_pos = snap_result.point

        if self.fillet_state == FilletState.SELECT_FIRST_ENTITY:
            # Find item at click position
            clicked_item = self.scene.itemAt(world_pos, self.view.transform())
            if clicked_item and self._is_valid_fillet_entity(clicked_item):
                self._select_first_entity(clicked_item)
                return True

        elif self.fillet_state == FilletState.SELECT_SECOND_ENTITY:
            # Find item at click position
            clicked_item = self.scene.itemAt(world_pos, self.view.transform())
            if (
                clicked_item
                and self._is_valid_fillet_entity(clicked_item)
                and clicked_item != self.first_entity
            ):
                self._select_second_entity(clicked_item)
                return True

        elif self.fillet_state == FilletState.SET_RADIUS:
            self._set_radius_by_point(world_pos)
            return True

        return False

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        """Handle mouse move events."""
        world_pos = self.scene_pos_from_event(event)

        # Apply snapping
        snap_result = self.snap_engine.snap_point(world_pos, self.view)
        if snap_result.snapped:
            world_pos = snap_result.point

        if self.fillet_state == FilletState.SET_RADIUS and self.show_radius_preview:
            self._update_radius_preview(world_pos)
            return True

        return False

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle key press events."""
        if event.key() == Qt.Key_Escape:
            self._cancel_fillet()
            return True
        elif event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            if self.fillet_state == FilletState.SET_RADIUS:
                self._execute_fillet()
                return True
        elif event.key() == Qt.Key_R and event.modifiers() & Qt.ControlModifier:
            # Toggle radius preview
            self.show_radius_preview = not self.show_radius_preview
            if not self.show_radius_preview:
                self._clear_radius_preview()
            return True
        elif event.key() == Qt.Key_C and event.modifiers() & Qt.ControlModifier:
            # Clear selections
            self._clear_selections()
            return True

        return super().handle_key_press(event)

    def _is_valid_fillet_entity(self, item: QGraphicsItem) -> bool:
        """Check if item can be used for fillet."""
        # Check if item is not a marker or preview item
        if item in [
            self.first_marker,
            self.second_marker,
            self.preview_arc,
            self.radius_line,
        ]:
            return False

        # Check if item has entity_id (is a CAD entity)
        if not hasattr(item, "entity_id"):
            return False

        # For fillet, we typically support lines
        # In a real implementation, check if it's a supported entity type
        return True

    def _select_first_entity(self, entity: QGraphicsItem):
        """Select first entity for fillet."""
        self.first_entity = entity
        self.fillet_state = FilletState.SELECT_SECOND_ENTITY

        # Create marker
        self._create_first_marker()

        # Emit signal
        self.first_entity_selected.emit(entity)

        logger.debug(
            f"Selected first entity for fillet: {getattr(entity, 'entity_id', 'unknown')}"
        )

    def _select_second_entity(self, entity: QGraphicsItem):
        """Select second entity for fillet."""
        self.second_entity = entity
        self.fillet_state = FilletState.SET_RADIUS

        # Create marker
        self._create_second_marker()

        # Emit signal
        self.second_entity_selected.emit(entity)

        logger.debug(
            f"Selected second entity for fillet: {getattr(entity, 'entity_id', 'unknown')}"
        )

    def _create_first_marker(self):
        """Create marker for first entity."""
        if not self.first_entity:
            return

        self._clear_first_marker()

        # Get entity bounds
        bounds = self.first_entity.boundingRect()
        center = bounds.center()

        # Create marker
        marker_size = 8
        self.first_marker = QGraphicsEllipseItem(
            center.x() - marker_size / 2,
            center.y() - marker_size / 2,
            marker_size,
            marker_size,
        )

        self.first_marker.setPen(self.entity_marker_pen)
        self.first_marker.setZValue(1000)

        self.scene.addItem(self.first_marker)

    def _create_second_marker(self):
        """Create marker for second entity."""
        if not self.second_entity:
            return

        self._clear_second_marker()

        # Get entity bounds
        bounds = self.second_entity.boundingRect()
        center = bounds.center()

        # Create marker with square shape to differentiate
        marker_size = 8
        self.second_marker = QGraphicsEllipseItem(
            center.x() - marker_size / 2,
            center.y() - marker_size / 2,
            marker_size,
            marker_size,
        )

        # Use different pen style for second marker
        second_pen = QPen(self.entity_marker_pen)
        second_pen.setStyle(Qt.DashLine)
        self.second_marker.setPen(second_pen)
        self.second_marker.setZValue(1000)

        self.scene.addItem(self.second_marker)

    def _clear_first_marker(self):
        """Clear first entity marker."""
        if self.first_marker and self.first_marker.scene():
            self.scene.removeItem(self.first_marker)
            self.first_marker = None

    def _clear_second_marker(self):
        """Clear second entity marker."""
        if self.second_marker and self.second_marker.scene():
            self.scene.removeItem(self.second_marker)
            self.second_marker = None

    def _clear_markers(self):
        """Clear all entity markers."""
        self._clear_first_marker()
        self._clear_second_marker()

    def _set_radius_by_point(self, point: QPointF):
        """Set fillet radius by clicking a point."""
        if not self.first_entity or not self.second_entity:
            return

        # Calculate radius based on distance from intersection point
        intersection_point = self._estimate_intersection_point()

        if intersection_point:
            distance = (
                (point.x() - intersection_point.x()) ** 2
                + (point.y() - intersection_point.y()) ** 2
            ) ** 0.5

            self.fillet_radius = max(0.1, distance)  # Minimum radius
            self.reference_point = point

            # Clear radius preview
            self._clear_radius_preview()

            # Execute fillet
            asyncio.create_task(self._execute_fillet())

            # Emit signal
            self.radius_set.emit(self.fillet_radius)

            logger.debug(f"Fillet radius set to: {self.fillet_radius:.2f}")

    def _estimate_intersection_point(self) -> Optional[QPointF]:
        """Estimate intersection point between two entities."""
        if not self.first_entity or not self.second_entity:
            return None

        # Simplified intersection estimation using bounding rect centers
        bounds1 = self.first_entity.boundingRect()
        bounds2 = self.second_entity.boundingRect()

        center1 = bounds1.center()
        center2 = bounds2.center()

        # Return midpoint as rough estimate
        return QPointF((center1.x() + center2.x()) / 2, (center1.y() + center2.y()) / 2)

    def _update_radius_preview(self, current_point: QPointF):
        """Update radius preview."""
        if not self.first_entity or not self.second_entity:
            return

        # Clear existing preview
        self._clear_radius_preview()

        # Calculate current radius
        intersection_point = self._estimate_intersection_point()

        if intersection_point:
            current_radius = (
                (current_point.x() - intersection_point.x()) ** 2
                + (current_point.y() - intersection_point.y()) ** 2
            ) ** 0.5

            # Create radius line
            self.radius_line = QGraphicsLineItem(
                intersection_point.x(),
                intersection_point.y(),
                current_point.x(),
                current_point.y(),
            )
            self.radius_line.setPen(self.radius_pen)
            self.radius_line.setZValue(999)

            self.scene.addItem(self.radius_line)

            # Create fillet preview
            self._create_fillet_preview(intersection_point, current_radius)

            # Update current radius for display
            self.fillet_radius = max(0.1, current_radius)

    def _create_fillet_preview(self, center: QPointF, radius: float):
        """Create preview of fillet arc."""
        if radius <= 0:
            return

        try:
            # Create preview arc (simplified - just a circle section)
            arc_size = radius * 2

            self.preview_arc = QGraphicsEllipseItem(
                center.x() - radius, center.y() - radius, arc_size, arc_size
            )

            self.preview_arc.setPen(self.preview_pen)
            self.preview_arc.setZValue(998)

            # Set span angle for arc preview (90 degrees)
            self.preview_arc.setStartAngle(0 * 16)  # Qt angles are in 1/16th degrees
            self.preview_arc.setSpanAngle(90 * 16)

            self.scene.addItem(self.preview_arc)

        except Exception as e:
            logger.warning(f"Error creating fillet preview: {e}")

    def _clear_radius_preview(self):
        """Clear radius preview."""
        if self.radius_line and self.radius_line.scene():
            self.scene.removeItem(self.radius_line)
            self.radius_line = None

        if self.preview_arc and self.preview_arc.scene():
            self.scene.removeItem(self.preview_arc)
            self.preview_arc = None

    def _clear_preview(self):
        """Clear all preview graphics."""
        self._clear_radius_preview()

    async def _execute_fillet(self):
        """Execute the fillet operation."""
        if not self.first_entity or not self.second_entity:
            return

        self.fillet_state = FilletState.FILLETING

        try:
            # Clear preview
            self._clear_preview()

            # Create fillet command
            from ...core.commands import FilletCommand

            # Get entity IDs
            entity1_id = getattr(self.first_entity, "entity_id", None)
            entity2_id = getattr(self.second_entity, "entity_id", None)

            if not entity1_id or not entity2_id:
                logger.error("Invalid entity IDs for fillet operation")
                self._reset_tool()
                return

            # Create and execute fillet command
            fillet_command = FilletCommand(
                self.api_client, entity1_id, entity2_id, self.fillet_radius
            )

            # Execute through command manager for undo support
            success = await self.command_manager.execute_command(fillet_command)

            if success:
                # Emit completion signal
                self.fillet_completed.emit(
                    self.first_entity, self.second_entity, self.fillet_radius
                )

                logger.info(
                    f"Created fillet between {entity1_id} and {entity2_id} with radius {self.fillet_radius:.2f}"
                )

                # Reset for next operation
                self._reset_tool()
            else:
                logger.error("Fillet command execution failed")
                self._reset_tool()

        except Exception as e:
            logger.error(f"Error executing fillet: {e}")
            self._reset_tool()

    def _cancel_fillet(self):
        """Cancel the current fillet operation."""
        self._clear_preview()
        self._clear_markers()
        self._reset_tool()

        # Emit cancellation signal
        self.fillet_cancelled.emit()

        logger.debug("Fillet operation cancelled")

    def _clear_selections(self):
        """Clear entity selections."""
        self._clear_markers()
        self.first_entity = None
        self.second_entity = None
        self.fillet_state = FilletState.SELECT_FIRST_ENTITY

        logger.debug("Fillet selections cleared")

    def _reset_tool(self):
        """Reset tool to initial state."""
        self.fillet_state = FilletState.SELECT_FIRST_ENTITY
        self.first_entity = None
        self.second_entity = None
        self.reference_point = None
        self._clear_markers()

    def set_fillet_radius(self, radius: float):
        """Set fillet radius directly."""
        self.fillet_radius = max(0.1, radius)

        if self.fillet_state == FilletState.SET_RADIUS:
            asyncio.create_task(self._execute_fillet())

        logger.debug(f"Fillet radius set to: {self.fillet_radius:.2f}")

    def set_show_radius_preview(self, show_preview: bool):
        """Set whether to show radius preview."""
        self.show_radius_preview = show_preview
        if not show_preview:
            self._clear_radius_preview()

    def set_auto_select_from_selection(self, auto_select: bool):
        """Set whether to auto-select from current selection."""
        self.auto_select_from_selection = auto_select

    def selection_changed(self, selected_items: List[QGraphicsItem]):
        """Handle selection changes."""
        if not self.auto_select_from_selection:
            return

        valid_items = [
            item for item in selected_items if self._is_valid_fillet_entity(item)
        ]

        if (
            self.fillet_state == FilletState.SELECT_FIRST_ENTITY
            and len(valid_items) >= 1
        ):
            self._select_first_entity(valid_items[0])
            if len(valid_items) >= 2:
                self._select_second_entity(valid_items[1])
        elif (
            self.fillet_state == FilletState.SELECT_SECOND_ENTITY
            and len(valid_items) >= 1
        ):
            # Find item that's not the first entity
            for item in valid_items:
                if item != self.first_entity:
                    self._select_second_entity(item)
                    break

    def get_tool_info(self) -> Dict[str, Any]:
        """Get current tool information."""
        return {
            **super().get_tool_info(),
            "fillet_state": self.fillet_state.name,
            "first_entity": getattr(self.first_entity, "entity_id", None)
            if self.first_entity
            else None,
            "second_entity": getattr(self.second_entity, "entity_id", None)
            if self.second_entity
            else None,
            "fillet_radius": self.fillet_radius,
            "reference_point": {
                "x": self.reference_point.x(),
                "y": self.reference_point.y(),
            }
            if self.reference_point
            else None,
            "show_radius_preview": self.show_radius_preview,
            "auto_select_from_selection": self.auto_select_from_selection,
        }
