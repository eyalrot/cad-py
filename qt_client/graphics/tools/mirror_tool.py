"""
Mirror tool for CAD drawing operations.

This module provides an interactive mirror tool that allows users to mirror
selected geometry across a reflection line with real-time preview.
"""

import asyncio
import logging
import math
from enum import Enum, auto
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QLineF, QPointF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPen, QTransform
from PySide6.QtWidgets import QGraphicsItem, QGraphicsLineItem

from ...core.selection_manager import SelectionManager
from .base_tool import BaseTool, ToolState

logger = logging.getLogger(__name__)


class MirrorState(Enum):
    """States for mirror tool operation."""

    WAITING_FOR_SELECTION = auto()
    WAITING_FOR_FIRST_POINT = auto()
    WAITING_FOR_SECOND_POINT = auto()
    MIRRORING = auto()
    COMPLETED = auto()


class MirrorMode(Enum):
    """Mirror modes."""

    COPY = auto()  # Create mirrored copy, keep original
    MOVE = auto()  # Mirror and delete original


class MirrorTool(BaseTool):
    """
    Interactive mirror tool for mirroring selected geometry.

    Features:
    - Mirror selected objects across a user-defined reflection line
    - Copy or move mode (keep original or replace)
    - Real-time preview during mirror operation
    - Snap integration for precise mirror line placement
    - Visual feedback with mirror line and preview
    - Undo/redo support through command pattern
    """

    # Signals
    mirror_started = Signal(QPointF)  # first point of mirror line
    mirror_preview = Signal(QPointF, QPointF)  # first point, second point
    mirror_completed = Signal(QPointF, QPointF, bool)  # first, second, copy_mode
    mirror_cancelled = Signal()

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
        self.mirror_state = MirrorState.WAITING_FOR_SELECTION
        self.mirror_mode = MirrorMode.COPY  # Default to copy mode

        # Mirror operation data
        self.first_point: Optional[QPointF] = None
        self.second_point: Optional[QPointF] = None
        self.current_point: Optional[QPointF] = None
        self.selected_items: List[QGraphicsItem] = []

        # Mirror line calculations
        self.mirror_line: Optional[QLineF] = None

        # Preview graphics
        self.preview_items: List[QGraphicsItem] = []
        self.mirror_line_item: Optional[QGraphicsLineItem] = None

        # Visual properties
        self.preview_pen = QPen(QColor(100, 255, 255, 180))  # Cyan for mirror
        self.preview_pen.setWidth(1)
        self.preview_pen.setStyle(Qt.DashLine)

        self.mirror_line_pen = QPen(QColor(255, 150, 0, 200))  # Orange mirror line
        self.mirror_line_pen.setWidth(2)
        self.mirror_line_pen.setStyle(Qt.DashDotLine)

        logger.debug("Mirror tool initialized")

    def get_tool_name(self) -> str:
        """Get tool display name."""
        mode_text = "Copy" if self.mirror_mode == MirrorMode.COPY else "Move"
        return f"Mirror ({mode_text})"

    def get_status_text(self) -> str:
        """Get current status text."""
        if self.mirror_state == MirrorState.WAITING_FOR_SELECTION:
            return "Select objects to mirror"
        elif self.mirror_state == MirrorState.WAITING_FOR_FIRST_POINT:
            return "Select first point of mirror line"
        elif self.mirror_state == MirrorState.WAITING_FOR_SECOND_POINT:
            return "Select second point of mirror line"
        elif self.mirror_state == MirrorState.MIRRORING:
            return "Mirroring objects..."
        else:
            return "Mirror tool ready"

    def activate(self) -> bool:
        """Activate the mirror tool."""
        if not super().activate():
            return False

        # Check if there are selected objects
        if self.selection_manager.has_selection():
            self.selected_items = list(self.selection_manager.get_selected_items())
            self.mirror_state = MirrorState.WAITING_FOR_FIRST_POINT
            logger.debug(
                f"Mirror tool activated with {len(self.selected_items)} selected items"
            )
        else:
            self.mirror_state = MirrorState.WAITING_FOR_SELECTION
            logger.debug("Mirror tool activated, waiting for selection")

        return True

    def deactivate(self):
        """Deactivate the mirror tool."""
        self._clear_preview()
        self.mirror_state = MirrorState.WAITING_FOR_SELECTION
        self.first_point = None
        self.second_point = None
        self.current_point = None
        self.selected_items.clear()
        self.mirror_line = None

        super().deactivate()
        logger.debug("Mirror tool deactivated")

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        """Handle mouse press events."""
        world_pos = self.scene_pos_from_event(event)

        # Apply snapping
        snap_result = self.snap_engine.snap_point(world_pos, self.view)
        if snap_result.snapped:
            world_pos = snap_result.point

        if self.mirror_state == MirrorState.WAITING_FOR_SELECTION:
            # Let selection manager handle the click
            return False

        elif self.mirror_state == MirrorState.WAITING_FOR_FIRST_POINT:
            self._set_first_point(world_pos)
            return True

        elif self.mirror_state == MirrorState.WAITING_FOR_SECOND_POINT:
            self._execute_mirror(world_pos)
            return True

        return False

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        """Handle mouse move events."""
        if self.mirror_state != MirrorState.WAITING_FOR_SECOND_POINT:
            return False

        world_pos = self.scene_pos_from_event(event)

        # Apply snapping
        snap_result = self.snap_engine.snap_point(
            world_pos, self.view, self.first_point
        )
        if snap_result.snapped:
            world_pos = snap_result.point

        self._update_mirror_preview(world_pos)
        return True

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle key press events."""
        if event.key() == Qt.Key_Escape:
            self._cancel_mirror()
            return True
        elif event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            if (
                self.mirror_state == MirrorState.WAITING_FOR_SECOND_POINT
                and self.current_point
            ):
                self._execute_mirror(self.current_point)
                return True
        elif event.key() == Qt.Key_C and event.modifiers() & Qt.ControlModifier:
            # Toggle copy/move mode
            self._toggle_mirror_mode()
            return True

        return super().handle_key_press(event)

    def _set_first_point(self, point: QPointF):
        """Set the first point of the mirror line."""
        self.first_point = point
        self.mirror_state = MirrorState.WAITING_FOR_SECOND_POINT

        # Create initial mirror line
        self._create_mirror_line()

        # Emit signal
        self.mirror_started.emit(self.first_point)

        logger.debug(f"Mirror first point set to ({point.x():.2f}, {point.y():.2f})")

    def _update_mirror_preview(self, current_point: QPointF):
        """Update the mirror preview."""
        if not self.first_point:
            return

        self.current_point = current_point
        self.second_point = current_point

        # Update mirror line
        self.mirror_line = QLineF(self.first_point, self.second_point)

        if self.mirror_line_item:
            self.mirror_line_item.setLine(self.mirror_line)

        # Update preview items
        self._update_preview_items()

        # Emit signal
        self.mirror_preview.emit(self.first_point, self.second_point)

    def _create_mirror_line(self):
        """Create the mirror line graphic."""
        if self.mirror_line_item:
            self.scene.removeItem(self.mirror_line_item)

        self.mirror_line_item = QGraphicsLineItem()
        self.mirror_line_item.setPen(self.mirror_line_pen)
        self.mirror_line_item.setZValue(1000)  # Draw on top
        self.scene.addItem(self.mirror_line_item)

    def _update_preview_items(self):
        """Update preview items showing mirrored positions."""
        if not self.mirror_line or self.mirror_line.length() < 0.001:
            self._clear_preview_items()
            return

        # Remove existing preview items
        self._clear_preview_items()

        # Calculate mirror transform
        transform = self._calculate_mirror_transform()

        if transform:
            # Create preview items for each selected item
            for item in self.selected_items:
                preview_item = self._create_preview_item(item, transform)
                if preview_item:
                    self.preview_items.append(preview_item)
                    self.scene.addItem(preview_item)

    def _calculate_mirror_transform(self) -> Optional[QTransform]:
        """Calculate the mirror transformation matrix."""
        if not self.mirror_line or self.mirror_line.length() < 0.001:
            return None

        # Get mirror line parameters
        p1 = self.mirror_line.p1()
        p2 = self.mirror_line.p2()

        # Calculate line direction and normal
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = math.sqrt(dx * dx + dy * dy)

        if length < 0.001:
            return None

        # Normalize direction vector
        ux = dx / length
        uy = dy / length

        # Mirror transformation matrix
        # For a line passing through (px, py) with unit direction (ux, uy),
        # the mirror matrix is: M = I - 2 * n * n^T where n is the normal
        # Normal vector is (-uy, ux)
        nx = -uy
        ny = ux

        # Mirror matrix components
        m11 = 1 - 2 * nx * nx
        m12 = -2 * nx * ny
        m21 = -2 * ny * nx
        m22 = 1 - 2 * ny * ny

        # Translation component for line not passing through origin
        # We need to translate to line, mirror, and translate back
        px = p1.x()
        py = p1.y()

        # Calculate the translation needed
        tx = 2 * (nx * (nx * px + ny * py))
        ty = 2 * (ny * (nx * px + ny * py))

        # Create transform
        transform = QTransform(m11, m12, m21, m22, tx, ty)

        return transform

    def _create_preview_item(
        self, original_item: QGraphicsItem, transform: QTransform
    ) -> Optional[QGraphicsItem]:
        """Create a preview item for the given original item."""
        try:
            # Clone the item's geometry with mirror transformation
            if hasattr(original_item, "rect"):
                # Rectangle item
                from PySide6.QtWidgets import QGraphicsRectItem

                rect = original_item.rect()

                # Transform the rectangle corners
                corners = [
                    rect.topLeft(),
                    rect.topRight(),
                    rect.bottomLeft(),
                    rect.bottomRight(),
                ]
                transformed_corners = [transform.map(corner) for corner in corners]

                # Find bounding rect of transformed corners
                xs = [p.x() for p in transformed_corners]
                ys = [p.y() for p in transformed_corners]
                new_rect = QRectF(
                    min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
                )

                preview = QGraphicsRectItem(new_rect)

            elif hasattr(original_item, "line"):
                # Line item
                from PySide6.QtWidgets import QGraphicsLineItem

                line = original_item.line()

                # Transform line endpoints
                p1_transformed = transform.map(line.p1())
                p2_transformed = transform.map(line.p2())
                transformed_line = QLineF(p1_transformed, p2_transformed)

                preview = QGraphicsLineItem(transformed_line)

            elif hasattr(original_item, "path"):
                # Path item
                from PySide6.QtWidgets import QGraphicsPathItem

                path = original_item.path()
                transformed_path = transform.map(path)
                preview = QGraphicsPathItem(transformed_path)

            else:
                # Generic item - transform bounding rect
                from PySide6.QtWidgets import QGraphicsRectItem

                rect = original_item.boundingRect()

                # Transform corners and find new bounding rect
                corners = [
                    rect.topLeft(),
                    rect.topRight(),
                    rect.bottomLeft(),
                    rect.bottomRight(),
                ]
                transformed_corners = [transform.map(corner) for corner in corners]

                xs = [p.x() for p in transformed_corners]
                ys = [p.y() for p in transformed_corners]
                new_rect = QRectF(
                    min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
                )

                preview = QGraphicsRectItem(new_rect)

            # Set preview appearance
            preview.setPen(self.preview_pen)
            preview.setOpacity(0.7)
            preview.setZValue(999)

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

        if self.mirror_line_item and self.mirror_line_item.scene():
            self.scene.removeItem(self.mirror_line_item)
            self.mirror_line_item = None

    def _toggle_mirror_mode(self):
        """Toggle between copy and move modes."""
        if self.mirror_mode == MirrorMode.COPY:
            self.mirror_mode = MirrorMode.MOVE
        else:
            self.mirror_mode = MirrorMode.COPY

        logger.debug(f"Mirror mode changed to {self.mirror_mode.name}")

    async def _execute_mirror(self, second_point: QPointF):
        """Execute the mirror operation."""
        if not self.first_point or not self.selected_items:
            return

        # Update final mirror line
        self._update_mirror_preview(second_point)

        self.mirror_state = MirrorState.MIRRORING

        try:
            # Clear preview
            self._clear_preview()

            # Create mirror command
            from ...core.commands import MirrorCommand

            # Get entity IDs from selected items
            entity_ids = []
            for item in self.selected_items:
                if hasattr(item, "entity_id"):
                    entity_ids.append(item.entity_id)

            if entity_ids and self.mirror_line:
                # Create and execute mirror command
                copy_mode = self.mirror_mode == MirrorMode.COPY

                mirror_command = MirrorCommand(
                    self.api_client,
                    entity_ids,
                    self.first_point.x(),
                    self.first_point.y(),
                    self.second_point.x(),
                    self.second_point.y(),
                    copy_mode,
                )

                # Execute through command manager for undo support
                success = await self.command_manager.execute_command(mirror_command)

                if success:
                    # Emit completion signal
                    self.mirror_completed.emit(
                        self.first_point, self.second_point, copy_mode
                    )

                    action = "Mirrored (copy)" if copy_mode else "Mirrored (move)"
                    logger.info(f"{action} {len(entity_ids)} objects")

                    # Reset tool state
                    self._reset_tool()
                else:
                    logger.error("Mirror command execution failed")
                    self._cancel_mirror()
            else:
                logger.warning("No valid entities found for mirror operation")
                self._cancel_mirror()

        except Exception as e:
            logger.error(f"Error executing mirror: {e}")
            self._cancel_mirror()

    def _cancel_mirror(self):
        """Cancel the current mirror operation."""
        self._clear_preview()

        if self.mirror_state != MirrorState.WAITING_FOR_SELECTION:
            self.mirror_state = (
                MirrorState.WAITING_FOR_FIRST_POINT
                if self.selected_items
                else MirrorState.WAITING_FOR_SELECTION
            )

        self.first_point = None
        self.second_point = None
        self.current_point = None
        self.mirror_line = None

        # Emit cancellation signal
        self.mirror_cancelled.emit()

        logger.debug("Mirror operation cancelled")

    def _reset_tool(self):
        """Reset tool to initial state."""
        self.mirror_state = MirrorState.WAITING_FOR_SELECTION
        self.first_point = None
        self.second_point = None
        self.current_point = None
        self.selected_items.clear()
        self.mirror_line = None

        # Clear selection
        self.selection_manager.clear_selection()

    def selection_changed(self, selected_items: List[QGraphicsItem]):
        """Handle selection changes."""
        if self.mirror_state == MirrorState.WAITING_FOR_SELECTION and selected_items:
            self.selected_items = selected_items
            self.mirror_state = MirrorState.WAITING_FOR_FIRST_POINT
            logger.debug(
                f"Mirror tool updated with {len(selected_items)} selected items"
            )

    def get_tool_info(self) -> Dict[str, Any]:
        """Get current tool information."""
        return {
            **super().get_tool_info(),
            "mirror_state": self.mirror_state.name,
            "mirror_mode": self.mirror_mode.name,
            "first_point": {"x": self.first_point.x(), "y": self.first_point.y()}
            if self.first_point
            else None,
            "second_point": {"x": self.second_point.x(), "y": self.second_point.y()}
            if self.second_point
            else None,
            "mirror_line_length": self.mirror_line.length()
            if self.mirror_line
            else 0.0,
            "selected_count": len(self.selected_items),
            "copy_mode": self.mirror_mode == MirrorMode.COPY,
        }
