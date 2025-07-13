"""
Move tool for CAD drawing operations.

This module provides an interactive move tool that allows users to relocate
selected geometry with precise control and real-time preview.
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


class MoveState(Enum):
    """States for move tool operation."""

    WAITING_FOR_SELECTION = auto()
    WAITING_FOR_BASE_POINT = auto()
    WAITING_FOR_DESTINATION = auto()
    MOVING = auto()
    COMPLETED = auto()


class MoveTool(BaseTool):
    """
    Interactive move tool for relocating selected geometry.

    Features:
    - Move selected objects with base point and destination
    - Real-time preview during movement
    - Snap integration for precise positioning
    - Visual feedback with temporary graphics
    - Undo/redo support through command pattern
    """

    # Signals
    move_started = Signal(QPointF)  # base point
    move_preview = Signal(QPointF, QPointF)  # base, current
    move_completed = Signal(QPointF, QPointF)  # base, destination
    move_cancelled = Signal()

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
        self.move_state = MoveState.WAITING_FOR_SELECTION

        # Move operation data
        self.base_point: Optional[QPointF] = None
        self.current_point: Optional[QPointF] = None
        self.selected_items: List[QGraphicsItem] = []

        # Preview graphics
        self.preview_items: List[QGraphicsItem] = []
        self.reference_line: Optional[QGraphicsLineItem] = None

        # Visual properties
        self.preview_pen = QPen(QColor(100, 150, 255, 180))
        self.preview_pen.setWidth(1)
        self.preview_pen.setStyle(Qt.DashLine)

        self.reference_pen = QPen(QColor(255, 100, 100, 200))
        self.reference_pen.setWidth(1)
        self.reference_pen.setStyle(Qt.DotLine)

        logger.debug("Move tool initialized")

    def get_tool_name(self) -> str:
        """Get tool display name."""
        return "Move"

    def get_status_text(self) -> str:
        """Get current status text."""
        if self.move_state == MoveState.WAITING_FOR_SELECTION:
            return "Select objects to move"
        elif self.move_state == MoveState.WAITING_FOR_BASE_POINT:
            return "Select base point for move"
        elif self.move_state == MoveState.WAITING_FOR_DESTINATION:
            return f"Select destination point (distance: {self._get_current_distance():.2f})"
        elif self.move_state == MoveState.MOVING:
            return "Moving objects..."
        else:
            return "Move tool ready"

    def activate(self) -> bool:
        """Activate the move tool."""
        if not super().activate():
            return False

        # Check if there are selected objects
        if self.selection_manager.has_selection():
            self.selected_items = list(self.selection_manager.get_selected_items())
            self.move_state = MoveState.WAITING_FOR_BASE_POINT
            logger.debug(
                f"Move tool activated with {len(self.selected_items)} selected items"
            )
        else:
            self.move_state = MoveState.WAITING_FOR_SELECTION
            logger.debug("Move tool activated, waiting for selection")

        return True

    def deactivate(self):
        """Deactivate the move tool."""
        self._clear_preview()
        self.move_state = MoveState.WAITING_FOR_SELECTION
        self.base_point = None
        self.current_point = None
        self.selected_items.clear()

        super().deactivate()
        logger.debug("Move tool deactivated")

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        """Handle mouse press events."""
        world_pos = self.scene_pos_from_event(event)

        # Apply snapping
        snap_result = self.snap_engine.snap_point(world_pos, self.view)
        if snap_result.snapped:
            world_pos = snap_result.point

        if self.move_state == MoveState.WAITING_FOR_SELECTION:
            # Let selection manager handle the click
            return False

        elif self.move_state == MoveState.WAITING_FOR_BASE_POINT:
            self._set_base_point(world_pos)
            return True

        elif self.move_state == MoveState.WAITING_FOR_DESTINATION:
            self._execute_move(world_pos)
            return True

        return False

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        """Handle mouse move events."""
        if self.move_state != MoveState.WAITING_FOR_DESTINATION:
            return False

        world_pos = self.scene_pos_from_event(event)

        # Apply snapping
        snap_result = self.snap_engine.snap_point(world_pos, self.view, self.base_point)
        if snap_result.snapped:
            world_pos = snap_result.point

        self._update_preview(world_pos)
        return True

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle key press events."""
        if event.key() == Qt.Key_Escape:
            self._cancel_move()
            return True
        elif event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            if (
                self.move_state == MoveState.WAITING_FOR_DESTINATION
                and self.current_point
            ):
                self._execute_move(self.current_point)
                return True

        return super().handle_key_press(event)

    def _set_base_point(self, point: QPointF):
        """Set the base point for the move operation."""
        self.base_point = point
        self.current_point = point
        self.move_state = MoveState.WAITING_FOR_DESTINATION

        # Create reference line
        self._create_reference_line()

        # Emit signal
        self.move_started.emit(self.base_point)

        logger.debug(f"Move base point set to ({point.x():.2f}, {point.y():.2f})")

    def _update_preview(self, current_point: QPointF):
        """Update the move preview."""
        if not self.base_point:
            return

        self.current_point = current_point

        # Update reference line
        if self.reference_line:
            self.reference_line.setLine(
                self.base_point.x(),
                self.base_point.y(),
                current_point.x(),
                current_point.y(),
            )

        # Update preview items
        self._update_preview_items()

        # Emit signal
        self.move_preview.emit(self.base_point, current_point)

    def _create_reference_line(self):
        """Create the reference line from base point to cursor."""
        if self.reference_line:
            self.scene.removeItem(self.reference_line)

        self.reference_line = QGraphicsLineItem()
        self.reference_line.setPen(self.reference_pen)
        self.reference_line.setZValue(1000)  # Draw on top
        self.scene.addItem(self.reference_line)

    def _update_preview_items(self):
        """Update preview items showing future positions."""
        if not self.base_point or not self.current_point:
            return

        # Calculate displacement
        delta = self.current_point - self.base_point

        # Remove existing preview items
        self._clear_preview_items()

        # Create preview items for each selected item
        for item in self.selected_items:
            preview_item = self._create_preview_item(item, delta)
            if preview_item:
                self.preview_items.append(preview_item)
                self.scene.addItem(preview_item)

    def _create_preview_item(
        self, original_item: QGraphicsItem, delta: QPointF
    ) -> Optional[QGraphicsItem]:
        """Create a preview item for the given original item."""
        try:
            # Clone the item's geometry with offset
            if hasattr(original_item, "rect"):
                # Rectangle item
                from PySide6.QtWidgets import QGraphicsRectItem

                rect = original_item.rect()
                rect.translate(delta)
                preview = QGraphicsRectItem(rect)

            elif hasattr(original_item, "line"):
                # Line item
                from PySide6.QtWidgets import QGraphicsLineItem

                line = original_item.line()
                line.translate(delta)
                preview = QGraphicsLineItem(line)

            elif hasattr(original_item, "path"):
                # Path item
                from PySide6.QtWidgets import QGraphicsPathItem

                path = original_item.path()
                path.translate(delta)
                preview = QGraphicsPathItem(path)

            else:
                # Generic item - use bounding rect
                from PySide6.QtWidgets import QGraphicsRectItem

                rect = original_item.boundingRect()
                rect.translate(delta)
                preview = QGraphicsRectItem(rect)

            # Set preview appearance
            preview.setPen(self.preview_pen)
            preview.setOpacity(0.7)
            preview.setZValue(999)  # Below reference line but above normal items

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

        if self.reference_line and self.reference_line.scene():
            self.scene.removeItem(self.reference_line)
            self.reference_line = None

    async def _execute_move(self, destination_point: QPointF):
        """Execute the move operation."""
        if not self.base_point or not self.selected_items:
            return

        self.move_state = MoveState.MOVING

        try:
            # Calculate displacement
            delta = destination_point - self.base_point

            # Clear preview
            self._clear_preview()

            # Create move command
            from ...core.commands import MoveCommand

            # Get entity IDs from selected items
            entity_ids = []
            for item in self.selected_items:
                if hasattr(item, "entity_id"):
                    entity_ids.append(item.entity_id)

            if entity_ids:
                # Create and execute move command
                move_command = MoveCommand(
                    self.api_client, entity_ids, delta.x(), delta.y()
                )

                # Execute through command manager for undo support
                success = await self.command_manager.execute_command(move_command)

                if success:
                    # Emit completion signal
                    self.move_completed.emit(self.base_point, destination_point)

                    logger.info(
                        f"Moved {len(entity_ids)} objects by ({delta.x():.2f}, {delta.y():.2f})"
                    )

                    # Reset tool state
                    self._reset_tool()
                else:
                    logger.error("Move command execution failed")
                    self._cancel_move()
            else:
                logger.warning("No valid entities found for move operation")
                self._cancel_move()

        except Exception as e:
            logger.error(f"Error executing move: {e}")
            self._cancel_move()

    def _cancel_move(self):
        """Cancel the current move operation."""
        self._clear_preview()

        if self.move_state != MoveState.WAITING_FOR_SELECTION:
            self.move_state = (
                MoveState.WAITING_FOR_BASE_POINT
                if self.selected_items
                else MoveState.WAITING_FOR_SELECTION
            )

        self.base_point = None
        self.current_point = None

        # Emit cancellation signal
        self.move_cancelled.emit()

        logger.debug("Move operation cancelled")

    def _reset_tool(self):
        """Reset tool to initial state."""
        self.move_state = MoveState.WAITING_FOR_SELECTION
        self.base_point = None
        self.current_point = None
        self.selected_items.clear()

        # Clear selection
        self.selection_manager.clear_selection()

    def _get_current_distance(self) -> float:
        """Get current distance from base point to cursor."""
        if not self.base_point or not self.current_point:
            return 0.0

        delta = self.current_point - self.base_point
        return (delta.x() ** 2 + delta.y() ** 2) ** 0.5

    def selection_changed(self, selected_items: List[QGraphicsItem]):
        """Handle selection changes."""
        if self.move_state == MoveState.WAITING_FOR_SELECTION and selected_items:
            self.selected_items = selected_items
            self.move_state = MoveState.WAITING_FOR_BASE_POINT
            logger.debug(f"Move tool updated with {len(selected_items)} selected items")

    def get_tool_info(self) -> Dict[str, Any]:
        """Get current tool information."""
        return {
            **super().get_tool_info(),
            "move_state": self.move_state.name,
            "base_point": {"x": self.base_point.x(), "y": self.base_point.y()}
            if self.base_point
            else None,
            "current_point": {"x": self.current_point.x(), "y": self.current_point.y()}
            if self.current_point
            else None,
            "selected_count": len(self.selected_items),
            "distance": self._get_current_distance(),
        }
