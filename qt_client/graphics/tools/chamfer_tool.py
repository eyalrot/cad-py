"""
Chamfer tool for CAD drawing operations.

This module provides an interactive chamfer tool that allows users to create
beveled corners between entities with distance input and real-time preview.
"""

import asyncio
import logging
import math
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPen
from PySide6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsLineItem

from ...core.selection_manager import SelectionManager
from .base_tool import BaseTool, ToolState

logger = logging.getLogger(__name__)


class ChamferState(Enum):
    """States for chamfer tool operation."""

    SELECT_FIRST_ENTITY = auto()
    SELECT_SECOND_ENTITY = auto()
    SET_FIRST_DISTANCE = auto()
    SET_SECOND_DISTANCE = auto()
    CHAMFERING = auto()
    COMPLETED = auto()


class ChamferMode(Enum):
    """Chamfer modes."""

    EQUAL_DISTANCES = auto()  # Same distance on both entities
    DIFFERENT_DISTANCES = auto()  # Different distances on each entity
    ANGLE_DISTANCE = auto()  # Angle and distance mode


class ChamferTool(BaseTool):
    """
    Interactive chamfer tool for creating beveled corners.

    Features:
    - Select two entities to chamfer between
    - Set chamfer distances for each entity
    - Equal or different distance modes
    - Real-time preview of chamfer line
    - Visual feedback for entity selection
    - Support for line-line chamfers
    - Snap integration for precise distance input
    - Undo/redo support through command pattern
    """

    # Signals
    first_entity_selected = Signal(QGraphicsItem)
    second_entity_selected = Signal(QGraphicsItem)
    first_distance_set = Signal(float)
    second_distance_set = Signal(float)
    chamfer_completed = Signal(
        QGraphicsItem, QGraphicsItem, float, float
    )  # entity1, entity2, dist1, dist2
    chamfer_cancelled = Signal()

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
        self.chamfer_state = ChamferState.SELECT_FIRST_ENTITY
        self.chamfer_mode = ChamferMode.EQUAL_DISTANCES

        # Chamfer operation data
        self.first_entity: Optional[QGraphicsItem] = None
        self.second_entity: Optional[QGraphicsItem] = None
        self.first_distance = 5.0  # Default distance for first entity
        self.second_distance = 5.0  # Default distance for second entity
        self.first_reference_point: Optional[QPointF] = None
        self.second_reference_point: Optional[QPointF] = None

        # Preview graphics
        self.first_marker: Optional[QGraphicsEllipseItem] = None
        self.second_marker: Optional[QGraphicsEllipseItem] = None
        self.preview_chamfer: Optional[QGraphicsLineItem] = None
        self.first_distance_line: Optional[QGraphicsLineItem] = None
        self.second_distance_line: Optional[QGraphicsLineItem] = None

        # Visual properties
        self.entity_marker_pen = QPen(QColor(255, 150, 100, 200))  # Orange for chamfer
        self.entity_marker_pen.setWidth(3)

        self.preview_pen = QPen(QColor(255, 150, 100, 180))
        self.preview_pen.setWidth(2)
        self.preview_pen.setStyle(Qt.DashLine)

        self.distance_pen = QPen(QColor(100, 200, 255, 180))
        self.distance_pen.setWidth(1)
        self.distance_pen.setStyle(Qt.DotLine)

        # Settings
        self.show_distance_preview = True
        self.auto_select_from_selection = True

        logger.debug("Chamfer tool initialized")

    def get_tool_name(self) -> str:
        """Get tool display name."""
        mode_text = (
            "Equal" if self.chamfer_mode == ChamferMode.EQUAL_DISTANCES else "Different"
        )
        return f"Chamfer ({mode_text})"

    def get_status_text(self) -> str:
        """Get current status text."""
        if self.chamfer_state == ChamferState.SELECT_FIRST_ENTITY:
            return "Select first entity for chamfer"
        elif self.chamfer_state == ChamferState.SELECT_SECOND_ENTITY:
            return "Select second entity for chamfer"
        elif self.chamfer_state == ChamferState.SET_FIRST_DISTANCE:
            return f"Set first distance (current: {self.first_distance:.2f}) - click point or press Enter"
        elif self.chamfer_state == ChamferState.SET_SECOND_DISTANCE:
            return f"Set second distance (current: {self.second_distance:.2f}) - click point or press Enter"
        elif self.chamfer_state == ChamferState.CHAMFERING:
            return "Creating chamfer..."
        else:
            return "Chamfer tool ready"

    def activate(self) -> bool:
        """Activate the chamfer tool."""
        if not super().activate():
            return False

        # Check if there are two selected entities
        if self.selection_manager.has_selection() and self.auto_select_from_selection:
            selected_items = self.selection_manager.get_selected_items()
            valid_items = [
                item for item in selected_items if self._is_valid_chamfer_entity(item)
            ]

            if len(valid_items) >= 2:
                self._select_first_entity(valid_items[0])
                self._select_second_entity(valid_items[1])
                logger.debug("Chamfer tool activated with two selected entities")
            elif len(valid_items) == 1:
                self._select_first_entity(valid_items[0])
                logger.debug("Chamfer tool activated with one selected entity")
            else:
                self.chamfer_state = ChamferState.SELECT_FIRST_ENTITY
                logger.debug("Chamfer tool activated, waiting for entity selection")
        else:
            self.chamfer_state = ChamferState.SELECT_FIRST_ENTITY
            logger.debug("Chamfer tool activated, waiting for entity selection")

        return True

    def deactivate(self):
        """Deactivate the chamfer tool."""
        self._clear_preview()
        self._clear_markers()
        self.first_entity = None
        self.second_entity = None
        self.first_reference_point = None
        self.second_reference_point = None
        self.chamfer_state = ChamferState.SELECT_FIRST_ENTITY

        super().deactivate()
        logger.debug("Chamfer tool deactivated")

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        """Handle mouse press events."""
        world_pos = self.scene_pos_from_event(event)

        # Apply snapping
        snap_result = self.snap_engine.snap_point(world_pos, self.view)
        if snap_result.snapped:
            world_pos = snap_result.point

        if self.chamfer_state == ChamferState.SELECT_FIRST_ENTITY:
            # Find item at click position
            clicked_item = self.scene.itemAt(world_pos, self.view.transform())
            if clicked_item and self._is_valid_chamfer_entity(clicked_item):
                self._select_first_entity(clicked_item)
                return True

        elif self.chamfer_state == ChamferState.SELECT_SECOND_ENTITY:
            # Find item at click position
            clicked_item = self.scene.itemAt(world_pos, self.view.transform())
            if (
                clicked_item
                and self._is_valid_chamfer_entity(clicked_item)
                and clicked_item != self.first_entity
            ):
                self._select_second_entity(clicked_item)
                return True

        elif self.chamfer_state == ChamferState.SET_FIRST_DISTANCE:
            self._set_first_distance_by_point(world_pos)
            return True

        elif self.chamfer_state == ChamferState.SET_SECOND_DISTANCE:
            self._set_second_distance_by_point(world_pos)
            return True

        return False

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        """Handle mouse move events."""
        world_pos = self.scene_pos_from_event(event)

        # Apply snapping
        snap_result = self.snap_engine.snap_point(world_pos, self.view)
        if snap_result.snapped:
            world_pos = snap_result.point

        if (
            self.chamfer_state == ChamferState.SET_FIRST_DISTANCE
            and self.show_distance_preview
        ):
            self._update_first_distance_preview(world_pos)
            return True
        elif (
            self.chamfer_state == ChamferState.SET_SECOND_DISTANCE
            and self.show_distance_preview
        ):
            self._update_second_distance_preview(world_pos)
            return True

        return False

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle key press events."""
        if event.key() == Qt.Key_Escape:
            self._cancel_chamfer()
            return True
        elif event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            if self.chamfer_state == ChamferState.SET_FIRST_DISTANCE:
                self._confirm_first_distance()
                return True
            elif self.chamfer_state == ChamferState.SET_SECOND_DISTANCE:
                self._execute_chamfer()
                return True
        elif event.key() == Qt.Key_M and event.modifiers() & Qt.ControlModifier:
            # Toggle chamfer mode
            self._toggle_chamfer_mode()
            return True
        elif event.key() == Qt.Key_D and event.modifiers() & Qt.ControlModifier:
            # Toggle distance preview
            self.show_distance_preview = not self.show_distance_preview
            if not self.show_distance_preview:
                self._clear_distance_preview()
            return True
        elif event.key() == Qt.Key_C and event.modifiers() & Qt.ControlModifier:
            # Clear selections
            self._clear_selections()
            return True

        return super().handle_key_press(event)

    def _is_valid_chamfer_entity(self, item: QGraphicsItem) -> bool:
        """Check if item can be used for chamfer."""
        # Check if item is not a marker or preview item
        if item in [
            self.first_marker,
            self.second_marker,
            self.preview_chamfer,
            self.first_distance_line,
            self.second_distance_line,
        ]:
            return False

        # Check if item has entity_id (is a CAD entity)
        if not hasattr(item, "entity_id"):
            return False

        # For chamfer, we typically support lines
        # In a real implementation, check if it's a supported entity type
        return True

    def _select_first_entity(self, entity: QGraphicsItem):
        """Select first entity for chamfer."""
        self.first_entity = entity
        self.chamfer_state = ChamferState.SELECT_SECOND_ENTITY

        # Create marker
        self._create_first_marker()

        # Emit signal
        self.first_entity_selected.emit(entity)

        logger.debug(
            f"Selected first entity for chamfer: {getattr(entity, 'entity_id', 'unknown')}"
        )

    def _select_second_entity(self, entity: QGraphicsItem):
        """Select second entity for chamfer."""
        self.second_entity = entity
        self.chamfer_state = ChamferState.SET_FIRST_DISTANCE

        # Create marker
        self._create_second_marker()

        # Emit signal
        self.second_entity_selected.emit(entity)

        logger.debug(
            f"Selected second entity for chamfer: {getattr(entity, 'entity_id', 'unknown')}"
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

        # Create marker with different style
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

    def _set_first_distance_by_point(self, point: QPointF):
        """Set first chamfer distance by clicking a point."""
        if not self.first_entity:
            return

        # Calculate distance from intersection point
        intersection_point = self._estimate_intersection_point()

        if intersection_point:
            distance = (
                (point.x() - intersection_point.x()) ** 2
                + (point.y() - intersection_point.y()) ** 2
            ) ** 0.5

            self.first_distance = max(0.1, distance)  # Minimum distance
            self.first_reference_point = point

            # Clear first distance preview
            self._clear_first_distance_preview()

            # Move to second distance or execute if equal mode
            if self.chamfer_mode == ChamferMode.EQUAL_DISTANCES:
                self.second_distance = self.first_distance
                asyncio.create_task(self._execute_chamfer())
            else:
                self.chamfer_state = ChamferState.SET_SECOND_DISTANCE

            # Emit signal
            self.first_distance_set.emit(self.first_distance)

            logger.debug(f"First chamfer distance set to: {self.first_distance:.2f}")

    def _set_second_distance_by_point(self, point: QPointF):
        """Set second chamfer distance by clicking a point."""
        if not self.second_entity:
            return

        # Calculate distance from intersection point
        intersection_point = self._estimate_intersection_point()

        if intersection_point:
            distance = (
                (point.x() - intersection_point.x()) ** 2
                + (point.y() - intersection_point.y()) ** 2
            ) ** 0.5

            self.second_distance = max(0.1, distance)  # Minimum distance
            self.second_reference_point = point

            # Clear second distance preview
            self._clear_second_distance_preview()

            # Execute chamfer
            asyncio.create_task(self._execute_chamfer())

            # Emit signal
            self.second_distance_set.emit(self.second_distance)

            logger.debug(f"Second chamfer distance set to: {self.second_distance:.2f}")

    def _confirm_first_distance(self):
        """Confirm first distance and move to second distance or execute."""
        if self.chamfer_mode == ChamferMode.EQUAL_DISTANCES:
            self.second_distance = self.first_distance
            asyncio.create_task(self._execute_chamfer())
        else:
            self.chamfer_state = ChamferState.SET_SECOND_DISTANCE
            self._clear_first_distance_preview()

        logger.debug(f"Confirmed first chamfer distance: {self.first_distance:.2f}")

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

    def _update_first_distance_preview(self, current_point: QPointF):
        """Update first distance preview."""
        if not self.first_entity:
            return

        # Clear existing preview
        self._clear_first_distance_preview()

        # Calculate current distance
        intersection_point = self._estimate_intersection_point()

        if intersection_point:
            current_distance = (
                (current_point.x() - intersection_point.x()) ** 2
                + (current_point.y() - intersection_point.y()) ** 2
            ) ** 0.5

            # Create distance line
            self.first_distance_line = QGraphicsLineItem(
                intersection_point.x(),
                intersection_point.y(),
                current_point.x(),
                current_point.y(),
            )
            self.first_distance_line.setPen(self.distance_pen)
            self.first_distance_line.setZValue(999)

            self.scene.addItem(self.first_distance_line)

            # Update current distance for display
            self.first_distance = max(0.1, current_distance)

    def _update_second_distance_preview(self, current_point: QPointF):
        """Update second distance preview."""
        if not self.second_entity:
            return

        # Clear existing preview
        self._clear_second_distance_preview()

        # Calculate current distance
        intersection_point = self._estimate_intersection_point()

        if intersection_point:
            current_distance = (
                (current_point.x() - intersection_point.x()) ** 2
                + (current_point.y() - intersection_point.y()) ** 2
            ) ** 0.5

            # Create distance line
            second_pen = QPen(self.distance_pen)
            second_pen.setStyle(Qt.DashLine)

            self.second_distance_line = QGraphicsLineItem(
                intersection_point.x(),
                intersection_point.y(),
                current_point.x(),
                current_point.y(),
            )
            self.second_distance_line.setPen(second_pen)
            self.second_distance_line.setZValue(999)

            self.scene.addItem(self.second_distance_line)

            # Create chamfer preview
            self._create_chamfer_preview(
                intersection_point, self.first_distance, current_distance
            )

            # Update current distance for display
            self.second_distance = max(0.1, current_distance)

    def _create_chamfer_preview(
        self, intersection: QPointF, dist1: float, dist2: float
    ):
        """Create preview of chamfer line."""
        try:
            # This is a simplified preview calculation
            # In reality, would use proper geometric calculations

            # Calculate chamfer endpoints (simplified)
            angle1 = 0  # Default angles
            angle2 = math.pi / 2

            point1 = QPointF(
                intersection.x() + dist1 * math.cos(angle1),
                intersection.y() + dist1 * math.sin(angle1),
            )

            point2 = QPointF(
                intersection.x() + dist2 * math.cos(angle2),
                intersection.y() + dist2 * math.sin(angle2),
            )

            # Clear existing preview
            if self.preview_chamfer and self.preview_chamfer.scene():
                self.scene.removeItem(self.preview_chamfer)

            # Create chamfer line
            self.preview_chamfer = QGraphicsLineItem(
                point1.x(), point1.y(), point2.x(), point2.y()
            )
            self.preview_chamfer.setPen(self.preview_pen)
            self.preview_chamfer.setZValue(998)

            self.scene.addItem(self.preview_chamfer)

        except Exception as e:
            logger.warning(f"Error creating chamfer preview: {e}")

    def _clear_first_distance_preview(self):
        """Clear first distance preview."""
        if self.first_distance_line and self.first_distance_line.scene():
            self.scene.removeItem(self.first_distance_line)
            self.first_distance_line = None

    def _clear_second_distance_preview(self):
        """Clear second distance preview."""
        if self.second_distance_line and self.second_distance_line.scene():
            self.scene.removeItem(self.second_distance_line)
            self.second_distance_line = None

        if self.preview_chamfer and self.preview_chamfer.scene():
            self.scene.removeItem(self.preview_chamfer)
            self.preview_chamfer = None

    def _clear_distance_preview(self):
        """Clear all distance previews."""
        self._clear_first_distance_preview()
        self._clear_second_distance_preview()

    def _clear_preview(self):
        """Clear all preview graphics."""
        self._clear_distance_preview()

    def _toggle_chamfer_mode(self):
        """Toggle between equal and different distance modes."""
        if self.chamfer_mode == ChamferMode.EQUAL_DISTANCES:
            self.chamfer_mode = ChamferMode.DIFFERENT_DISTANCES
        else:
            self.chamfer_mode = ChamferMode.EQUAL_DISTANCES

        logger.debug(f"Chamfer mode changed to: {self.chamfer_mode.name}")

    async def _execute_chamfer(self):
        """Execute the chamfer operation."""
        if not self.first_entity or not self.second_entity:
            return

        self.chamfer_state = ChamferState.CHAMFERING

        try:
            # Clear preview
            self._clear_preview()

            # Create chamfer command
            from ...core.commands import ChamferCommand

            # Get entity IDs
            entity1_id = getattr(self.first_entity, "entity_id", None)
            entity2_id = getattr(self.second_entity, "entity_id", None)

            if not entity1_id or not entity2_id:
                logger.error("Invalid entity IDs for chamfer operation")
                self._reset_tool()
                return

            # Create and execute chamfer command
            chamfer_command = ChamferCommand(
                self.api_client,
                entity1_id,
                entity2_id,
                self.first_distance,
                self.second_distance,
            )

            # Execute through command manager for undo support
            success = await self.command_manager.execute_command(chamfer_command)

            if success:
                # Emit completion signal
                self.chamfer_completed.emit(
                    self.first_entity,
                    self.second_entity,
                    self.first_distance,
                    self.second_distance,
                )

                logger.info(
                    f"Created chamfer between {entity1_id} and {entity2_id} "
                    f"with distances {self.first_distance:.2f}, {self.second_distance:.2f}"
                )

                # Reset for next operation
                self._reset_tool()
            else:
                logger.error("Chamfer command execution failed")
                self._reset_tool()

        except Exception as e:
            logger.error(f"Error executing chamfer: {e}")
            self._reset_tool()

    def _cancel_chamfer(self):
        """Cancel the current chamfer operation."""
        self._clear_preview()
        self._clear_markers()
        self._reset_tool()

        # Emit cancellation signal
        self.chamfer_cancelled.emit()

        logger.debug("Chamfer operation cancelled")

    def _clear_selections(self):
        """Clear entity selections."""
        self._clear_markers()
        self.first_entity = None
        self.second_entity = None
        self.chamfer_state = ChamferState.SELECT_FIRST_ENTITY

        logger.debug("Chamfer selections cleared")

    def _reset_tool(self):
        """Reset tool to initial state."""
        self.chamfer_state = ChamferState.SELECT_FIRST_ENTITY
        self.first_entity = None
        self.second_entity = None
        self.first_reference_point = None
        self.second_reference_point = None
        self._clear_markers()

    def set_chamfer_distances(
        self, distance1: float, distance2: Optional[float] = None
    ):
        """Set chamfer distances directly."""
        self.first_distance = max(0.1, distance1)

        if distance2 is not None:
            self.second_distance = max(0.1, distance2)
            self.chamfer_mode = ChamferMode.DIFFERENT_DISTANCES
        else:
            self.second_distance = self.first_distance
            self.chamfer_mode = ChamferMode.EQUAL_DISTANCES

        # Execute if both entities are selected
        if (
            self.first_entity
            and self.second_entity
            and self.chamfer_state
            in [ChamferState.SET_FIRST_DISTANCE, ChamferState.SET_SECOND_DISTANCE]
        ):
            asyncio.create_task(self._execute_chamfer())

        logger.debug(
            f"Chamfer distances set to: {self.first_distance:.2f}, {self.second_distance:.2f}"
        )

    def set_chamfer_mode(self, mode: ChamferMode):
        """Set chamfer mode."""
        self.chamfer_mode = mode

        if mode == ChamferMode.EQUAL_DISTANCES:
            self.second_distance = self.first_distance

        logger.debug(f"Chamfer mode set to: {mode.name}")

    def set_show_distance_preview(self, show_preview: bool):
        """Set whether to show distance preview."""
        self.show_distance_preview = show_preview
        if not show_preview:
            self._clear_distance_preview()

    def set_auto_select_from_selection(self, auto_select: bool):
        """Set whether to auto-select from current selection."""
        self.auto_select_from_selection = auto_select

    def selection_changed(self, selected_items: List[QGraphicsItem]):
        """Handle selection changes."""
        if not self.auto_select_from_selection:
            return

        valid_items = [
            item for item in selected_items if self._is_valid_chamfer_entity(item)
        ]

        if (
            self.chamfer_state == ChamferState.SELECT_FIRST_ENTITY
            and len(valid_items) >= 1
        ):
            self._select_first_entity(valid_items[0])
            if len(valid_items) >= 2:
                self._select_second_entity(valid_items[1])
        elif (
            self.chamfer_state == ChamferState.SELECT_SECOND_ENTITY
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
            "chamfer_state": self.chamfer_state.name,
            "chamfer_mode": self.chamfer_mode.name,
            "first_entity": getattr(self.first_entity, "entity_id", None)
            if self.first_entity
            else None,
            "second_entity": getattr(self.second_entity, "entity_id", None)
            if self.second_entity
            else None,
            "first_distance": self.first_distance,
            "second_distance": self.second_distance,
            "first_reference_point": {
                "x": self.first_reference_point.x(),
                "y": self.first_reference_point.y(),
            }
            if self.first_reference_point
            else None,
            "second_reference_point": {
                "x": self.second_reference_point.x(),
                "y": self.second_reference_point.y(),
            }
            if self.second_reference_point
            else None,
            "show_distance_preview": self.show_distance_preview,
            "auto_select_from_selection": self.auto_select_from_selection,
        }
