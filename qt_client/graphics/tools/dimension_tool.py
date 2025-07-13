"""
Base dimension tool for CAD drawing operations.

This module provides the base functionality for creating linear dimensions
including horizontal, vertical, and aligned dimensions.
"""

import asyncio
import logging
import math
from enum import Enum, auto
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPainterPath, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsTextItem,
)

from ...core.selection_manager import SelectionManager
from .base_tool import BaseTool, ToolState

logger = logging.getLogger(__name__)


class DimensionType(Enum):
    """Types of dimensions."""

    HORIZONTAL = auto()
    VERTICAL = auto()
    ALIGNED = auto()
    ANGULAR = auto()
    RADIUS = auto()
    DIAMETER = auto()
    ARC_LENGTH = auto()


class DimensionState(Enum):
    """States for dimension tool operation."""

    WAITING_FOR_FIRST_POINT = auto()
    WAITING_FOR_SECOND_POINT = auto()
    WAITING_FOR_DIMENSION_LINE = auto()
    CREATING = auto()
    COMPLETED = auto()


class DimensionStyle:
    """Style settings for dimensions."""

    def __init__(self):
        self.text_height = 2.5
        self.text_color = QColor(0, 0, 0)  # Black
        self.text_font = QFont("Arial", 10)

        self.arrow_size = 2.5
        self.line_color = QColor(0, 0, 0)  # Black
        self.line_weight = 1.0

        self.extension_line_offset = 1.25
        self.extension_line_extension = 1.25
        self.dimension_line_gap = 0.625

        self.precision = 2
        self.unit_suffix = ""
        self.scale_factor = 1.0


class DimensionGraphics:
    """Graphics items for dimension display."""

    def __init__(self, scene, style: DimensionStyle):
        self.scene = scene
        self.style = style
        self.items: List[QGraphicsItem] = []

        # Pens for drawing
        self.line_pen = QPen(style.line_color, style.line_weight)
        self.preview_pen = QPen(QColor(100, 150, 255, 180), 1, Qt.PenStyle.DashLine)

    def clear(self):
        """Remove all graphics items from scene."""
        for item in self.items:
            if item.scene():
                self.scene.removeItem(item)
        self.items.clear()

    def create_dimension_graphics(
        self,
        point1: QPointF,
        point2: QPointF,
        dim_line_pos: QPointF,
        dim_type: DimensionType,
        is_preview: bool = False,
    ):
        """Create complete dimension graphics."""
        self.clear()

        pen = self.preview_pen if is_preview else self.line_pen

        # Calculate dimension value
        if dim_type == DimensionType.HORIZONTAL:
            measurement = abs(point2.x() - point1.x())
            # Adjust dimension line position to be horizontal
            dim_line_y = dim_line_pos.y()
            dim_start = QPointF(min(point1.x(), point2.x()), dim_line_y)
            dim_end = QPointF(max(point1.x(), point2.x()), dim_line_y)

            # Extension lines
            ext1_start = QPointF(point1.x(), point1.y())
            ext1_end = QPointF(
                point1.x(), dim_line_y + self.style.extension_line_extension
            )
            ext2_start = QPointF(point2.x(), point2.y())
            ext2_end = QPointF(
                point2.x(), dim_line_y + self.style.extension_line_extension
            )

        elif dim_type == DimensionType.VERTICAL:
            measurement = abs(point2.y() - point1.y())
            # Adjust dimension line position to be vertical
            dim_line_x = dim_line_pos.x()
            dim_start = QPointF(dim_line_x, min(point1.y(), point2.y()))
            dim_end = QPointF(dim_line_x, max(point1.y(), point2.y()))

            # Extension lines
            ext1_start = QPointF(point1.x(), point1.y())
            ext1_end = QPointF(
                dim_line_x + self.style.extension_line_extension, point1.y()
            )
            ext2_start = QPointF(point2.x(), point2.y())
            ext2_end = QPointF(
                dim_line_x + self.style.extension_line_extension, point2.y()
            )

        else:  # ALIGNED
            measurement = math.sqrt(
                (point2.x() - point1.x()) ** 2 + (point2.y() - point1.y()) ** 2
            )

            # Calculate aligned dimension line
            direction = QPointF(point2.x() - point1.x(), point2.y() - point1.y())
            length = math.sqrt(direction.x() ** 2 + direction.y() ** 2)
            if length > 0:
                unit_dir = QPointF(direction.x() / length, direction.y() / length)

                # Perpendicular vector for offset
                perp = QPointF(-unit_dir.y(), unit_dir.x())

                # Calculate offset distance from dimension line position
                to_dim_line = QPointF(
                    dim_line_pos.x() - point1.x(), dim_line_pos.y() - point1.y()
                )
                offset_distance = (
                    perp.x() * to_dim_line.x() + perp.y() * to_dim_line.y()
                )

                offset = QPointF(perp.x() * offset_distance, perp.y() * offset_distance)
                dim_start = QPointF(point1.x() + offset.x(), point1.y() + offset.y())
                dim_end = QPointF(point2.x() + offset.x(), point2.y() + offset.y())

                # Extension lines
                ext_offset = QPointF(
                    perp.x() * self.style.extension_line_extension,
                    perp.y() * self.style.extension_line_extension,
                )
                ext1_start = point1
                ext1_end = QPointF(
                    dim_start.x() + ext_offset.x(), dim_start.y() + ext_offset.y()
                )
                ext2_start = point2
                ext2_end = QPointF(
                    dim_end.x() + ext_offset.x(), dim_end.y() + ext_offset.y()
                )
            else:
                dim_start = point1
                dim_end = point2
                ext1_start = ext1_end = point1
                ext2_start = ext2_end = point2

        # Create extension lines
        ext1_line = QGraphicsLineItem(
            ext1_start.x(), ext1_start.y(), ext1_end.x(), ext1_end.y()
        )
        ext1_line.setPen(pen)
        ext1_line.setZValue(998)
        self.scene.addItem(ext1_line)
        self.items.append(ext1_line)

        ext2_line = QGraphicsLineItem(
            ext2_start.x(), ext2_start.y(), ext2_end.x(), ext2_end.y()
        )
        ext2_line.setPen(pen)
        ext2_line.setZValue(998)
        self.scene.addItem(ext2_line)
        self.items.append(ext2_line)

        # Create dimension line
        dim_line = QGraphicsLineItem(
            dim_start.x(), dim_start.y(), dim_end.x(), dim_end.y()
        )
        dim_line.setPen(pen)
        dim_line.setZValue(999)
        self.scene.addItem(dim_line)
        self.items.append(dim_line)

        # Create arrows
        self._create_arrow(dim_start, dim_end, pen, True)
        self._create_arrow(dim_end, dim_start, pen, True)

        # Create dimension text
        text = self._format_measurement(measurement)
        text_item = QGraphicsTextItem(text)
        text_item.setFont(self.style.text_font)
        text_item.setDefaultTextColor(self.style.text_color)

        # Position text at center of dimension line
        text_center = QPointF(
            (dim_start.x() + dim_end.x()) / 2, (dim_start.y() + dim_end.y()) / 2
        )
        text_rect = text_item.boundingRect()
        text_item.setPos(
            text_center.x() - text_rect.width() / 2,
            text_center.y() - text_rect.height() / 2,
        )
        text_item.setZValue(1000)

        self.scene.addItem(text_item)
        self.items.append(text_item)

    def _create_arrow(
        self, start: QPointF, end: QPointF, pen: QPen, filled: bool = True
    ):
        """Create an arrow at the start point pointing toward end point."""
        # Calculate arrow direction
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        length = math.sqrt(dx * dx + dy * dy)

        if length == 0:
            return

        # Normalize direction
        dx /= length
        dy /= length

        # Arrow geometry
        arrow_length = self.style.arrow_size
        arrow_width = self.style.arrow_size * 0.3

        # Arrow points
        tip = start
        base1 = QPointF(
            start.x() - dx * arrow_length + dy * arrow_width,
            start.y() - dy * arrow_length - dx * arrow_width,
        )
        base2 = QPointF(
            start.x() - dx * arrow_length - dy * arrow_width,
            start.y() - dy * arrow_length + dx * arrow_width,
        )

        # Create arrow path
        arrow_path = QPainterPath()
        arrow_path.moveTo(tip)
        arrow_path.lineTo(base1)
        arrow_path.lineTo(base2)
        arrow_path.closeSubpath()

        # Create arrow graphics item
        arrow_item = QGraphicsPathItem(arrow_path)
        arrow_item.setPen(pen)

        if filled:
            brush = pen.brush()
            brush.setColor(pen.color())
            brush.setStyle(Qt.BrushStyle.SolidPattern)
            arrow_item.setBrush(brush)

        arrow_item.setZValue(999)
        self.scene.addItem(arrow_item)
        self.items.append(arrow_item)

    def _format_measurement(self, value: float) -> str:
        """Format measurement value according to style."""
        scaled_value = value * self.style.scale_factor
        formatted = f"{scaled_value:.{self.style.precision}f}"

        # Remove trailing zeros if needed
        if "." in formatted:
            formatted = formatted.rstrip("0").rstrip(".")

        return formatted + self.style.unit_suffix


class BaseDimensionTool(BaseTool):
    """
    Base class for dimension tools.

    Provides common functionality for creating linear dimensions with
    proper geometric calculations and visual feedback.
    """

    # Signals
    dimension_created = Signal(dict)  # dimension_data
    dimension_cancelled = Signal()

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
        self.dimension_type = DimensionType.HORIZONTAL  # Override in subclasses
        self.dimension_state = DimensionState.WAITING_FOR_FIRST_POINT

        # Dimension data
        self.first_point: Optional[QPointF] = None
        self.second_point: Optional[QPointF] = None
        self.dimension_line_position: Optional[QPointF] = None

        # Graphics
        self.dimension_style = DimensionStyle()
        self.dimension_graphics = DimensionGraphics(scene, self.dimension_style)

        # Preview graphics
        self.preview_line: Optional[QGraphicsLineItem] = None

        logger.debug(f"Base dimension tool initialized for {self.dimension_type}")

    def get_tool_name(self) -> str:
        """Get tool display name."""
        return f"{self.dimension_type.name.title()} Dimension"

    def get_status_text(self) -> str:
        """Get current status text."""
        if self.dimension_state == DimensionState.WAITING_FOR_FIRST_POINT:
            return "Select first dimension point"
        elif self.dimension_state == DimensionState.WAITING_FOR_SECOND_POINT:
            return "Select second dimension point"
        elif self.dimension_state == DimensionState.WAITING_FOR_DIMENSION_LINE:
            return "Click to place dimension line"
        elif self.dimension_state == DimensionState.CREATING:
            return "Creating dimension..."
        else:
            return "Dimension tool ready"

    def activate(self) -> bool:
        """Activate the dimension tool."""
        if not super().activate():
            return False

        self.dimension_state = DimensionState.WAITING_FOR_FIRST_POINT
        self._clear_dimension_data()

        logger.debug(f"{self.get_tool_name()} activated")
        return True

    def deactivate(self):
        """Deactivate the dimension tool."""
        self._clear_preview()
        self.dimension_graphics.clear()
        self._clear_dimension_data()

        super().deactivate()
        logger.debug(f"{self.get_tool_name()} deactivated")

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        """Handle mouse press events."""
        world_pos = self.scene_pos_from_event(event)

        # Apply snapping
        snap_result = self.snap_engine.snap_point(world_pos, self.view)
        if snap_result.snapped:
            world_pos = snap_result.point

        if self.dimension_state == DimensionState.WAITING_FOR_FIRST_POINT:
            self._set_first_point(world_pos)
            return True

        elif self.dimension_state == DimensionState.WAITING_FOR_SECOND_POINT:
            self._set_second_point(world_pos)
            return True

        elif self.dimension_state == DimensionState.WAITING_FOR_DIMENSION_LINE:
            self._set_dimension_line_position(world_pos)
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
            self.dimension_state == DimensionState.WAITING_FOR_SECOND_POINT
            and self.first_point
        ):
            self._update_second_point_preview(world_pos)
            return True

        elif (
            self.dimension_state == DimensionState.WAITING_FOR_DIMENSION_LINE
            and self.first_point
            and self.second_point
        ):
            self._update_dimension_line_preview(world_pos)
            return True

        return False

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Escape:
            self._cancel_dimension()
            return True
        elif event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
            if self.dimension_state == DimensionState.WAITING_FOR_DIMENSION_LINE:
                # Use current mouse position for dimension line
                cursor_pos = self.view.mapFromGlobal(self.view.cursor().pos())
                world_pos = self.view.mapToScene(cursor_pos)
                self._set_dimension_line_position(world_pos)
                return True

        return super().handle_key_press(event)

    def _set_first_point(self, point: QPointF):
        """Set the first dimension point."""
        self.first_point = point
        self.dimension_state = DimensionState.WAITING_FOR_SECOND_POINT
        logger.debug(f"First dimension point set: ({point.x():.2f}, {point.y():.2f})")

    def _set_second_point(self, point: QPointF):
        """Set the second dimension point."""
        self.second_point = point
        self.dimension_state = DimensionState.WAITING_FOR_DIMENSION_LINE
        self._clear_preview()
        logger.debug(f"Second dimension point set: ({point.x():.2f}, {point.y():.2f})")

    def _set_dimension_line_position(self, point: QPointF):
        """Set the dimension line position and create dimension."""
        self.dimension_line_position = point
        self.dimension_state = DimensionState.CREATING

        # Create the dimension
        asyncio.create_task(self._create_dimension())

        logger.debug(f"Dimension line position set: ({point.x():.2f}, {point.y():.2f})")

    def _update_second_point_preview(self, point: QPointF):
        """Update preview for second point selection."""
        if not self.first_point:
            return

        self._clear_preview()

        # Create preview line between first point and current position
        self.preview_line = QGraphicsLineItem(
            self.first_point.x(), self.first_point.y(), point.x(), point.y()
        )
        self.preview_line.setPen(
            QPen(QColor(100, 150, 255, 180), 1, Qt.PenStyle.DashLine)
        )
        self.preview_line.setZValue(997)
        self.scene.addItem(self.preview_line)

    def _update_dimension_line_preview(self, dim_line_pos: QPointF):
        """Update preview for dimension line positioning."""
        if not self.first_point or not self.second_point:
            return

        # Show preview of complete dimension
        self.dimension_graphics.create_dimension_graphics(
            self.first_point,
            self.second_point,
            dim_line_pos,
            self.dimension_type,
            is_preview=True,
        )

    async def _create_dimension(self):
        """Create the dimension entity."""
        if (
            not self.first_point
            or not self.second_point
            or not self.dimension_line_position
        ):
            return

        try:
            # Prepare dimension data for API
            dimension_data = {
                "dimension_type": self.dimension_type.name.lower(),
                "points": [
                    [self.first_point.x(), self.first_point.y()],
                    [self.second_point.x(), self.second_point.y()],
                    [
                        self.dimension_line_position.x(),
                        self.dimension_line_position.y(),
                    ],
                ],
                "layer_id": "0",  # Use current layer
                "style_id": None,  # Use default style
            }

            # Create dimension via API if available
            if self.api_client:
                response = await self.api_client.create_dimension(dimension_data)
                if response.get("success", False):
                    logger.info(
                        f"Created {self.dimension_type.name.lower()} dimension via API"
                    )
                else:
                    logger.error(
                        f"Failed to create dimension: {response.get('error_message', 'Unknown error')}"
                    )

            # Create final dimension graphics
            self.dimension_graphics.create_dimension_graphics(
                self.first_point,
                self.second_point,
                self.dimension_line_position,
                self.dimension_type,
                is_preview=False,
            )

            # Emit signal
            self.dimension_created.emit(dimension_data)

            # Reset tool for next dimension
            self._reset_tool()

        except Exception as e:
            logger.error(f"Error creating dimension: {e}")
            self._cancel_dimension()

    def _cancel_dimension(self):
        """Cancel the current dimension operation."""
        self._clear_preview()
        self.dimension_graphics.clear()
        self._clear_dimension_data()

        self.dimension_state = DimensionState.WAITING_FOR_FIRST_POINT
        self.dimension_cancelled.emit()

        logger.debug("Dimension operation cancelled")

    def _reset_tool(self):
        """Reset tool for next dimension."""
        self._clear_dimension_data()
        self.dimension_state = DimensionState.WAITING_FOR_FIRST_POINT

    def _clear_dimension_data(self):
        """Clear all dimension data."""
        self.first_point = None
        self.second_point = None
        self.dimension_line_position = None

    def _clear_preview(self):
        """Clear preview graphics."""
        if self.preview_line and self.preview_line.scene():
            self.scene.removeItem(self.preview_line)
            self.preview_line = None

    def get_tool_info(self) -> Dict[str, Any]:
        """Get current tool information."""
        return {
            **super().get_tool_info(),
            "dimension_type": self.dimension_type.name,
            "dimension_state": self.dimension_state.name,
            "first_point": {"x": self.first_point.x(), "y": self.first_point.y()}
            if self.first_point
            else None,
            "second_point": {"x": self.second_point.x(), "y": self.second_point.y()}
            if self.second_point
            else None,
            "dimension_line_position": {
                "x": self.dimension_line_position.x(),
                "y": self.dimension_line_position.y(),
            }
            if self.dimension_line_position
            else None,
        }


class HorizontalDimensionTool(BaseDimensionTool):
    """Tool for creating horizontal dimensions."""

    def __init__(
        self, scene, api_client, command_manager, snap_engine, selection_manager
    ):
        super().__init__(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        self.dimension_type = DimensionType.HORIZONTAL


class VerticalDimensionTool(BaseDimensionTool):
    """Tool for creating vertical dimensions."""

    def __init__(
        self, scene, api_client, command_manager, snap_engine, selection_manager
    ):
        super().__init__(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        self.dimension_type = DimensionType.VERTICAL


class AlignedDimensionTool(BaseDimensionTool):
    """Tool for creating aligned dimensions."""

    def __init__(
        self, scene, api_client, command_manager, snap_engine, selection_manager
    ):
        super().__init__(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        self.dimension_type = DimensionType.ALIGNED


class AngularDimensionTool(BaseTool):
    """Tool for creating angular dimensions between two lines."""

    # Signals
    dimension_created = Signal(dict)
    dimension_cancelled = Signal()

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
        
        # States for angular dimension
        self.first_line = None
        self.second_line = None
        self.arc_point = None
        self.state = "waiting_for_first_line"
        
        # Graphics
        self.dimension_style = DimensionStyle()
        self.preview_items = []

    def get_tool_name(self) -> str:
        return "Angular Dimension"

    def get_status_text(self) -> str:
        if self.state == "waiting_for_first_line":
            return "Select first line for angular dimension"
        elif self.state == "waiting_for_second_line":
            return "Select second line for angular dimension"
        elif self.state == "waiting_for_arc_point":
            return "Click to position angular dimension arc"
        else:
            return "Angular dimension tool ready"

    def activate(self) -> bool:
        if not super().activate():
            return False
        self._reset_tool()
        return True

    def deactivate(self):
        self._clear_preview()
        super().deactivate()

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        world_pos = self.scene_pos_from_event(event)
        
        if self.state == "waiting_for_first_line":
            line_entity = self._find_line_at_point(world_pos)
            if line_entity:
                self.first_line = line_entity
                self.state = "waiting_for_second_line"
                return True
                
        elif self.state == "waiting_for_second_line":
            line_entity = self._find_line_at_point(world_pos)
            if line_entity and line_entity != self.first_line:
                self.second_line = line_entity
                self.state = "waiting_for_arc_point"
                return True
                
        elif self.state == "waiting_for_arc_point":
            self.arc_point = world_pos
            asyncio.create_task(self._create_angular_dimension())
            return True
            
        return False

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        world_pos = self.scene_pos_from_event(event)
        
        if self.state == "waiting_for_arc_point" and self.first_line and self.second_line:
            self._update_angular_preview(world_pos)
            return True
            
        return False

    def handle_key_press(self, event: QKeyEvent) -> bool:
        if event.key() == Qt.Key.Key_Escape:
            self._cancel_dimension()
            return True
        return super().handle_key_press(event)

    def _find_line_at_point(self, point: QPointF):
        """Find line entity near the clicked point."""
        # Get items near the click point
        items = self.scene.items(point, Qt.ItemSelectionMode.IntersectsItemBoundingRect)
        for item in items:
            if isinstance(item, QGraphicsLineItem):
                return item
        return None

    def _calculate_angle_between_lines(self, line1, line2):
        """Calculate angle between two lines."""
        # Get line vectors
        l1_start = line1.line().p1()
        l1_end = line1.line().p2()
        l2_start = line2.line().p1()
        l2_end = line2.line().p2()
        
        # Calculate direction vectors
        v1 = QPointF(l1_end.x() - l1_start.x(), l1_end.y() - l1_start.y())
        v2 = QPointF(l2_end.x() - l2_start.x(), l2_end.y() - l2_start.y())
        
        # Calculate angle using dot product
        dot_product = v1.x() * v2.x() + v1.y() * v2.y()
        mag1 = math.sqrt(v1.x() ** 2 + v1.y() ** 2)
        mag2 = math.sqrt(v2.x() ** 2 + v2.y() ** 2)
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
            
        cos_angle = dot_product / (mag1 * mag2)
        cos_angle = max(-1.0, min(1.0, cos_angle))  # Clamp to valid range
        angle_rad = math.acos(cos_angle)
        angle_deg = math.degrees(angle_rad)
        
        return angle_deg

    def _find_intersection_point(self, line1, line2):
        """Find intersection point of two lines."""
        l1 = line1.line()
        l2 = line2.line()
        
        # Line 1: (x1,y1) to (x2,y2)
        x1, y1 = l1.p1().x(), l1.p1().y()
        x2, y2 = l1.p2().x(), l1.p2().y()
        
        # Line 2: (x3,y3) to (x4,y4)
        x3, y3 = l2.p1().x(), l2.p1().y()
        x4, y4 = l2.p2().x(), l2.p2().y()
        
        # Calculate intersection
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:  # Lines are parallel
            return None
            
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        
        intersection_x = x1 + t * (x2 - x1)
        intersection_y = y1 + t * (y2 - y1)
        
        return QPointF(intersection_x, intersection_y)

    def _update_angular_preview(self, arc_point: QPointF):
        """Update preview of angular dimension."""
        self._clear_preview()
        
        if not self.first_line or not self.second_line:
            return
            
        # Find intersection point
        vertex = self._find_intersection_point(self.first_line, self.second_line)
        if not vertex:
            return
            
        # Calculate angle
        angle = self._calculate_angle_between_lines(self.first_line, self.second_line)
        
        # Calculate arc radius from vertex to arc_point
        radius = math.sqrt(
            (arc_point.x() - vertex.x()) ** 2 + (arc_point.y() - vertex.y()) ** 2
        )
        
        # Create arc preview
        self._create_angular_arc_graphics(vertex, radius, angle, True)

    def _create_angular_arc_graphics(self, vertex: QPointF, radius: float, angle: float, is_preview: bool = False):
        """Create graphics for angular dimension arc."""
        pen = QPen(QColor(100, 150, 255, 180), 1, Qt.PenStyle.DashLine) if is_preview else QPen(self.dimension_style.line_color, self.dimension_style.line_weight)
        
        # Create arc path
        arc_path = QPainterPath()
        arc_rect = QRectF(vertex.x() - radius, vertex.y() - radius, radius * 2, radius * 2)
        
        # Calculate start angle based on first line direction
        l1 = self.first_line.line()
        start_angle = math.degrees(math.atan2(l1.p2().y() - l1.p1().y(), l1.p2().x() - l1.p1().x()))
        
        # Draw arc
        arc_path.arcMoveTo(arc_rect, start_angle)
        arc_path.arcTo(arc_rect, start_angle, angle)
        
        # Create arc graphics item
        arc_item = QGraphicsPathItem(arc_path)
        arc_item.setPen(pen)
        arc_item.setZValue(999)
        self.scene.addItem(arc_item)
        self.preview_items.append(arc_item)
        
        # Add dimension text
        arc_center_angle = start_angle + angle / 2
        text_radius = radius + self.dimension_style.text_offset
        text_x = vertex.x() + text_radius * math.cos(math.radians(arc_center_angle))
        text_y = vertex.y() + text_radius * math.sin(math.radians(arc_center_angle))
        
        text_item = QGraphicsTextItem(f"{angle:.1f}°")
        text_item.setFont(self.dimension_style.text_font)
        text_item.setDefaultTextColor(self.dimension_style.text_color)
        text_item.setPos(text_x, text_y)
        text_item.setZValue(1000)
        self.scene.addItem(text_item)
        self.preview_items.append(text_item)

    async def _create_angular_dimension(self):
        """Create the angular dimension entity."""
        if not self.first_line or not self.second_line or not self.arc_point:
            return
            
        try:
            # Find intersection point
            vertex = self._find_intersection_point(self.first_line, self.second_line)
            if not vertex:
                logger.error("Cannot create angular dimension: lines do not intersect")
                return
                
            # Calculate angle and radius
            angle = self._calculate_angle_between_lines(self.first_line, self.second_line)
            radius = math.sqrt(
                (self.arc_point.x() - vertex.x()) ** 2 + (self.arc_point.y() - vertex.y()) ** 2
            )
            
            # Prepare dimension data
            dimension_data = {
                "dimension_type": "angular",
                "points": [
                    [vertex.x(), vertex.y()],  # Vertex point
                    [self.arc_point.x(), self.arc_point.y()],  # Arc position
                ],
                "measurement_value": angle,
                "layer_id": "0",
                "style_id": None,
            }
            
            # Create dimension via API if available
            if self.api_client:
                response = await self.api_client.create_dimension(dimension_data)
                if response.get("success", False):
                    logger.info("Created angular dimension via API")
                else:
                    logger.error(f"Failed to create angular dimension: {response.get('error_message', 'Unknown error')}")
            
            # Create final graphics
            self._create_angular_arc_graphics(vertex, radius, angle, False)
            
            # Emit signal
            self.dimension_created.emit(dimension_data)
            
            # Reset tool
            self._reset_tool()
            
        except Exception as e:
            logger.error(f"Error creating angular dimension: {e}")
            self._cancel_dimension()

    def _cancel_dimension(self):
        """Cancel angular dimension operation."""
        self._clear_preview()
        self._reset_tool()
        self.dimension_cancelled.emit()

    def _reset_tool(self):
        """Reset tool for next dimension."""
        self.first_line = None
        self.second_line = None
        self.arc_point = None
        self.state = "waiting_for_first_line"

    def _clear_preview(self):
        """Clear preview graphics."""
        for item in self.preview_items:
            if item.scene():
                self.scene.removeItem(item)
        self.preview_items.clear()


class ArcLengthDimensionTool(BaseTool):
    """Tool for creating arc length dimensions on arcs."""

    # Signals
    dimension_created = Signal(dict)
    dimension_cancelled = Signal()

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
        
        # State
        self.selected_arc = None
        self.text_position = None
        self.state = "waiting_for_arc"
        
        # Graphics
        self.dimension_style = DimensionStyle()
        self.preview_items = []

    def get_tool_name(self) -> str:
        return "Arc Length Dimension"

    def get_status_text(self) -> str:
        if self.state == "waiting_for_arc":
            return "Select arc for arc length dimension"
        elif self.state == "waiting_for_position":
            return "Click to position arc length dimension text"
        else:
            return "Arc length dimension tool ready"

    def activate(self) -> bool:
        if not super().activate():
            return False
        self._reset_tool()
        return True

    def deactivate(self):
        self._clear_preview()
        super().deactivate()

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        world_pos = self.scene_pos_from_event(event)
        
        if self.state == "waiting_for_arc":
            arc_entity = self._find_arc_entity_at_point(world_pos)
            if arc_entity:
                self.selected_arc = arc_entity
                self.state = "waiting_for_position"
                return True
                
        elif self.state == "waiting_for_position":
            self.text_position = world_pos
            asyncio.create_task(self._create_arc_length_dimension())
            return True
            
        return False

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        world_pos = self.scene_pos_from_event(event)
        
        if self.state == "waiting_for_position" and self.selected_arc:
            self._update_arc_length_preview(world_pos)
            return True
            
        return False

    def handle_key_press(self, event: QKeyEvent) -> bool:
        if event.key() == Qt.Key.Key_Escape:
            self._cancel_dimension()
            return True
        return super().handle_key_press(event)

    def _find_arc_entity_at_point(self, point: QPointF):
        """Find arc entity near the clicked point."""
        items = self.scene.items(point, Qt.ItemSelectionMode.IntersectsItemBoundingRect)
        for item in items:
            # Check if item represents an arc
            if hasattr(item, 'entity_type') and item.entity_type == 'arc':
                return item
        return None

    def _get_arc_properties(self, arc_entity):
        """Get center, radius, start_angle, end_angle from arc entity."""
        # This would interface with your actual entity system
        # For demo purposes, providing fallback values
        if hasattr(arc_entity, 'center') and hasattr(arc_entity, 'radius'):
            center = arc_entity.center
            radius = arc_entity.radius
            start_angle = getattr(arc_entity, 'start_angle', 0.0)  # degrees
            end_angle = getattr(arc_entity, 'end_angle', 90.0)    # degrees
            return center, radius, start_angle, end_angle
        return QPointF(0, 0), 10.0, 0.0, 90.0  # Fallback values

    def _calculate_arc_length(self, radius: float, start_angle: float, end_angle: float) -> float:
        """Calculate arc length from radius and angle span."""
        # Convert angles to radians
        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)
        
        # Calculate angle span (handle wraparound)
        angle_span = end_rad - start_rad
        if angle_span < 0:
            angle_span += 2 * math.pi
            
        # Arc length = radius * angle (in radians)
        return radius * angle_span

    def _update_arc_length_preview(self, text_pos: QPointF):
        """Update preview of arc length dimension."""
        self._clear_preview()
        
        if not self.selected_arc:
            return
            
        center, radius, start_angle, end_angle = self._get_arc_properties(self.selected_arc)
        arc_length = self._calculate_arc_length(radius, start_angle, end_angle)
        
        # Calculate midpoint of arc for dimension line
        mid_angle = math.radians((start_angle + end_angle) / 2)
        arc_midpoint = QPointF(
            center.x() + radius * math.cos(mid_angle),
            center.y() + radius * math.sin(mid_angle)
        )
        
        # Create dimension line from arc midpoint to text position
        dim_line = QGraphicsLineItem(
            arc_midpoint.x(), arc_midpoint.y(), 
            text_pos.x(), text_pos.y()
        )
        dim_line.setPen(QPen(QColor(100, 150, 255, 180), 1, Qt.PenStyle.DashLine))
        dim_line.setZValue(999)
        self.scene.addItem(dim_line)
        self.preview_items.append(dim_line)
        
        # Create arc length text with arc symbol
        text_item = QGraphicsTextItem(f"⌒{arc_length:.2f}")
        text_item.setFont(self.dimension_style.text_font)
        text_item.setDefaultTextColor(self.dimension_style.text_color)
        text_item.setPos(text_pos.x(), text_pos.y())
        text_item.setZValue(1000)
        self.scene.addItem(text_item)
        self.preview_items.append(text_item)
        
        # Highlight the arc portion being measured
        arc_path = QPainterPath()
        arc_rect = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        arc_path.arcMoveTo(arc_rect, start_angle)
        arc_path.arcTo(arc_rect, start_angle, end_angle - start_angle)
        
        arc_highlight = QGraphicsPathItem(arc_path)
        arc_highlight.setPen(QPen(QColor(255, 100, 100, 200), 2))
        arc_highlight.setZValue(998)
        self.scene.addItem(arc_highlight)
        self.preview_items.append(arc_highlight)

    async def _create_arc_length_dimension(self):
        """Create the arc length dimension entity."""
        if not self.selected_arc or not self.text_position:
            return
            
        try:
            center, radius, start_angle, end_angle = self._get_arc_properties(self.selected_arc)
            arc_length = self._calculate_arc_length(radius, start_angle, end_angle)
            
            # Calculate midpoint of arc
            mid_angle = math.radians((start_angle + end_angle) / 2)
            arc_midpoint = QPointF(
                center.x() + radius * math.cos(mid_angle),
                center.y() + radius * math.sin(mid_angle)
            )
            
            # Prepare dimension data
            dimension_data = {
                "dimension_type": "arc_length",
                "points": [
                    [center.x(), center.y()],  # Arc center
                    [arc_midpoint.x(), arc_midpoint.y()],  # Arc midpoint
                    [self.text_position.x(), self.text_position.y()],  # Text position
                ],
                "measurement_value": arc_length,
                "properties": {
                    "radius": radius,
                    "start_angle": start_angle,
                    "end_angle": end_angle
                },
                "layer_id": "0",
                "style_id": None,
            }
            
            # Create dimension via API if available
            if self.api_client:
                response = await self.api_client.create_dimension(dimension_data)
                if response.get("success", False):
                    logger.info("Created arc length dimension via API")
                else:
                    logger.error(f"Failed to create arc length dimension: {response.get('error_message', 'Unknown error')}")
            
            # Create final graphics
            # Dimension line
            dim_line = QGraphicsLineItem(
                arc_midpoint.x(), arc_midpoint.y(), 
                self.text_position.x(), self.text_position.y()
            )
            dim_line.setPen(QPen(self.dimension_style.line_color, self.dimension_style.line_weight))
            dim_line.setZValue(999)
            self.scene.addItem(dim_line)
            
            # Arc length text
            text_item = QGraphicsTextItem(f"⌒{arc_length:.2f}")
            text_item.setFont(self.dimension_style.text_font)
            text_item.setDefaultTextColor(self.dimension_style.text_color)
            text_item.setPos(self.text_position.x(), self.text_position.y())
            text_item.setZValue(1000)
            self.scene.addItem(text_item)
            
            # Emit signal
            self.dimension_created.emit(dimension_data)
            
            # Reset tool
            self._reset_tool()
            
        except Exception as e:
            logger.error(f"Error creating arc length dimension: {e}")
            self._cancel_dimension()

    def _cancel_dimension(self):
        """Cancel arc length dimension operation."""
        self._clear_preview()
        self._reset_tool()
        self.dimension_cancelled.emit()

    def _reset_tool(self):
        """Reset tool for next dimension."""
        self.selected_arc = None
        self.text_position = None
        self.state = "waiting_for_arc"

    def _clear_preview(self):
        """Clear preview graphics."""
        for item in self.preview_items:
            if item.scene():
                self.scene.removeItem(item)
        self.preview_items.clear()


class RadialDimensionTool(BaseTool):
    """Tool for creating radius dimensions on circles and arcs."""

    # Signals
    dimension_created = Signal(dict)
    dimension_cancelled = Signal()

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
        
        # State
        self.selected_entity = None
        self.text_position = None
        self.state = "waiting_for_entity"
        
        # Graphics
        self.dimension_style = DimensionStyle()
        self.preview_items = []

    def get_tool_name(self) -> str:
        return "Radius Dimension"

    def get_status_text(self) -> str:
        if self.state == "waiting_for_entity":
            return "Select circle or arc for radius dimension"
        elif self.state == "waiting_for_position":
            return "Click to position radius dimension text"
        else:
            return "Radius dimension tool ready"

    def activate(self) -> bool:
        if not super().activate():
            return False
        self._reset_tool()
        return True

    def deactivate(self):
        self._clear_preview()
        super().deactivate()

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        world_pos = self.scene_pos_from_event(event)
        
        if self.state == "waiting_for_entity":
            entity = self._find_circular_entity_at_point(world_pos)
            if entity:
                self.selected_entity = entity
                self.state = "waiting_for_position"
                return True
                
        elif self.state == "waiting_for_position":
            self.text_position = world_pos
            asyncio.create_task(self._create_radius_dimension())
            return True
            
        return False

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        world_pos = self.scene_pos_from_event(event)
        
        if self.state == "waiting_for_position" and self.selected_entity:
            self._update_radius_preview(world_pos)
            return True
            
        return False

    def handle_key_press(self, event: QKeyEvent) -> bool:
        if event.key() == Qt.Key.Key_Escape:
            self._cancel_dimension()
            return True
        return super().handle_key_press(event)

    def _find_circular_entity_at_point(self, point: QPointF):
        """Find circle or arc entity near the clicked point."""
        # This is a simplified implementation - in practice you'd check against actual CAD entities
        items = self.scene.items(point, Qt.ItemSelectionMode.IntersectsItemBoundingRect)
        for item in items:
            # Check if item represents a circle or arc
            if hasattr(item, 'entity_type') and item.entity_type in ['circle', 'arc']:
                return item
        return None

    def _get_entity_center_and_radius(self, entity):
        """Get center point and radius from circular entity."""
        # This would interface with your actual entity system
        # For demo purposes, assuming entity has center and radius properties
        if hasattr(entity, 'center') and hasattr(entity, 'radius'):
            return entity.center, entity.radius
        return QPointF(0, 0), 10.0  # Fallback values

    def _update_radius_preview(self, text_pos: QPointF):
        """Update preview of radius dimension."""
        self._clear_preview()
        
        if not self.selected_entity:
            return
            
        center, radius = self._get_entity_center_and_radius(self.selected_entity)
        
        # Create radius line from center to circumference
        direction = QPointF(text_pos.x() - center.x(), text_pos.y() - center.y())
        length = math.sqrt(direction.x() ** 2 + direction.y() ** 2)
        
        if length > 0:
            # Normalize direction and scale to radius
            unit_dir = QPointF(direction.x() / length, direction.y() / length)
            circumference_point = QPointF(
                center.x() + unit_dir.x() * radius,
                center.y() + unit_dir.y() * radius
            )
            
            # Create radius line
            radius_line = QGraphicsLineItem(center.x(), center.y(), circumference_point.x(), circumference_point.y())
            radius_line.setPen(QPen(QColor(100, 150, 255, 180), 1, Qt.PenStyle.DashLine))
            radius_line.setZValue(999)
            self.scene.addItem(radius_line)
            self.preview_items.append(radius_line)
            
            # Create radius text
            text_item = QGraphicsTextItem(f"R{radius:.2f}")
            text_item.setFont(self.dimension_style.text_font)
            text_item.setDefaultTextColor(self.dimension_style.text_color)
            text_item.setPos(text_pos.x(), text_pos.y())
            text_item.setZValue(1000)
            self.scene.addItem(text_item)
            self.preview_items.append(text_item)

    async def _create_radius_dimension(self):
        """Create the radius dimension entity."""
        if not self.selected_entity or not self.text_position:
            return
            
        try:
            center, radius = self._get_entity_center_and_radius(self.selected_entity)
            
            # Prepare dimension data
            dimension_data = {
                "dimension_type": "radius",
                "points": [
                    [center.x(), center.y()],  # Center point
                    [self.text_position.x(), self.text_position.y()],  # Text position
                ],
                "measurement_value": radius,
                "layer_id": "0",
                "style_id": None,
            }
            
            # Create dimension via API if available
            if self.api_client:
                response = await self.api_client.create_dimension(dimension_data)
                if response.get("success", False):
                    logger.info("Created radius dimension via API")
                else:
                    logger.error(f"Failed to create radius dimension: {response.get('error_message', 'Unknown error')}")
            
            # Create final graphics (similar to preview but permanent)
            direction = QPointF(self.text_position.x() - center.x(), self.text_position.y() - center.y())
            length = math.sqrt(direction.x() ** 2 + direction.y() ** 2)
            
            if length > 0:
                unit_dir = QPointF(direction.x() / length, direction.y() / length)
                circumference_point = QPointF(
                    center.x() + unit_dir.x() * radius,
                    center.y() + unit_dir.y() * radius
                )
                
                # Create permanent radius line
                radius_line = QGraphicsLineItem(center.x(), center.y(), circumference_point.x(), circumference_point.y())
                radius_line.setPen(QPen(self.dimension_style.line_color, self.dimension_style.line_weight))
                radius_line.setZValue(999)
                self.scene.addItem(radius_line)
                
                # Create permanent text
                text_item = QGraphicsTextItem(f"R{radius:.2f}")
                text_item.setFont(self.dimension_style.text_font)
                text_item.setDefaultTextColor(self.dimension_style.text_color)
                text_item.setPos(self.text_position.x(), self.text_position.y())
                text_item.setZValue(1000)
                self.scene.addItem(text_item)
            
            # Emit signal
            self.dimension_created.emit(dimension_data)
            
            # Reset tool
            self._reset_tool()
            
        except Exception as e:
            logger.error(f"Error creating radius dimension: {e}")
            self._cancel_dimension()

    def _cancel_dimension(self):
        """Cancel radius dimension operation."""
        self._clear_preview()
        self._reset_tool()
        self.dimension_cancelled.emit()

    def _reset_tool(self):
        """Reset tool for next dimension."""
        self.selected_entity = None
        self.text_position = None
        self.state = "waiting_for_entity"

    def _clear_preview(self):
        """Clear preview graphics."""
        for item in self.preview_items:
            if item.scene():
                self.scene.removeItem(item)
        self.preview_items.clear()


class ArcLengthDimensionTool(BaseTool):
    """Tool for creating arc length dimensions on arcs."""

    # Signals
    dimension_created = Signal(dict)
    dimension_cancelled = Signal()

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
        
        # State
        self.selected_arc = None
        self.text_position = None
        self.state = "waiting_for_arc"
        
        # Graphics
        self.dimension_style = DimensionStyle()
        self.preview_items = []

    def get_tool_name(self) -> str:
        return "Arc Length Dimension"

    def get_status_text(self) -> str:
        if self.state == "waiting_for_arc":
            return "Select arc for arc length dimension"
        elif self.state == "waiting_for_position":
            return "Click to position arc length dimension text"
        else:
            return "Arc length dimension tool ready"

    def activate(self) -> bool:
        if not super().activate():
            return False
        self._reset_tool()
        return True

    def deactivate(self):
        self._clear_preview()
        super().deactivate()

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        world_pos = self.scene_pos_from_event(event)
        
        if self.state == "waiting_for_arc":
            arc_entity = self._find_arc_entity_at_point(world_pos)
            if arc_entity:
                self.selected_arc = arc_entity
                self.state = "waiting_for_position"
                return True
                
        elif self.state == "waiting_for_position":
            self.text_position = world_pos
            asyncio.create_task(self._create_arc_length_dimension())
            return True
            
        return False

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        world_pos = self.scene_pos_from_event(event)
        
        if self.state == "waiting_for_position" and self.selected_arc:
            self._update_arc_length_preview(world_pos)
            return True
            
        return False

    def handle_key_press(self, event: QKeyEvent) -> bool:
        if event.key() == Qt.Key.Key_Escape:
            self._cancel_dimension()
            return True
        return super().handle_key_press(event)

    def _find_arc_entity_at_point(self, point: QPointF):
        """Find arc entity near the clicked point."""
        items = self.scene.items(point, Qt.ItemSelectionMode.IntersectsItemBoundingRect)
        for item in items:
            # Check if item represents an arc
            if hasattr(item, 'entity_type') and item.entity_type == 'arc':
                return item
        return None

    def _get_arc_properties(self, arc_entity):
        """Get center, radius, start_angle, end_angle from arc entity."""
        # This would interface with your actual entity system
        # For demo purposes, providing fallback values
        if hasattr(arc_entity, 'center') and hasattr(arc_entity, 'radius'):
            center = arc_entity.center
            radius = arc_entity.radius
            start_angle = getattr(arc_entity, 'start_angle', 0.0)  # degrees
            end_angle = getattr(arc_entity, 'end_angle', 90.0)    # degrees
            return center, radius, start_angle, end_angle
        return QPointF(0, 0), 10.0, 0.0, 90.0  # Fallback values

    def _calculate_arc_length(self, radius: float, start_angle: float, end_angle: float) -> float:
        """Calculate arc length from radius and angle span."""
        # Convert angles to radians
        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)
        
        # Calculate angle span (handle wraparound)
        angle_span = end_rad - start_rad
        if angle_span < 0:
            angle_span += 2 * math.pi
            
        # Arc length = radius * angle (in radians)
        return radius * angle_span

    def _update_arc_length_preview(self, text_pos: QPointF):
        """Update preview of arc length dimension."""
        self._clear_preview()
        
        if not self.selected_arc:
            return
            
        center, radius, start_angle, end_angle = self._get_arc_properties(self.selected_arc)
        arc_length = self._calculate_arc_length(radius, start_angle, end_angle)
        
        # Calculate midpoint of arc for dimension line
        mid_angle = math.radians((start_angle + end_angle) / 2)
        arc_midpoint = QPointF(
            center.x() + radius * math.cos(mid_angle),
            center.y() + radius * math.sin(mid_angle)
        )
        
        # Create dimension line from arc midpoint to text position
        dim_line = QGraphicsLineItem(
            arc_midpoint.x(), arc_midpoint.y(), 
            text_pos.x(), text_pos.y()
        )
        dim_line.setPen(QPen(QColor(100, 150, 255, 180), 1, Qt.PenStyle.DashLine))
        dim_line.setZValue(999)
        self.scene.addItem(dim_line)
        self.preview_items.append(dim_line)
        
        # Create arc length text with arc symbol
        text_item = QGraphicsTextItem(f"⌒{arc_length:.2f}")
        text_item.setFont(self.dimension_style.text_font)
        text_item.setDefaultTextColor(self.dimension_style.text_color)
        text_item.setPos(text_pos.x(), text_pos.y())
        text_item.setZValue(1000)
        self.scene.addItem(text_item)
        self.preview_items.append(text_item)
        
        # Highlight the arc portion being measured
        arc_path = QPainterPath()
        arc_rect = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        arc_path.arcMoveTo(arc_rect, start_angle)
        arc_path.arcTo(arc_rect, start_angle, end_angle - start_angle)
        
        arc_highlight = QGraphicsPathItem(arc_path)
        arc_highlight.setPen(QPen(QColor(255, 100, 100, 200), 2))
        arc_highlight.setZValue(998)
        self.scene.addItem(arc_highlight)
        self.preview_items.append(arc_highlight)

    async def _create_arc_length_dimension(self):
        """Create the arc length dimension entity."""
        if not self.selected_arc or not self.text_position:
            return
            
        try:
            center, radius, start_angle, end_angle = self._get_arc_properties(self.selected_arc)
            arc_length = self._calculate_arc_length(radius, start_angle, end_angle)
            
            # Calculate midpoint of arc
            mid_angle = math.radians((start_angle + end_angle) / 2)
            arc_midpoint = QPointF(
                center.x() + radius * math.cos(mid_angle),
                center.y() + radius * math.sin(mid_angle)
            )
            
            # Prepare dimension data
            dimension_data = {
                "dimension_type": "arc_length",
                "points": [
                    [center.x(), center.y()],  # Arc center
                    [arc_midpoint.x(), arc_midpoint.y()],  # Arc midpoint
                    [self.text_position.x(), self.text_position.y()],  # Text position
                ],
                "measurement_value": arc_length,
                "properties": {
                    "radius": radius,
                    "start_angle": start_angle,
                    "end_angle": end_angle
                },
                "layer_id": "0",
                "style_id": None,
            }
            
            # Create dimension via API if available
            if self.api_client:
                response = await self.api_client.create_dimension(dimension_data)
                if response.get("success", False):
                    logger.info("Created arc length dimension via API")
                else:
                    logger.error(f"Failed to create arc length dimension: {response.get('error_message', 'Unknown error')}")
            
            # Create final graphics
            # Dimension line
            dim_line = QGraphicsLineItem(
                arc_midpoint.x(), arc_midpoint.y(), 
                self.text_position.x(), self.text_position.y()
            )
            dim_line.setPen(QPen(self.dimension_style.line_color, self.dimension_style.line_weight))
            dim_line.setZValue(999)
            self.scene.addItem(dim_line)
            
            # Arc length text
            text_item = QGraphicsTextItem(f"⌒{arc_length:.2f}")
            text_item.setFont(self.dimension_style.text_font)
            text_item.setDefaultTextColor(self.dimension_style.text_color)
            text_item.setPos(self.text_position.x(), self.text_position.y())
            text_item.setZValue(1000)
            self.scene.addItem(text_item)
            
            # Emit signal
            self.dimension_created.emit(dimension_data)
            
            # Reset tool
            self._reset_tool()
            
        except Exception as e:
            logger.error(f"Error creating arc length dimension: {e}")
            self._cancel_dimension()

    def _cancel_dimension(self):
        """Cancel arc length dimension operation."""
        self._clear_preview()
        self._reset_tool()
        self.dimension_cancelled.emit()

    def _reset_tool(self):
        """Reset tool for next dimension."""
        self.selected_arc = None
        self.text_position = None
        self.state = "waiting_for_arc"

    def _clear_preview(self):
        """Clear preview graphics."""
        for item in self.preview_items:
            if item.scene():
                self.scene.removeItem(item)
        self.preview_items.clear()


class DiameterDimensionTool(BaseTool):
    """Tool for creating diameter dimensions on circles."""

    # Signals
    dimension_created = Signal(dict)
    dimension_cancelled = Signal()

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
        
        # State
        self.selected_entity = None
        self.text_position = None
        self.state = "waiting_for_entity"
        
        # Graphics
        self.dimension_style = DimensionStyle()
        self.preview_items = []

    def get_tool_name(self) -> str:
        return "Diameter Dimension"

    def get_status_text(self) -> str:
        if self.state == "waiting_for_entity":
            return "Select circle for diameter dimension"
        elif self.state == "waiting_for_position":
            return "Click to position diameter dimension text"
        else:
            return "Diameter dimension tool ready"

    def activate(self) -> bool:
        if not super().activate():
            return False
        self._reset_tool()
        return True

    def deactivate(self):
        self._clear_preview()
        super().deactivate()

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        world_pos = self.scene_pos_from_event(event)
        
        if self.state == "waiting_for_entity":
            entity = self._find_circle_entity_at_point(world_pos)
            if entity:
                self.selected_entity = entity
                self.state = "waiting_for_position"
                return True
                
        elif self.state == "waiting_for_position":
            self.text_position = world_pos
            asyncio.create_task(self._create_diameter_dimension())
            return True
            
        return False

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        world_pos = self.scene_pos_from_event(event)
        
        if self.state == "waiting_for_position" and self.selected_entity:
            self._update_diameter_preview(world_pos)
            return True
            
        return False

    def handle_key_press(self, event: QKeyEvent) -> bool:
        if event.key() == Qt.Key.Key_Escape:
            self._cancel_dimension()
            return True
        return super().handle_key_press(event)

    def _find_circle_entity_at_point(self, point: QPointF):
        """Find circle entity near the clicked point."""
        items = self.scene.items(point, Qt.ItemSelectionMode.IntersectsItemBoundingRect)
        for item in items:
            # Check if item represents a circle (not arc)
            if hasattr(item, 'entity_type') and item.entity_type == 'circle':
                return item
        return None

    def _get_circle_center_and_radius(self, entity):
        """Get center point and radius from circle entity."""
        if hasattr(entity, 'center') and hasattr(entity, 'radius'):
            return entity.center, entity.radius
        return QPointF(0, 0), 10.0  # Fallback values

    def _update_diameter_preview(self, text_pos: QPointF):
        """Update preview of diameter dimension."""
        self._clear_preview()
        
        if not self.selected_entity:
            return
            
        center, radius = self._get_circle_center_and_radius(self.selected_entity)
        diameter = radius * 2
        
        # Create diameter line through center
        direction = QPointF(text_pos.x() - center.x(), text_pos.y() - center.y())
        length = math.sqrt(direction.x() ** 2 + direction.y() ** 2)
        
        if length > 0:
            # Normalize direction
            unit_dir = QPointF(direction.x() / length, direction.y() / length)
            
            # Calculate diameter line endpoints
            end1 = QPointF(center.x() - unit_dir.x() * radius, center.y() - unit_dir.y() * radius)
            end2 = QPointF(center.x() + unit_dir.x() * radius, center.y() + unit_dir.y() * radius)
            
            # Create diameter line
            diameter_line = QGraphicsLineItem(end1.x(), end1.y(), end2.x(), end2.y())
            diameter_line.setPen(QPen(QColor(100, 150, 255, 180), 1, Qt.PenStyle.DashLine))
            diameter_line.setZValue(999)
            self.scene.addItem(diameter_line)
            self.preview_items.append(diameter_line)
            
            # Create diameter text with diameter symbol
            text_item = QGraphicsTextItem(f"⌀{diameter:.2f}")
            text_item.setFont(self.dimension_style.text_font)
            text_item.setDefaultTextColor(self.dimension_style.text_color)
            text_item.setPos(text_pos.x(), text_pos.y())
            text_item.setZValue(1000)
            self.scene.addItem(text_item)
            self.preview_items.append(text_item)

    async def _create_diameter_dimension(self):
        """Create the diameter dimension entity."""
        if not self.selected_entity or not self.text_position:
            return
            
        try:
            center, radius = self._get_circle_center_and_radius(self.selected_entity)
            diameter = radius * 2
            
            # Prepare dimension data
            dimension_data = {
                "dimension_type": "diameter",
                "points": [
                    [center.x(), center.y()],  # Center point
                    [self.text_position.x(), self.text_position.y()],  # Text position
                ],
                "measurement_value": diameter,
                "layer_id": "0",
                "style_id": None,
            }
            
            # Create dimension via API if available
            if self.api_client:
                response = await self.api_client.create_dimension(dimension_data)
                if response.get("success", False):
                    logger.info("Created diameter dimension via API")
                else:
                    logger.error(f"Failed to create diameter dimension: {response.get('error_message', 'Unknown error')}")
            
            # Create final graphics
            direction = QPointF(self.text_position.x() - center.x(), self.text_position.y() - center.y())
            length = math.sqrt(direction.x() ** 2 + direction.y() ** 2)
            
            if length > 0:
                unit_dir = QPointF(direction.x() / length, direction.y() / length)
                end1 = QPointF(center.x() - unit_dir.x() * radius, center.y() - unit_dir.y() * radius)
                end2 = QPointF(center.x() + unit_dir.x() * radius, center.y() + unit_dir.y() * radius)
                
                # Create permanent diameter line
                diameter_line = QGraphicsLineItem(end1.x(), end1.y(), end2.x(), end2.y())
                diameter_line.setPen(QPen(self.dimension_style.line_color, self.dimension_style.line_weight))
                diameter_line.setZValue(999)
                self.scene.addItem(diameter_line)
                
                # Create permanent text
                text_item = QGraphicsTextItem(f"⌀{diameter:.2f}")
                text_item.setFont(self.dimension_style.text_font)
                text_item.setDefaultTextColor(self.dimension_style.text_color)
                text_item.setPos(self.text_position.x(), self.text_position.y())
                text_item.setZValue(1000)
                self.scene.addItem(text_item)
            
            # Emit signal
            self.dimension_created.emit(dimension_data)
            
            # Reset tool
            self._reset_tool()
            
        except Exception as e:
            logger.error(f"Error creating diameter dimension: {e}")
            self._cancel_dimension()

    def _cancel_dimension(self):
        """Cancel diameter dimension operation."""
        self._clear_preview()
        self._reset_tool()
        self.dimension_cancelled.emit()

    def _reset_tool(self):
        """Reset tool for next dimension."""
        self.selected_entity = None
        self.text_position = None
        self.state = "waiting_for_entity"

    def _clear_preview(self):
        """Clear preview graphics."""
        for item in self.preview_items:
            if item.scene():
                self.scene.removeItem(item)
        self.preview_items.clear()


class ArcLengthDimensionTool(BaseTool):
    """Tool for creating arc length dimensions on arcs."""

    # Signals
    dimension_created = Signal(dict)
    dimension_cancelled = Signal()

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
        
        # State
        self.selected_arc = None
        self.text_position = None
        self.state = "waiting_for_arc"
        
        # Graphics
        self.dimension_style = DimensionStyle()
        self.preview_items = []

    def get_tool_name(self) -> str:
        return "Arc Length Dimension"

    def get_status_text(self) -> str:
        if self.state == "waiting_for_arc":
            return "Select arc for arc length dimension"
        elif self.state == "waiting_for_position":
            return "Click to position arc length dimension text"
        else:
            return "Arc length dimension tool ready"

    def activate(self) -> bool:
        if not super().activate():
            return False
        self._reset_tool()
        return True

    def deactivate(self):
        self._clear_preview()
        super().deactivate()

    def handle_mouse_press(self, event: QMouseEvent) -> bool:
        world_pos = self.scene_pos_from_event(event)
        
        if self.state == "waiting_for_arc":
            arc_entity = self._find_arc_entity_at_point(world_pos)
            if arc_entity:
                self.selected_arc = arc_entity
                self.state = "waiting_for_position"
                return True
                
        elif self.state == "waiting_for_position":
            self.text_position = world_pos
            asyncio.create_task(self._create_arc_length_dimension())
            return True
            
        return False

    def handle_mouse_move(self, event: QMouseEvent) -> bool:
        world_pos = self.scene_pos_from_event(event)
        
        if self.state == "waiting_for_position" and self.selected_arc:
            self._update_arc_length_preview(world_pos)
            return True
            
        return False

    def handle_key_press(self, event: QKeyEvent) -> bool:
        if event.key() == Qt.Key.Key_Escape:
            self._cancel_dimension()
            return True
        return super().handle_key_press(event)

    def _find_arc_entity_at_point(self, point: QPointF):
        """Find arc entity near the clicked point."""
        items = self.scene.items(point, Qt.ItemSelectionMode.IntersectsItemBoundingRect)
        for item in items:
            # Check if item represents an arc
            if hasattr(item, 'entity_type') and item.entity_type == 'arc':
                return item
        return None

    def _get_arc_properties(self, arc_entity):
        """Get center, radius, start_angle, end_angle from arc entity."""
        # This would interface with your actual entity system
        # For demo purposes, providing fallback values
        if hasattr(arc_entity, 'center') and hasattr(arc_entity, 'radius'):
            center = arc_entity.center
            radius = arc_entity.radius
            start_angle = getattr(arc_entity, 'start_angle', 0.0)  # degrees
            end_angle = getattr(arc_entity, 'end_angle', 90.0)    # degrees
            return center, radius, start_angle, end_angle
        return QPointF(0, 0), 10.0, 0.0, 90.0  # Fallback values

    def _calculate_arc_length(self, radius: float, start_angle: float, end_angle: float) -> float:
        """Calculate arc length from radius and angle span."""
        # Convert angles to radians
        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)
        
        # Calculate angle span (handle wraparound)
        angle_span = end_rad - start_rad
        if angle_span < 0:
            angle_span += 2 * math.pi
            
        # Arc length = radius * angle (in radians)
        return radius * angle_span

    def _update_arc_length_preview(self, text_pos: QPointF):
        """Update preview of arc length dimension."""
        self._clear_preview()
        
        if not self.selected_arc:
            return
            
        center, radius, start_angle, end_angle = self._get_arc_properties(self.selected_arc)
        arc_length = self._calculate_arc_length(radius, start_angle, end_angle)
        
        # Calculate midpoint of arc for dimension line
        mid_angle = math.radians((start_angle + end_angle) / 2)
        arc_midpoint = QPointF(
            center.x() + radius * math.cos(mid_angle),
            center.y() + radius * math.sin(mid_angle)
        )
        
        # Create dimension line from arc midpoint to text position
        dim_line = QGraphicsLineItem(
            arc_midpoint.x(), arc_midpoint.y(), 
            text_pos.x(), text_pos.y()
        )
        dim_line.setPen(QPen(QColor(100, 150, 255, 180), 1, Qt.PenStyle.DashLine))
        dim_line.setZValue(999)
        self.scene.addItem(dim_line)
        self.preview_items.append(dim_line)
        
        # Create arc length text with arc symbol
        text_item = QGraphicsTextItem(f"⌒{arc_length:.2f}")
        text_item.setFont(self.dimension_style.text_font)
        text_item.setDefaultTextColor(self.dimension_style.text_color)
        text_item.setPos(text_pos.x(), text_pos.y())
        text_item.setZValue(1000)
        self.scene.addItem(text_item)
        self.preview_items.append(text_item)
        
        # Highlight the arc portion being measured
        arc_path = QPainterPath()
        arc_rect = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        arc_path.arcMoveTo(arc_rect, start_angle)
        arc_path.arcTo(arc_rect, start_angle, end_angle - start_angle)
        
        arc_highlight = QGraphicsPathItem(arc_path)
        arc_highlight.setPen(QPen(QColor(255, 100, 100, 200), 2))
        arc_highlight.setZValue(998)
        self.scene.addItem(arc_highlight)
        self.preview_items.append(arc_highlight)

    async def _create_arc_length_dimension(self):
        """Create the arc length dimension entity."""
        if not self.selected_arc or not self.text_position:
            return
            
        try:
            center, radius, start_angle, end_angle = self._get_arc_properties(self.selected_arc)
            arc_length = self._calculate_arc_length(radius, start_angle, end_angle)
            
            # Calculate midpoint of arc
            mid_angle = math.radians((start_angle + end_angle) / 2)
            arc_midpoint = QPointF(
                center.x() + radius * math.cos(mid_angle),
                center.y() + radius * math.sin(mid_angle)
            )
            
            # Prepare dimension data
            dimension_data = {
                "dimension_type": "arc_length",
                "points": [
                    [center.x(), center.y()],  # Arc center
                    [arc_midpoint.x(), arc_midpoint.y()],  # Arc midpoint
                    [self.text_position.x(), self.text_position.y()],  # Text position
                ],
                "measurement_value": arc_length,
                "properties": {
                    "radius": radius,
                    "start_angle": start_angle,
                    "end_angle": end_angle
                },
                "layer_id": "0",
                "style_id": None,
            }
            
            # Create dimension via API if available
            if self.api_client:
                response = await self.api_client.create_dimension(dimension_data)
                if response.get("success", False):
                    logger.info("Created arc length dimension via API")
                else:
                    logger.error(f"Failed to create arc length dimension: {response.get('error_message', 'Unknown error')}")
            
            # Create final graphics
            # Dimension line
            dim_line = QGraphicsLineItem(
                arc_midpoint.x(), arc_midpoint.y(), 
                self.text_position.x(), self.text_position.y()
            )
            dim_line.setPen(QPen(self.dimension_style.line_color, self.dimension_style.line_weight))
            dim_line.setZValue(999)
            self.scene.addItem(dim_line)
            
            # Arc length text
            text_item = QGraphicsTextItem(f"⌒{arc_length:.2f}")
            text_item.setFont(self.dimension_style.text_font)
            text_item.setDefaultTextColor(self.dimension_style.text_color)
            text_item.setPos(self.text_position.x(), self.text_position.y())
            text_item.setZValue(1000)
            self.scene.addItem(text_item)
            
            # Emit signal
            self.dimension_created.emit(dimension_data)
            
            # Reset tool
            self._reset_tool()
            
        except Exception as e:
            logger.error(f"Error creating arc length dimension: {e}")
            self._cancel_dimension()

    def _cancel_dimension(self):
        """Cancel arc length dimension operation."""
        self._clear_preview()
        self._reset_tool()
        self.dimension_cancelled.emit()

    def _reset_tool(self):
        """Reset tool for next dimension."""
        self.selected_arc = None
        self.text_position = None
        self.state = "waiting_for_arc"

    def _clear_preview(self):
        """Clear preview graphics."""
        for item in self.preview_items:
            if item.scene():
                self.scene.removeItem(item)
        self.preview_items.clear()
