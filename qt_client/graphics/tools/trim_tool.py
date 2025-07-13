"""
Trim tool for CAD drawing operations.

This module provides an interactive trim tool that allows users to trim
entities to boundaries with precise control and visual feedback.
"""

import asyncio
import logging
from enum import Enum, auto
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem

from ...core.selection_manager import SelectionManager
from .base_tool import BaseTool, ToolState

logger = logging.getLogger(__name__)


class TrimState(Enum):
    """States for trim tool operation."""

    SELECT_BOUNDARY = auto()
    SELECT_ENTITY_TO_TRIM = auto()
    TRIMMING = auto()
    COMPLETED = auto()


class TrimTool(BaseTool):
    """
    Interactive trim tool for trimming entities to boundaries.

    Features:
    - Select boundary entities for trimming
    - Click entities to trim them to nearest boundary
    - Visual feedback for boundary selection
    - Support for multiple boundary entities
    - Snap integration for precise selection
    - Undo/redo support through command pattern
    """

    # Signals
    boundary_selected = Signal(QGraphicsItem)
    entity_trimmed = Signal(QGraphicsItem, QGraphicsItem)  # entity, boundary
    trim_completed = Signal()
    trim_cancelled = Signal()

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
        self.trim_state = TrimState.SELECT_BOUNDARY

        # Trim operation data
        self.boundary_entities: List[QGraphicsItem] = []
        self.boundary_markers: List[QGraphicsEllipseItem] = []

        # Visual properties
        self.boundary_marker_pen = QPen(QColor(255, 150, 0, 200))
        self.boundary_marker_pen.setWidth(3)

        self.trim_feedback_pen = QPen(QColor(255, 100, 100, 180))
        self.trim_feedback_pen.setWidth(2)
        self.trim_feedback_pen.setStyle(Qt.DashLine)

        # Settings
        self.auto_select_boundaries = (
            False  # If True, use selected entities as boundaries
        )

        logger.debug("Trim tool initialized")

    def get_tool_name(self) -> str:
        """Get tool display name."""
        return "Trim"

    def get_status_text(self) -> str:
        """Get current status text."""
        if self.trim_state == TrimState.SELECT_BOUNDARY:
            boundary_count = len(self.boundary_entities)
            if boundary_count == 0:
                return (
                    "Select boundary entities (or press Enter to use selected entities)"
                )
            else:
                return f"Select boundary entities ({boundary_count} selected) or press Enter to start trimming"
        elif self.trim_state == TrimState.SELECT_ENTITY_TO_TRIM:
            return f"Click entities to trim to boundaries ({len(self.boundary_entities)} boundaries active)"
        elif self.trim_state == TrimState.TRIMMING:
            return "Trimming entity..."
        else:
            return "Trim tool ready"

    def activate(self) -> bool:
        """Activate the trim tool."""
        if not super().activate():
            return False

        # Check if there are selected entities to use as boundaries
        if self.selection_manager.has_selection() and self.auto_select_boundaries:
            self.boundary_entities = list(self.selection_manager.get_selected_items())
            self._create_boundary_markers()
            self.trim_state = TrimState.SELECT_ENTITY_TO_TRIM
            logger.debug(
                f"Trim tool activated with {len(self.boundary_entities)} boundary entities from selection"
            )
        else:
            self.trim_state = TrimState.SELECT_BOUNDARY
            logger.debug("Trim tool activated, waiting for boundary selection")

        return True

    def deactivate(self):
        """Deactivate the trim tool."""
        self._clear_boundary_markers()
        self.boundary_entities.clear()
        self.trim_state = TrimState.SELECT_BOUNDARY

        super().deactivate()
        logger.debug("Trim tool deactivated")

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        """Handle mouse press events."""
        world_pos = self.scene_pos_from_event(event)

        # Find item at click position
        clicked_item = self.scene.itemAt(world_pos, self.view.transform())

        if self.trim_state == TrimState.SELECT_BOUNDARY:
            if clicked_item and self._is_valid_boundary(clicked_item):
                self._add_boundary_entity(clicked_item)
                return True

        elif self.trim_state == TrimState.SELECT_ENTITY_TO_TRIM:
            if clicked_item and self._is_valid_trim_entity(clicked_item):
                asyncio.create_task(self._trim_entity(clicked_item, world_pos))
                return True

        return False

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle key press events."""
        if event.key() == Qt.Key_Escape:
            self._cancel_trim()
            return True
        elif event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            if self.trim_state == TrimState.SELECT_BOUNDARY:
                if self.boundary_entities:
                    self._start_trimming()
                elif self.selection_manager.has_selection():
                    # Use selected entities as boundaries
                    self.boundary_entities = list(
                        self.selection_manager.get_selected_items()
                    )
                    self._create_boundary_markers()
                    self._start_trimming()
                return True
        elif event.key() == Qt.Key_C and event.modifiers() & Qt.ControlModifier:
            # Clear boundaries
            self._clear_boundaries()
            return True

        return super().handle_key_press(event)

    def _is_valid_boundary(self, item: QGraphicsItem) -> bool:
        """Check if item can be used as a boundary."""
        # Check if item is not already a boundary marker
        if item in self.boundary_markers:
            return False

        # Check if item has entity_id (is a CAD entity)
        if not hasattr(item, "entity_id"):
            return False

        # Check if already selected as boundary
        if item in self.boundary_entities:
            return False

        return True

    def _is_valid_trim_entity(self, item: QGraphicsItem) -> bool:
        """Check if item can be trimmed."""
        # Check if item is not a boundary marker
        if item in self.boundary_markers:
            return False

        # Check if item has entity_id (is a CAD entity)
        if not hasattr(item, "entity_id"):
            return False

        # Check if item is not a boundary entity
        if item in self.boundary_entities:
            return False

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

        # Create marker
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

        if self.trim_state == TrimState.SELECT_ENTITY_TO_TRIM:
            self.trim_state = TrimState.SELECT_BOUNDARY

        logger.debug("Boundary entities cleared")

    def _start_trimming(self):
        """Start the trimming phase."""
        if self.boundary_entities:
            self.trim_state = TrimState.SELECT_ENTITY_TO_TRIM
            logger.debug(
                f"Started trimming with {len(self.boundary_entities)} boundaries"
            )
        else:
            logger.warning("Cannot start trimming without boundary entities")

    async def _trim_entity(self, entity: QGraphicsItem, click_point: QPointF):
        """Trim entity to nearest boundary."""
        if not self.boundary_entities:
            logger.warning("No boundary entities for trimming")
            return

        self.trim_state = TrimState.TRIMMING

        try:
            # Find the best boundary for trimming
            best_boundary = self._find_best_boundary(entity, click_point)

            if not best_boundary:
                logger.warning("No suitable boundary found for trimming")
                self.trim_state = TrimState.SELECT_ENTITY_TO_TRIM
                return

            # Create trim command
            from ...core.commands import TrimCommand

            # Get entity IDs
            entity_id = getattr(entity, "entity_id", None)
            boundary_id = getattr(best_boundary, "entity_id", None)

            if not entity_id or not boundary_id:
                logger.error("Invalid entity IDs for trim operation")
                self.trim_state = TrimState.SELECT_ENTITY_TO_TRIM
                return

            # Create and execute trim command
            trim_command = TrimCommand(
                self.api_client,
                entity_id,
                boundary_id,
                click_point.x(),
                click_point.y(),
            )

            # Execute through command manager for undo support
            success = await self.command_manager.execute_command(trim_command)

            if success:
                # Emit signals
                self.entity_trimmed.emit(entity, best_boundary)

                logger.info(f"Trimmed entity {entity_id} to boundary {boundary_id}")
            else:
                logger.error("Trim command execution failed")

            # Return to trimming state
            self.trim_state = TrimState.SELECT_ENTITY_TO_TRIM

        except Exception as e:
            logger.error(f"Error trimming entity: {e}")
            self.trim_state = TrimState.SELECT_ENTITY_TO_TRIM

    def _find_best_boundary(
        self, entity: QGraphicsItem, click_point: QPointF
    ) -> Optional[QGraphicsItem]:
        """Find the best boundary entity for trimming."""
        if not self.boundary_entities:
            return None

        # For now, find the closest boundary entity
        # In a real implementation, this would find the boundary that creates
        # the most sensible trim based on intersection analysis

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

    def _cancel_trim(self):
        """Cancel the current trim operation."""
        self._clear_boundary_markers()
        self.boundary_entities.clear()
        self.trim_state = TrimState.SELECT_BOUNDARY

        # Emit cancellation signal
        self.trim_cancelled.emit()

        logger.debug("Trim operation cancelled")

    def set_auto_select_boundaries(self, auto_select: bool):
        """Set auto-select boundaries from selection."""
        self.auto_select_boundaries = auto_select

        if (
            auto_select
            and self.trim_state == TrimState.SELECT_BOUNDARY
            and self.selection_manager.has_selection()
        ):
            self.boundary_entities = list(self.selection_manager.get_selected_items())
            self._create_boundary_markers()
            self._start_trimming()

    def add_boundary_from_selection(self):
        """Add selected entities as boundaries."""
        if self.selection_manager.has_selection():
            selected_items = self.selection_manager.get_selected_items()
            for item in selected_items:
                if self._is_valid_boundary(item):
                    self._add_boundary_entity(item)

            if self.boundary_entities and self.trim_state == TrimState.SELECT_BOUNDARY:
                self._start_trimming()

    def selection_changed(self, selected_items: List[QGraphicsItem]):
        """Handle selection changes."""
        if self.auto_select_boundaries and self.trim_state == TrimState.SELECT_BOUNDARY:
            if selected_items:
                self.boundary_entities = [
                    item for item in selected_items if self._is_valid_boundary(item)
                ]
                self._create_boundary_markers()
                if self.boundary_entities:
                    self._start_trimming()

    def get_tool_info(self) -> Dict[str, Any]:
        """Get current tool information."""
        return {
            **super().get_tool_info(),
            "trim_state": self.trim_state.name,
            "boundary_count": len(self.boundary_entities),
            "auto_select_boundaries": self.auto_select_boundaries,
            "boundary_entities": [
                getattr(e, "entity_id", "unknown") for e in self.boundary_entities
            ],
        }
