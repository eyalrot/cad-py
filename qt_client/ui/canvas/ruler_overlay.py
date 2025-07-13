"""
Ruler overlay for the CAD drawing canvas.

This module provides horizontal and vertical rulers with measurements,
tick marks, and coordinate display for precise drawing operations.
"""

import logging
import math
from typing import List, Optional, Tuple

from PySide6.QtCore import QObject, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QWidget

logger = logging.getLogger(__name__)


class RulerOverlay(QObject):
    """
    Ruler overlay for drawing canvas with measurements and tick marks.

    Provides:
    - Horizontal and vertical rulers
    - Adaptive tick spacing based on zoom
    - Coordinate measurements
    - Customizable units and formatting
    """

    # Signals
    ruler_changed = Signal()
    unit_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.parent = parent

        # Ruler properties
        self.ruler_height = 20  # Height/width of ruler in pixels
        self.visible = True
        self.show_horizontal = True
        self.show_vertical = True

        # Measurement properties
        self.units = "mm"  # Default units
        self.precision = 1  # Decimal places
        self.major_tick_interval = 10.0  # Major tick interval in world units
        self.minor_tick_interval = 1.0  # Minor tick interval in world units
        self.subdivisions = 10  # Number of minor ticks between major ticks

        # Visual properties
        self.background_color = QColor(240, 240, 240, 220)
        self.border_color = QColor(150, 150, 150)
        self.major_tick_color = QColor(80, 80, 80)
        self.minor_tick_color = QColor(120, 120, 120)
        self.text_color = QColor(50, 50, 50)

        # Font properties
        self.font = QFont("Arial", 8)
        self.font_metrics = QFontMetrics(self.font)

        # Adaptive properties
        self.min_tick_spacing = 5  # Minimum pixels between ticks
        self.max_tick_spacing = 100  # Maximum pixels between ticks

        # Current zoom state
        self.current_zoom = 1.0
        self.view_size = QSize(800, 600)

        logger.debug("Ruler overlay initialized")

    def set_visible(self, visible: bool):
        """Set ruler visibility."""
        if self.visible != visible:
            self.visible = visible
            self.ruler_changed.emit()

    def set_horizontal_visible(self, visible: bool):
        """Set horizontal ruler visibility."""
        if self.show_horizontal != visible:
            self.show_horizontal = visible
            self.ruler_changed.emit()

    def set_vertical_visible(self, visible: bool):
        """Set vertical ruler visibility."""
        if self.show_vertical != visible:
            self.show_vertical = visible
            self.ruler_changed.emit()

    def set_units(self, units: str):
        """Set measurement units."""
        if self.units != units:
            self.units = units
            self.unit_changed.emit(units)
            self.ruler_changed.emit()

    def set_precision(self, precision: int):
        """Set measurement precision (decimal places)."""
        if self.precision != precision:
            self.precision = max(0, min(6, precision))
            self.ruler_changed.emit()

    def update_for_zoom(self, zoom_factor: float):
        """Update ruler for zoom level changes."""
        self.current_zoom = zoom_factor

        # Calculate adaptive tick spacing
        major_pixel_spacing = self.major_tick_interval * zoom_factor

        # Adjust tick intervals to maintain readable spacing
        if major_pixel_spacing < self.min_tick_spacing:
            # Zoom out: increase spacing
            while (
                major_pixel_spacing < self.min_tick_spacing
                and self.major_tick_interval < 10000
            ):
                self.major_tick_interval *= 10
                major_pixel_spacing = self.major_tick_interval * zoom_factor
        elif major_pixel_spacing > self.max_tick_spacing:
            # Zoom in: decrease spacing
            while (
                major_pixel_spacing > self.max_tick_spacing
                and self.major_tick_interval > 0.001
            ):
                self.major_tick_interval /= 10
                major_pixel_spacing = self.major_tick_interval * zoom_factor

        # Update minor tick interval
        self.minor_tick_interval = self.major_tick_interval / self.subdivisions

        logger.debug(
            f"Ruler updated for zoom {zoom_factor:.3f}: "
            f"major={self.major_tick_interval}, minor={self.minor_tick_interval}"
        )

    def update_for_view_size(self, size: QSize):
        """Update ruler for view size changes."""
        self.view_size = size

    def paint_rulers(self, painter: QPainter, view):
        """Paint rulers on the view."""
        if not self.visible:
            return

        try:
            # Get visible area in world coordinates
            visible_rect = view.mapToScene(view.rect()).boundingRect()

            # Paint horizontal ruler
            if self.show_horizontal:
                self._paint_horizontal_ruler(painter, view, visible_rect)

            # Paint vertical ruler
            if self.show_vertical:
                self._paint_vertical_ruler(painter, view, visible_rect)

        except Exception as e:
            logger.warning(f"Error painting rulers: {e}")

    def _paint_horizontal_ruler(self, painter: QPainter, view, visible_rect: QRectF):
        """Paint horizontal ruler at the top of the view."""
        view_rect = view.rect()
        ruler_rect = QRectF(0, 0, view_rect.width(), self.ruler_height)

        # Draw ruler background
        painter.fillRect(ruler_rect, self.background_color)
        painter.setPen(QPen(self.border_color, 1))
        painter.drawRect(ruler_rect)

        # Calculate tick positions
        left_world = visible_rect.left()
        right_world = visible_rect.right()

        # Draw ticks and labels
        self._draw_horizontal_ticks(painter, view, left_world, right_world, ruler_rect)

    def _paint_vertical_ruler(self, painter: QPainter, view, visible_rect: QRectF):
        """Paint vertical ruler at the left of the view."""
        view_rect = view.rect()
        ruler_rect = QRectF(0, 0, self.ruler_height, view_rect.height())

        # Draw ruler background
        painter.fillRect(ruler_rect, self.background_color)
        painter.setPen(QPen(self.border_color, 1))
        painter.drawRect(ruler_rect)

        # Calculate tick positions
        top_world = visible_rect.top()
        bottom_world = visible_rect.bottom()

        # Draw ticks and labels
        self._draw_vertical_ticks(painter, view, top_world, bottom_world, ruler_rect)

    def _draw_horizontal_ticks(
        self, painter: QPainter, view, left: float, right: float, ruler_rect: QRectF
    ):
        """Draw horizontal ruler ticks and labels."""
        # Calculate tick range
        start_tick = (
            math.floor(left / self.major_tick_interval) * self.major_tick_interval
        )
        end_tick = (
            math.ceil(right / self.major_tick_interval) * self.major_tick_interval
        )

        # Draw major ticks
        painter.setPen(QPen(self.major_tick_color, 1))
        painter.setFont(self.font)

        current_tick = start_tick
        while current_tick <= end_tick:
            # Convert to view coordinates
            scene_point = QPointF(current_tick, 0)
            view_point = view.mapFromScene(scene_point)
            x = view_point.x()

            if 0 <= x <= ruler_rect.width():
                # Draw major tick
                painter.drawLine(
                    int(x),
                    int(ruler_rect.height() - 8),
                    int(x),
                    int(ruler_rect.height()),
                )

                # Draw label
                label = self._format_measurement(current_tick)
                label_width = self.font_metrics.horizontalAdvance(label)
                label_x = x - label_width / 2

                if label_x >= 0 and label_x + label_width <= ruler_rect.width():
                    painter.setPen(QPen(self.text_color, 1))
                    painter.drawText(int(label_x), int(ruler_rect.height() - 10), label)
                    painter.setPen(QPen(self.major_tick_color, 1))

            current_tick += self.major_tick_interval

        # Draw minor ticks
        if self.minor_tick_interval > 0:
            painter.setPen(QPen(self.minor_tick_color, 1))

            start_minor = (
                math.floor(left / self.minor_tick_interval) * self.minor_tick_interval
            )
            end_minor = (
                math.ceil(right / self.minor_tick_interval) * self.minor_tick_interval
            )

            current_minor = start_minor
            while current_minor <= end_minor:
                # Skip major ticks
                if abs(current_minor % self.major_tick_interval) > 1e-6:
                    scene_point = QPointF(current_minor, 0)
                    view_point = view.mapFromScene(scene_point)
                    x = view_point.x()

                    if 0 <= x <= ruler_rect.width():
                        # Draw minor tick
                        painter.drawLine(
                            int(x),
                            int(ruler_rect.height() - 4),
                            int(x),
                            int(ruler_rect.height()),
                        )

                current_minor += self.minor_tick_interval

    def _draw_vertical_ticks(
        self, painter: QPainter, view, top: float, bottom: float, ruler_rect: QRectF
    ):
        """Draw vertical ruler ticks and labels."""
        # Calculate tick range
        start_tick = (
            math.floor(top / self.major_tick_interval) * self.major_tick_interval
        )
        end_tick = (
            math.ceil(bottom / self.major_tick_interval) * self.major_tick_interval
        )

        # Draw major ticks
        painter.setPen(QPen(self.major_tick_color, 1))
        painter.setFont(self.font)

        current_tick = start_tick
        while current_tick <= end_tick:
            # Convert to view coordinates
            scene_point = QPointF(0, current_tick)
            view_point = view.mapFromScene(scene_point)
            y = view_point.y()

            if 0 <= y <= ruler_rect.height():
                # Draw major tick
                painter.drawLine(
                    int(ruler_rect.width() - 8), int(y), int(ruler_rect.width()), int(y)
                )

                # Draw label (rotated for vertical ruler)
                label = self._format_measurement(
                    -current_tick
                )  # Negative for standard Y-up coordinate system

                painter.save()
                painter.setPen(QPen(self.text_color, 1))
                painter.translate(int(ruler_rect.width() - 12), int(y))
                painter.rotate(-90)
                painter.drawText(0, 0, label)
                painter.restore()

            current_tick += self.major_tick_interval

        # Draw minor ticks
        if self.minor_tick_interval > 0:
            painter.setPen(QPen(self.minor_tick_color, 1))

            start_minor = (
                math.floor(top / self.minor_tick_interval) * self.minor_tick_interval
            )
            end_minor = (
                math.ceil(bottom / self.minor_tick_interval) * self.minor_tick_interval
            )

            current_minor = start_minor
            while current_minor <= end_minor:
                # Skip major ticks
                if abs(current_minor % self.major_tick_interval) > 1e-6:
                    scene_point = QPointF(0, current_minor)
                    view_point = view.mapFromScene(scene_point)
                    y = view_point.y()

                    if 0 <= y <= ruler_rect.height():
                        # Draw minor tick
                        painter.drawLine(
                            int(ruler_rect.width() - 4),
                            int(y),
                            int(ruler_rect.width()),
                            int(y),
                        )

                current_minor += self.minor_tick_interval

    def _format_measurement(self, value: float) -> str:
        """Format measurement value with units."""
        if self.precision == 0:
            return f"{int(round(value))}"
        else:
            format_str = f"{{:.{self.precision}f}}"
            return format_str.format(value)

    def get_ruler_height(self) -> int:
        """Get ruler height in pixels."""
        return self.ruler_height if self.visible else 0

    def get_content_offset(self) -> Tuple[int, int]:
        """Get content offset due to rulers (x_offset, y_offset)."""
        x_offset = self.ruler_height if (self.visible and self.show_vertical) else 0
        y_offset = self.ruler_height if (self.visible and self.show_horizontal) else 0
        return x_offset, y_offset

    def hit_test_rulers(self, point: QPointF) -> str:
        """
        Hit test for ruler areas.

        Args:
            point: Point in view coordinates

        Returns:
            'horizontal', 'vertical', 'corner', or 'none'
        """
        if not self.visible:
            return "none"

        x, y = point.x(), point.y()
        h_ruler_active = self.show_horizontal and 0 <= y <= self.ruler_height
        v_ruler_active = self.show_vertical and 0 <= x <= self.ruler_height

        if h_ruler_active and v_ruler_active:
            return "corner"
        elif h_ruler_active:
            return "horizontal"
        elif v_ruler_active:
            return "vertical"
        else:
            return "none"

    def world_to_ruler_coordinate(
        self, world_pos: QPointF, view
    ) -> Tuple[float, float]:
        """Convert world position to ruler coordinates."""
        view_pos = view.mapFromScene(world_pos)

        # Adjust for ruler offset
        x_offset, y_offset = self.get_content_offset()
        ruler_x = view_pos.x() - x_offset
        ruler_y = view_pos.y() - y_offset

        return ruler_x, ruler_y

    def get_ruler_info(self) -> dict:
        """Get current ruler information."""
        return {
            "visible": self.visible,
            "show_horizontal": self.show_horizontal,
            "show_vertical": self.show_vertical,
            "units": self.units,
            "precision": self.precision,
            "major_tick_interval": self.major_tick_interval,
            "minor_tick_interval": self.minor_tick_interval,
            "ruler_height": self.ruler_height,
            "zoom": self.current_zoom,
        }


class RulerGuides(QObject):
    """
    Ruler guides system for temporary measurement lines.

    Provides draggable guide lines from rulers for precise alignment.
    """

    # Signals
    guide_added = Signal(str, float)  # orientation, position
    guide_removed = Signal(str, float)
    guide_moved = Signal(str, float, float)  # orientation, old_pos, new_pos

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Guide storage
        self.horizontal_guides: List[float] = []  # Y positions in world coordinates
        self.vertical_guides: List[float] = []  # X positions in world coordinates

        # Visual properties
        self.guide_color = QColor(255, 0, 255, 180)  # Magenta guides
        self.guide_width = 1.0
        self.guide_style = Qt.DashLine

        # Interaction
        self.drag_tolerance = 5  # Pixels
        self.active_guide: Optional[Tuple[str, int]] = None  # (orientation, index)

    def add_horizontal_guide(self, y_position: float):
        """Add horizontal guide at Y position."""
        if y_position not in self.horizontal_guides:
            self.horizontal_guides.append(y_position)
            self.horizontal_guides.sort()
            self.guide_added.emit("horizontal", y_position)

    def add_vertical_guide(self, x_position: float):
        """Add vertical guide at X position."""
        if x_position not in self.vertical_guides:
            self.vertical_guides.append(x_position)
            self.vertical_guides.sort()
            self.guide_added.emit("vertical", x_position)

    def remove_horizontal_guide(self, y_position: float):
        """Remove horizontal guide."""
        if y_position in self.horizontal_guides:
            self.horizontal_guides.remove(y_position)
            self.guide_removed.emit("horizontal", y_position)

    def remove_vertical_guide(self, x_position: float):
        """Remove vertical guide."""
        if x_position in self.vertical_guides:
            self.vertical_guides.remove(x_position)
            self.guide_removed.emit("vertical", x_position)

    def clear_all_guides(self):
        """Clear all guides."""
        self.horizontal_guides.clear()
        self.vertical_guides.clear()

    def paint_guides(self, painter: QPainter, view, visible_rect: QRectF):
        """Paint all guide lines."""
        pen = QPen(self.guide_color)
        pen.setWidthF(self.guide_width)
        pen.setStyle(self.guide_style)
        pen.setCosmetic(True)
        painter.setPen(pen)

        # Draw horizontal guides
        for y_pos in self.horizontal_guides:
            if visible_rect.top() <= y_pos <= visible_rect.bottom():
                start_scene = QPointF(visible_rect.left(), y_pos)
                end_scene = QPointF(visible_rect.right(), y_pos)
                start_view = view.mapFromScene(start_scene)
                end_view = view.mapFromScene(end_scene)
                painter.drawLine(start_view, end_view)

        # Draw vertical guides
        for x_pos in self.vertical_guides:
            if visible_rect.left() <= x_pos <= visible_rect.right():
                start_scene = QPointF(x_pos, visible_rect.top())
                end_scene = QPointF(x_pos, visible_rect.bottom())
                start_view = view.mapFromScene(start_scene)
                end_view = view.mapFromScene(end_scene)
                painter.drawLine(start_view, end_view)

    def hit_test_guides(
        self, world_pos: QPointF, tolerance: float = 1.0
    ) -> Optional[Tuple[str, int]]:
        """
        Hit test for guide lines.

        Returns:
            Tuple of (orientation, index) if hit, None otherwise
        """
        # Test horizontal guides
        for i, y_pos in enumerate(self.horizontal_guides):
            if abs(world_pos.y() - y_pos) <= tolerance:
                return ("horizontal", i)

        # Test vertical guides
        for i, x_pos in enumerate(self.vertical_guides):
            if abs(world_pos.x() - x_pos) <= tolerance:
                return ("vertical", i)

        return None

    def get_snap_guides_near(self, world_pos: QPointF, radius: float) -> List[QPointF]:
        """Get guide snap points near the specified position."""
        snap_points = []

        # Check horizontal guides
        for y_pos in self.horizontal_guides:
            if abs(world_pos.y() - y_pos) <= radius:
                snap_points.append(QPointF(world_pos.x(), y_pos))

        # Check vertical guides
        for x_pos in self.vertical_guides:
            if abs(world_pos.x() - x_pos) <= radius:
                snap_points.append(QPointF(x_pos, world_pos.y()))

        return snap_points
