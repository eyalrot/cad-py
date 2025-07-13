"""
Snap engine for CAD drawing tools.

This module provides a comprehensive snapping system that integrates
with grid, rulers, geometry, and custom snap points for precise drawing.
"""

import logging
import math
from dataclasses import dataclass
from enum import Enum, Flag, auto
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, QPointF, QRectF, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QGraphicsScene

logger = logging.getLogger(__name__)


class SnapType(Flag):
    """Types of snapping available."""

    NONE = 0
    GRID = auto()
    ENDPOINT = auto()
    MIDPOINT = auto()
    CENTER = auto()
    INTERSECTION = auto()
    PERPENDICULAR = auto()
    TANGENT = auto()
    QUADRANT = auto()
    NEAREST = auto()
    RULER_GUIDE = auto()
    PARALLEL = auto()
    EXTENSION = auto()

    # Convenience combinations
    ALL = (
        GRID
        | ENDPOINT
        | MIDPOINT
        | CENTER
        | INTERSECTION
        | PERPENDICULAR
        | TANGENT
        | QUADRANT
        | NEAREST
        | RULER_GUIDE
        | PARALLEL
        | EXTENSION
    )
    BASIC = GRID | ENDPOINT | MIDPOINT | CENTER
    GEOMETRIC = (
        ENDPOINT | MIDPOINT | CENTER | INTERSECTION | PERPENDICULAR | TANGENT | QUADRANT
    )


@dataclass
class SnapPoint:
    """Represents a snap point with metadata."""

    position: QPointF
    snap_type: SnapType
    priority: int = 0  # Higher priority takes precedence
    description: str = ""
    source_object: Optional[Any] = None  # Reference to geometry that created this snap


@dataclass
class SnapResult:
    """Result of a snap operation."""

    snapped: bool
    point: QPointF
    snap_point: Optional[SnapPoint] = None
    distance: float = 0.0


class SnapEngine(QObject):
    """
    Comprehensive snap engine for CAD drawing operations.

    Features:
    - Grid snapping with adaptive tolerance
    - Geometric snapping (endpoints, midpoints, centers, etc.)
    - Ruler guide snapping
    - Custom snap point registration
    - Visual snap feedback
    - Configurable snap types and tolerances
    """

    # Signals
    snap_preview = Signal(QPointF, str)  # position, description
    snap_cleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Snap configuration
        self.enabled_snaps = SnapType.BASIC
        self.snap_tolerance = 10.0  # Pixels
        self.priority_tolerance = (
            5.0  # Higher priority snaps within this range override others
        )

        # Grid and ruler references
        self.grid_overlay = None
        self.ruler_guides = None

        # Scene reference for geometry snapping
        self.scene: Optional[QGraphicsScene] = None

        # Custom snap points
        self.custom_snap_points: List[SnapPoint] = []

        # Visual feedback
        self.show_snap_preview = True
        self.snap_marker_size = 8
        self.snap_colors = {
            SnapType.GRID: QColor(100, 255, 100, 180),
            SnapType.ENDPOINT: QColor(255, 100, 100, 180),
            SnapType.MIDPOINT: QColor(100, 100, 255, 180),
            SnapType.CENTER: QColor(255, 255, 100, 180),
            SnapType.INTERSECTION: QColor(255, 100, 255, 180),
            SnapType.RULER_GUIDE: QColor(255, 150, 0, 180),
        }

        # Current snap state
        self.current_snap_point: Optional[SnapPoint] = None
        self.preview_active = False

        logger.debug("Snap engine initialized")

    def set_grid_overlay(self, grid_overlay):
        """Set grid overlay for grid snapping."""
        self.grid_overlay = grid_overlay

    def set_ruler_guides(self, ruler_guides):
        """Set ruler guides for guide snapping."""
        self.ruler_guides = ruler_guides

    def set_scene(self, scene: QGraphicsScene):
        """Set graphics scene for geometry snapping."""
        self.scene = scene

    def set_enabled_snaps(self, snap_types: SnapType):
        """Set which snap types are enabled."""
        self.enabled_snaps = snap_types
        logger.debug(f"Enabled snap types: {snap_types}")

    def set_snap_tolerance(self, tolerance: float):
        """Set snap tolerance in pixels."""
        self.snap_tolerance = max(1.0, tolerance)

    def enable_snap_type(self, snap_type: SnapType, enabled: bool = True):
        """Enable or disable a specific snap type."""
        if enabled:
            self.enabled_snaps |= snap_type
        else:
            self.enabled_snaps &= ~snap_type

    def is_snap_enabled(self, snap_type: SnapType) -> bool:
        """Check if a snap type is enabled."""
        return bool(self.enabled_snaps & snap_type)

    def add_custom_snap_point(
        self, position: QPointF, description: str = "", priority: int = 0
    ):
        """Add a custom snap point."""
        snap_point = SnapPoint(
            position=QPointF(position),
            snap_type=SnapType.NEAREST,
            priority=priority,
            description=description,
        )
        self.custom_snap_points.append(snap_point)

    def clear_custom_snap_points(self):
        """Clear all custom snap points."""
        self.custom_snap_points.clear()

    def snap_point(
        self, input_point: QPointF, view, exclude_point: Optional[QPointF] = None
    ) -> SnapResult:
        """
        Find the best snap point for the given input position.

        Args:
            input_point: World coordinates of input position
            view: View for coordinate transformations
            exclude_point: Point to exclude from snapping (e.g., start point of current operation)

        Returns:
            SnapResult with snap information
        """
        if not self.enabled_snaps:
            return SnapResult(False, input_point)

        # Convert tolerance to world coordinates
        world_tolerance = (
            self.snap_tolerance / view.transform().m11()
        )  # Assuming uniform scaling

        # Collect all potential snap points
        candidates: List[SnapPoint] = []

        # Grid snapping
        if self.is_snap_enabled(SnapType.GRID) and self.grid_overlay:
            grid_points = self._get_grid_snap_points(input_point, world_tolerance)
            candidates.extend(grid_points)

        # Ruler guide snapping
        if self.is_snap_enabled(SnapType.RULER_GUIDE) and self.ruler_guides:
            guide_points = self._get_ruler_guide_snap_points(
                input_point, world_tolerance
            )
            candidates.extend(guide_points)

        # Geometry snapping
        if self.scene and (self.enabled_snaps & SnapType.GEOMETRIC):
            geometry_points = self._get_geometry_snap_points(
                input_point, world_tolerance, exclude_point
            )
            candidates.extend(geometry_points)

        # Custom snap points
        custom_points = self._get_custom_snap_points(input_point, world_tolerance)
        candidates.extend(custom_points)

        # Find best snap point
        best_snap = self._find_best_snap_point(input_point, candidates)

        if best_snap:
            # Update preview
            if self.show_snap_preview:
                self._update_snap_preview(best_snap)

            return SnapResult(
                snapped=True,
                point=best_snap.position,
                snap_point=best_snap,
                distance=self._distance(input_point, best_snap.position),
            )
        else:
            # Clear preview
            if self.preview_active:
                self._clear_snap_preview()

            return SnapResult(False, input_point)

    def _get_grid_snap_points(
        self, input_point: QPointF, tolerance: float
    ) -> List[SnapPoint]:
        """Get grid snap points near the input point."""
        if not self.grid_overlay or not self.grid_overlay.visible:
            return []

        snap_points = []
        grid_positions = self.grid_overlay.get_snap_points_near(input_point, tolerance)

        for pos in grid_positions:
            snap_points.append(
                SnapPoint(
                    position=pos,
                    snap_type=SnapType.GRID,
                    priority=1,
                    description="Grid",
                )
            )

        return snap_points

    def _get_ruler_guide_snap_points(
        self, input_point: QPointF, tolerance: float
    ) -> List[SnapPoint]:
        """Get ruler guide snap points near the input point."""
        if not self.ruler_guides:
            return []

        snap_points = []
        guide_positions = self.ruler_guides.get_snap_guides_near(input_point, tolerance)

        for pos in guide_positions:
            snap_points.append(
                SnapPoint(
                    position=pos,
                    snap_type=SnapType.RULER_GUIDE,
                    priority=3,
                    description="Ruler Guide",
                )
            )

        return snap_points

    def _get_geometry_snap_points(
        self, input_point: QPointF, tolerance: float, exclude_point: Optional[QPointF]
    ) -> List[SnapPoint]:
        """Get geometry snap points from scene objects."""
        snap_points = []

        if not self.scene:
            return snap_points

        # Get items near the input point
        search_rect = QPointF(tolerance, tolerance)
        search_area = QRectF(input_point - search_rect, input_point + search_rect)
        nearby_items = self.scene.items(search_area)

        for item in nearby_items:
            # Extract geometry points based on item type
            item_snaps = self._extract_item_snap_points(
                item, input_point, tolerance, exclude_point
            )
            snap_points.extend(item_snaps)

        return snap_points

    def _extract_item_snap_points(
        self,
        item,
        input_point: QPointF,
        tolerance: float,
        exclude_point: Optional[QPointF],
    ) -> List[SnapPoint]:
        """Extract snap points from a graphics item."""
        snap_points = []

        # This is a simplified implementation - in a real application,
        # you would analyze the specific geometry type and extract appropriate points

        # For now, just get the item's bounding rect corners and center
        if hasattr(item, "boundingRect"):
            rect = item.boundingRect()

            # Center point
            if self.is_snap_enabled(SnapType.CENTER):
                center = rect.center()
                if self._is_point_valid(center, exclude_point, tolerance):
                    snap_points.append(
                        SnapPoint(
                            position=center,
                            snap_type=SnapType.CENTER,
                            priority=4,
                            description="Center",
                            source_object=item,
                        )
                    )

            # Corner points (endpoints)
            if self.is_snap_enabled(SnapType.ENDPOINT):
                corners = [
                    rect.topLeft(),
                    rect.topRight(),
                    rect.bottomLeft(),
                    rect.bottomRight(),
                ]

                for corner in corners:
                    if self._is_point_valid(corner, exclude_point, tolerance):
                        snap_points.append(
                            SnapPoint(
                                position=corner,
                                snap_type=SnapType.ENDPOINT,
                                priority=5,
                                description="Endpoint",
                                source_object=item,
                            )
                        )

            # Midpoints
            if self.is_snap_enabled(SnapType.MIDPOINT):
                midpoints = [
                    QPointF((rect.left() + rect.right()) / 2, rect.top()),  # Top mid
                    QPointF(
                        (rect.left() + rect.right()) / 2, rect.bottom()
                    ),  # Bottom mid
                    QPointF(rect.left(), (rect.top() + rect.bottom()) / 2),  # Left mid
                    QPointF(
                        rect.right(), (rect.top() + rect.bottom()) / 2
                    ),  # Right mid
                ]

                for midpoint in midpoints:
                    if self._is_point_valid(midpoint, exclude_point, tolerance):
                        snap_points.append(
                            SnapPoint(
                                position=midpoint,
                                snap_type=SnapType.MIDPOINT,
                                priority=4,
                                description="Midpoint",
                                source_object=item,
                            )
                        )

        return snap_points

    def _get_custom_snap_points(
        self, input_point: QPointF, tolerance: float
    ) -> List[SnapPoint]:
        """Get custom snap points near the input point."""
        snap_points = []

        for custom_point in self.custom_snap_points:
            distance = self._distance(input_point, custom_point.position)
            if distance <= tolerance:
                snap_points.append(custom_point)

        return snap_points

    def _find_best_snap_point(
        self, input_point: QPointF, candidates: List[SnapPoint]
    ) -> Optional[SnapPoint]:
        """Find the best snap point from candidates."""
        if not candidates:
            return None

        # Sort by priority (higher first), then by distance (closer first)
        def sort_key(snap_point: SnapPoint) -> Tuple[int, float]:
            distance = self._distance(input_point, snap_point.position)
            return (-snap_point.priority, distance)

        candidates.sort(key=sort_key)

        # Check if the highest priority candidate should override others
        best = candidates[0]
        best_distance = self._distance(input_point, best.position)

        # If we have multiple candidates, check priority override
        if len(candidates) > 1:
            second_best = candidates[1]
            second_distance = self._distance(input_point, second_best.position)

            # If second candidate is much closer and priority difference isn't huge
            priority_diff = best.priority - second_best.priority
            distance_diff = second_distance - best_distance

            if priority_diff <= 1 and distance_diff < -best_distance * 0.5:
                return second_best

        return best

    def _is_point_valid(
        self, point: QPointF, exclude_point: Optional[QPointF], tolerance: float
    ) -> bool:
        """Check if a point is valid for snapping."""
        if exclude_point is not None:
            return self._distance(point, exclude_point) > tolerance * 0.5
        return True

    def _distance(self, p1: QPointF, p2: QPointF) -> float:
        """Calculate distance between two points."""
        dx = p1.x() - p2.x()
        dy = p1.y() - p2.y()
        return math.sqrt(dx * dx + dy * dy)

    def _update_snap_preview(self, snap_point: SnapPoint):
        """Update snap preview display."""
        self.current_snap_point = snap_point
        self.preview_active = True

        description = snap_point.description or snap_point.snap_type.name.title()
        self.snap_preview.emit(snap_point.position, description)

    def _clear_snap_preview(self):
        """Clear snap preview display."""
        self.current_snap_point = None
        self.preview_active = False
        self.snap_cleared.emit()

    def paint_snap_feedback(self, painter: QPainter, view, visible_rect: QRectF):
        """Paint snap feedback on the view."""
        if not self.preview_active or not self.current_snap_point:
            return

        snap_point = self.current_snap_point

        # Get snap color
        color = self.snap_colors.get(snap_point.snap_type, QColor(255, 255, 255, 180))

        # Convert to view coordinates
        view_pos = view.mapFromScene(snap_point.position)

        # Draw snap marker
        painter.save()

        pen = QPen(color)
        pen.setWidth(2)
        pen.setCosmetic(True)
        painter.setPen(pen)

        # Draw crosshair marker
        size = self.snap_marker_size
        painter.drawLine(
            int(view_pos.x() - size),
            int(view_pos.y()),
            int(view_pos.x() + size),
            int(view_pos.y()),
        )
        painter.drawLine(
            int(view_pos.x()),
            int(view_pos.y() - size),
            int(view_pos.x()),
            int(view_pos.y() + size),
        )

        # Draw circle around marker
        painter.drawEllipse(
            int(view_pos.x() - size // 2), int(view_pos.y() - size // 2), size, size
        )

        painter.restore()

    def get_snap_info(self) -> dict:
        """Get current snap engine information."""
        return {
            "enabled_snaps": self.enabled_snaps.value,
            "snap_tolerance": self.snap_tolerance,
            "preview_active": self.preview_active,
            "current_snap": {
                "type": self.current_snap_point.snap_type.name
                if self.current_snap_point
                else None,
                "position": {
                    "x": self.current_snap_point.position.x(),
                    "y": self.current_snap_point.position.y(),
                }
                if self.current_snap_point
                else None,
                "description": self.current_snap_point.description
                if self.current_snap_point
                else None,
            }
            if self.current_snap_point
            else None,
            "custom_snap_count": len(self.custom_snap_points),
        }
