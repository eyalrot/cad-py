"""
Extend tool for CAD drawing operations.

This module provides an interactive extend tool that allows users to extend
entities to boundaries with precise control and visual feedback.
"""

import asyncio
import logging
from enum import Enum, auto
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem

from ...core.selection_manager import SelectionManager
from .base_tool import BaseTool, ToolState

logger = logging.getLogger(__name__)


class ExtendState(Enum):
    """States for extend tool operation."""

    SELECT_BOUNDARY = auto()
    SELECT_ENTITY_TO_EXTEND = auto()
    EXTENDING = auto()
    COMPLETED = auto()


class ExtendTool(BaseTool):
    """
    Interactive extend tool for extending entities to boundaries.

    Features:
    - Select boundary entities for extension
    - Click entities to extend them to nearest boundary
    - Visual feedback for boundary selection and extension preview
    - Support for multiple boundary entities
    - Snap integration for precise selection
    - Undo/redo support through command pattern
    """

    # Signals
    boundary_selected = Signal(QGraphicsItem)
    entity_extended = Signal(QGraphicsItem, QGraphicsItem)  # entity, boundary
    extend_completed = Signal()
    extend_cancelled = Signal()

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
        self.extend_state = ExtendState.SELECT_BOUNDARY

        # Extend operation data
        self.boundary_entities: List[QGraphicsItem] = []
        self.boundary_markers: List[QGraphicsEllipseItem] = []
        self.preview_line: Optional[QGraphicsLineItem] = None

        # Visual properties
        self.boundary_marker_pen = QPen(QColor(100, 255, 100, 200))  # Green for extend
        self.boundary_marker_pen.setWidth(3)

        self.preview_pen = QPen(QColor(100, 255, 100, 180))
        self.preview_pen.setWidth(2)
        self.preview_pen.setStyle(Qt.DashLine)

        self.extend_feedback_pen = QPen(QColor(150, 255, 150, 180))
        self.extend_feedback_pen.setWidth(1)
        self.extend_feedback_pen.setStyle(Qt.DotLine)

        # Settings
        self.auto_select_boundaries = (
            False  # If True, use selected entities as boundaries
        )
        self.show_extension_preview = True  # Show preview of extension

        logger.debug("Extend tool initialized")

    def get_tool_name(self) -> str:
        """Get tool display name."""
        return "Extend"

    def get_status_text(self) -> str:
        """Get current status text."""
        if self.extend_state == ExtendState.SELECT_BOUNDARY:
            boundary_count = len(self.boundary_entities)
            if boundary_count == 0:
                return (
                    "Select boundary entities (or press Enter to use selected entities)"
                )
            else:
                return f"Select boundary entities ({boundary_count} selected) or press Enter to start extending"
        elif self.extend_state == ExtendState.SELECT_ENTITY_TO_EXTEND:
            return f"Click entities to extend to boundaries ({len(self.boundary_entities)} boundaries active)"
        elif self.extend_state == ExtendState.EXTENDING:
            return "Extending entity..."
        else:
            return "Extend tool ready"

    def activate(self) -> bool:
        """Activate the extend tool."""
        if not super().activate():
            return False

        # Check if there are selected entities to use as boundaries
        if self.selection_manager.has_selection() and self.auto_select_boundaries:
            self.boundary_entities = list(self.selection_manager.get_selected_items())
            self._create_boundary_markers()
            self.extend_state = ExtendState.SELECT_ENTITY_TO_EXTEND
            logger.debug(
                f"Extend tool activated with {len(self.boundary_entities)} boundary entities from selection"
            )
        else:
            self.extend_state = ExtendState.SELECT_BOUNDARY
            logger.debug("Extend tool activated, waiting for boundary selection")

        return True

    def deactivate(self):
        """Deactivate the extend tool."""
        self._clear_boundary_markers()
        self._clear_preview()
        self.boundary_entities.clear()
        self.extend_state = ExtendState.SELECT_BOUNDARY

        super().deactivate()
        logger.debug("Extend tool deactivated")

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        """Handle mouse press events."""
        world_pos = self.scene_pos_from_event(event)

        # Find item at click position
        clicked_item = self.scene.itemAt(world_pos, self.view.transform())

        if self.extend_state == ExtendState.SELECT_BOUNDARY:
            if clicked_item and self._is_valid_boundary(clicked_item):
                self._add_boundary_entity(clicked_item)
                return True

        elif self.extend_state == ExtendState.SELECT_ENTITY_TO_EXTEND:
            if clicked_item and self._is_valid_extend_entity(clicked_item):
                asyncio.create_task(self._extend_entity(clicked_item, world_pos))
                return True

        return False

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        """Handle mouse move events."""
        if (
            self.extend_state != ExtendState.SELECT_ENTITY_TO_EXTEND
            or not self.show_extension_preview
        ):
            return False

        world_pos = self.scene_pos_from_event(event)

        # Find item under cursor
        item_under_cursor = self.scene.itemAt(world_pos, self.view.transform())

        if item_under_cursor and self._is_valid_extend_entity(item_under_cursor):
            self._update_extension_preview(item_under_cursor)
        else:
            self._clear_preview()

        return True

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle key press events."""
        if event.key() == Qt.Key_Escape:
            self._cancel_extend()
            return True
        elif event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            if self.extend_state == ExtendState.SELECT_BOUNDARY:
                if self.boundary_entities:
                    self._start_extending()
                elif self.selection_manager.has_selection():
                    # Use selected entities as boundaries
                    self.boundary_entities = list(
                        self.selection_manager.get_selected_items()
                    )
                    self._create_boundary_markers()
                    self._start_extending()
                return True
        elif event.key() == Qt.Key_C and event.modifiers() & Qt.ControlModifier:
            # Clear boundaries
            self._clear_boundaries()
            return True
        elif event.key() == Qt.Key_P and event.modifiers() & Qt.ControlModifier:
            # Toggle preview
            self.show_extension_preview = not self.show_extension_preview
            if not self.show_extension_preview:
                self._clear_preview()
            return True

        return super().handle_key_press(event)

    def _is_valid_boundary(self, item: QGraphicsItem) -> bool:
        """Check if item can be used as a boundary."""
        # Check if item is not already a boundary marker
        if item in self.boundary_markers:
            return False

        # Check if item is not a preview item
        if item == self.preview_line:
            return False

        # Check if item has entity_id (is a CAD entity)
        if not hasattr(item, "entity_id"):
            return False

        # Check if already selected as boundary
        if item in self.boundary_entities:
            return False

        return True

    def _is_valid_extend_entity(self, item: QGraphicsItem) -> bool:
        """Check if item can be extended."""
        # Check if item is not a boundary marker
        if item in self.boundary_markers:
            return False

        # Check if item is not a preview item
        if item == self.preview_line:
            return False

        # Check if item has entity_id (is a CAD entity)
        if not hasattr(item, "entity_id"):
            return False

        # Check if item is not a boundary entity
        if item in self.boundary_entities:
            return False

        # For extend, we typically only support lines
        # In a real implementation, check if it's a line entity
        return True

    def _add_boundary_entity(self, entity: QGraphicsItem):
        """Add entity as a boundary."""
        if entity not in self.boundary_entities:
            self.boundary_entities.append(entity)
            self._create_boundary_marker(entity)

            # Emit signal
            self.boundary_selected.emit(entity)

            logger.debug(
                f"Added boundary entity: {getattr(entity, 'entity_id', 'unknown')}"
            )

    def _create_boundary_marker(self, entity: QGraphicsItem):
        """Create visual marker for boundary entity."""
        # Get entity center point for marker placement
        bounds = entity.boundingRect()
        center = bounds.center()

        # Create marker with square shape for extend (different from trim)
        marker_size = 8
        marker = QGraphicsEllipseItem(
            center.x() - marker_size / 2,
            center.y() - marker_size / 2,
            marker_size,
            marker_size,
        )

        marker.setPen(self.boundary_marker_pen)
        marker.setZValue(1000)  # Draw on top

        self.scene.addItem(marker)
        self.boundary_markers.append(marker)

    def _create_boundary_markers(self):
        """Create markers for all boundary entities."""
        self._clear_boundary_markers()
        for entity in self.boundary_entities:
            self._create_boundary_marker(entity)

    def _clear_boundary_markers(self):
        """Clear all boundary markers."""
        for marker in self.boundary_markers:
            if marker.scene():
                self.scene.removeItem(marker)
        self.boundary_markers.clear()

    def _clear_boundaries(self):
        """Clear all boundary entities."""
        self._clear_boundary_markers()
        self.boundary_entities.clear()

        if self.extend_state == ExtendState.SELECT_ENTITY_TO_EXTEND:
            self.extend_state = ExtendState.SELECT_BOUNDARY

        logger.debug("Boundary entities cleared")

    def _start_extending(self):
        """Start the extending phase."""
        if self.boundary_entities:
            self.extend_state = ExtendState.SELECT_ENTITY_TO_EXTEND
            logger.debug(
                f"Started extending with {len(self.boundary_entities)} boundaries"
            )
        else:
            logger.warning("Cannot start extending without boundary entities")

    def _update_extension_preview(self, entity: QGraphicsItem):
        """Update extension preview for entity."""
        try:
            # Clear existing preview
            self._clear_preview()

            # Find potential extension
            extension_info = self._calculate_extension_preview(entity)

            if extension_info:
                start_point, end_point = extension_info

                # Create preview line
                self.preview_line = QGraphicsLineItem(
                    start_point.x(), start_point.y(), end_point.x(), end_point.y()
                )
                self.preview_line.setPen(self.preview_pen)
                self.preview_line.setZValue(999)

                self.scene.addItem(self.preview_line)

        except Exception as e:
            logger.warning(f"Error updating extension preview: {e}")

    def _calculate_extension_preview(self, entity: QGraphicsItem) -> Optional[tuple]:
        """Calculate extension preview points."""
        # This is a simplified preview calculation
        # In a real implementation, this would use geometric calculations
        # to find the intersection with boundary entities

        if not self.boundary_entities:
            return None

        # Get entity bounds
        entity_bounds = entity.boundingRect()

        # For demonstration, extend towards the nearest boundary
        # In reality, this would calculate the actual extension based on
        # the entity's geometry and boundary intersections

        nearest_boundary = self._find_nearest_boundary(entity)
        if not nearest_boundary:
            return None

        boundary_bounds = nearest_boundary.boundingRect()

        # Calculate extension direction (simplified)
        entity_center = entity_bounds.center()
        boundary_center = boundary_bounds.center()

        # Extend from entity towards boundary
        start_point = QPointF(entity_center.x(), entity_center.y())
        end_point = QPointF(boundary_center.x(), boundary_center.y())

        return start_point, end_point

    def _find_nearest_boundary(self, entity: QGraphicsItem) -> Optional[QGraphicsItem]:
        """Find the nearest boundary entity."""
        if not self.boundary_entities:
            return None

        entity_bounds = entity.boundingRect()
        entity_center = entity_bounds.center()

        nearest_boundary = None
        min_distance = float("inf")

        for boundary in self.boundary_entities:
            boundary_bounds = boundary.boundingRect()
            boundary_center = boundary_bounds.center()

            distance = (
                (entity_center.x() - boundary_center.x()) ** 2
                + (entity_center.y() - boundary_center.y()) ** 2
            ) ** 0.5

            if distance < min_distance:
                min_distance = distance
                nearest_boundary = boundary

        return nearest_boundary

    def _clear_preview(self):
        """Clear extension preview."""
        if self.preview_line and self.preview_line.scene():
            self.scene.removeItem(self.preview_line)
            self.preview_line = None

    async def _extend_entity(self, entity: QGraphicsItem, click_point: QPointF):
        """Extend entity to nearest boundary."""
        if not self.boundary_entities:
            logger.warning("No boundary entities for extending")
            return

        self.extend_state = ExtendState.EXTENDING

        try:
            # Find the best boundary for extension
            best_boundary = self._find_best_boundary(entity, click_point)

            if not best_boundary:
                logger.warning("No suitable boundary found for extension")
                self.extend_state = ExtendState.SELECT_ENTITY_TO_EXTEND
                return

            # Clear preview
            self._clear_preview()

            # Create extend command
            from ...core.commands import ExtendCommand

            # Get entity IDs
            entity_id = getattr(entity, "entity_id", None)
            boundary_id = getattr(best_boundary, "entity_id", None)

            if not entity_id or not boundary_id:
                logger.error("Invalid entity IDs for extend operation")
                self.extend_state = ExtendState.SELECT_ENTITY_TO_EXTEND
                return

            # Create and execute extend command
            extend_command = ExtendCommand(self.api_client, entity_id, boundary_id)

            # Execute through command manager for undo support
            success = await self.command_manager.execute_command(extend_command)

            if success:
                # Emit signals
                self.entity_extended.emit(entity, best_boundary)

                logger.info(f"Extended entity {entity_id} to boundary {boundary_id}")
            else:
                logger.error("Extend command execution failed")

            # Return to extending state
            self.extend_state = ExtendState.SELECT_ENTITY_TO_EXTEND

        except Exception as e:
            logger.error(f"Error extending entity: {e}")
            self.extend_state = ExtendState.SELECT_ENTITY_TO_EXTEND

    def _find_best_boundary(
        self, entity: QGraphicsItem, click_point: QPointF
    ) -> Optional[QGraphicsItem]:
        """Find the best boundary entity for extension."""
        if not self.boundary_entities:
            return None

        # For now, find the closest boundary entity
        # In a real implementation, this would find the boundary that creates
        # the most sensible extension based on geometric analysis

        best_boundary = None
        min_distance = float("inf")

        for boundary in self.boundary_entities:
            # Calculate distance from click point to boundary
            boundary_bounds = boundary.boundingRect()
            boundary_center = boundary_bounds.center()

            distance = (
                (click_point.x() - boundary_center.x()) ** 2
                + (click_point.y() - boundary_center.y()) ** 2
            ) ** 0.5

            if distance < min_distance:
                min_distance = distance
                best_boundary = boundary

        return best_boundary

    def _cancel_extend(self):
        """Cancel the current extend operation."""
        self._clear_boundary_markers()
        self._clear_preview()
        self.boundary_entities.clear()
        self.extend_state = ExtendState.SELECT_BOUNDARY

        # Emit cancellation signal
        self.extend_cancelled.emit()

        logger.debug("Extend operation cancelled")

    def set_auto_select_boundaries(self, auto_select: bool):
        """Set auto-select boundaries from selection."""
        self.auto_select_boundaries = auto_select

        if (
            auto_select
            and self.extend_state == ExtendState.SELECT_BOUNDARY
            and self.selection_manager.has_selection()
        ):
            self.boundary_entities = list(self.selection_manager.get_selected_items())
            self._create_boundary_markers()
            self._start_extending()

    def set_show_preview(self, show_preview: bool):
        """Set whether to show extension preview."""
        self.show_extension_preview = show_preview
        if not show_preview:
            self._clear_preview()

    def add_boundary_from_selection(self):
        """Add selected entities as boundaries."""
        if self.selection_manager.has_selection():
            selected_items = self.selection_manager.get_selected_items()
            for item in selected_items:
                if self._is_valid_boundary(item):
                    self._add_boundary_entity(item)

            if (
                self.boundary_entities
                and self.extend_state == ExtendState.SELECT_BOUNDARY
            ):
                self._start_extending()

    def selection_changed(self, selected_items: List[QGraphicsItem]):
        """Handle selection changes."""
        if (
            self.auto_select_boundaries
            and self.extend_state == ExtendState.SELECT_BOUNDARY
        ):
            if selected_items:
                self.boundary_entities = [
                    item for item in selected_items if self._is_valid_boundary(item)
                ]
                self._create_boundary_markers()
                if self.boundary_entities:
                    self._start_extending()

    def get_tool_info(self) -> Dict[str, Any]:
        """Get current tool information."""
        return {
            **super().get_tool_info(),
            "extend_state": self.extend_state.name,
            "boundary_count": len(self.boundary_entities),
            "auto_select_boundaries": self.auto_select_boundaries,
            "show_extension_preview": self.show_extension_preview,
            "boundary_entities": [
                getattr(e, "entity_id", "unknown") for e in self.boundary_entities
            ],
        }
