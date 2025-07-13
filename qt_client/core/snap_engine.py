"""Snap engine for CAD drawing operations with visual feedback."""

import logging
import math
from enum import Enum, auto
from typing import Optional, List, Set, Tuple
from dataclasses import dataclass

from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsRectItem
from PyQt6.QtGui import QPen, QBrush, QColor


logger = logging.getLogger(__name__)


class SnapType(Enum):
    """Types of snap points."""
    ENDPOINT = auto()
    MIDPOINT = auto()
    CENTER = auto()
    INTERSECTION = auto()
    PERPENDICULAR = auto()
    TANGENT = auto()
    QUADRANT = auto()
    NEAREST = auto()
    GRID = auto()


@dataclass
class SnapPoint:
    """Represents a snap point with position and type."""
    position: QPointF
    snap_type: SnapType
    source_item: Optional[QGraphicsItem] = None
    priority: int = 0
    
    def distance_to(self, point: QPointF) -> float:
        """Calculate distance to another point."""
        dx = self.position.x() - point.x()
        dy = self.position.y() - point.y()
        return math.sqrt(dx * dx + dy * dy)


class SnapMarker:
    """Visual marker for snap points."""
    
    # Marker styles for different snap types
    MARKER_STYLES = {
        SnapType.ENDPOINT: {"shape": "square", "color": QColor(255, 0, 0), "size": 8},
        SnapType.MIDPOINT: {"shape": "triangle", "color": QColor(0, 255, 0), "size": 8},
        SnapType.CENTER: {"shape": "circle", "color": QColor(0, 0, 255), "size": 8},
        SnapType.INTERSECTION: {"shape": "x", "color": QColor(255, 255, 0), "size": 10},
        SnapType.PERPENDICULAR: {"shape": "perpendicular", "color": QColor(255, 0, 255), "size": 8},
        SnapType.TANGENT: {"shape": "tangent", "color": QColor(0, 255, 255), "size": 8},
        SnapType.QUADRANT: {"shape": "diamond", "color": QColor(128, 128, 255), "size": 8},
        SnapType.NEAREST: {"shape": "dot", "color": QColor(128, 128, 128), "size": 6},
        SnapType.GRID: {"shape": "plus", "color": QColor(64, 64, 64), "size": 6}
    }
    
    def __init__(self):
        self._current_marker: Optional[QGraphicsItem] = None
        self._current_snap: Optional[SnapPoint] = None
    
    def show_marker(self, scene, snap_point: SnapPoint):
        """Show snap marker at the given snap point."""
        self.hide_marker(scene)
        
        style = self.MARKER_STYLES.get(snap_point.snap_type, self.MARKER_STYLES[SnapType.NEAREST])
        marker = self._create_marker(snap_point.position, style)
        
        if marker:
            scene.addItem(marker)
            self._current_marker = marker
            self._current_snap = snap_point
    
    def hide_marker(self, scene):
        """Hide the current snap marker."""
        if self._current_marker:
            scene.removeItem(self._current_marker)
            self._current_marker = None
            self._current_snap = None
    
    def _create_marker(self, position: QPointF, style: dict) -> Optional[QGraphicsItem]:
        """Create a visual marker based on style."""
        color = style["color"]
        size = style["size"]
        shape = style["shape"]
        
        # Create pen and brush
        pen = QPen(color, 2)
        pen.setCosmetic(True)  # Keep size constant regardless of zoom
        brush = QBrush(color)
        
        # Create marker based on shape
        if shape == "square":
            marker = QGraphicsRectItem(-size/2, -size/2, size, size)
            marker.setPen(pen)
            marker.setBrush(QBrush())  # No fill
        elif shape == "circle":
            marker = QGraphicsEllipseItem(-size/2, -size/2, size, size)
            marker.setPen(pen)
            marker.setBrush(QBrush())
        elif shape == "triangle":
            # Use a simple polygon for triangle
            from PyQt6.QtWidgets import QGraphicsPolygonItem
            from PyQt6.QtGui import QPolygonF
            triangle = QPolygonF([
                QPointF(0, -size/2),
                QPointF(-size/2, size/2),
                QPointF(size/2, size/2)
            ])
            marker = QGraphicsPolygonItem(triangle)
            marker.setPen(pen)
            marker.setBrush(QBrush())
        elif shape == "diamond":
            from PyQt6.QtWidgets import QGraphicsPolygonItem
            from PyQt6.QtGui import QPolygonF
            diamond = QPolygonF([
                QPointF(0, -size/2),
                QPointF(size/2, 0),
                QPointF(0, size/2),
                QPointF(-size/2, 0)
            ])
            marker = QGraphicsPolygonItem(diamond)
            marker.setPen(pen)
            marker.setBrush(QBrush())
        elif shape == "x":
            # Create an X using two lines
            from PyQt6.QtWidgets import QGraphicsItemGroup
            group = QGraphicsItemGroup()
            line1 = QGraphicsLineItem(-size/2, -size/2, size/2, size/2)
            line2 = QGraphicsLineItem(-size/2, size/2, size/2, -size/2)
            line1.setPen(pen)
            line2.setPen(pen)
            group.addToGroup(line1)
            group.addToGroup(line2)
            marker = group
        elif shape == "plus":
            # Create a plus using two lines
            from PyQt6.QtWidgets import QGraphicsItemGroup
            group = QGraphicsItemGroup()
            line1 = QGraphicsLineItem(-size/2, 0, size/2, 0)
            line2 = QGraphicsLineItem(0, -size/2, 0, size/2)
            line1.setPen(pen)
            line2.setPen(pen)
            group.addToGroup(line1)
            group.addToGroup(line2)
            marker = group
        elif shape == "dot":
            marker = QGraphicsEllipseItem(-size/4, -size/4, size/2, size/2)
            marker.setPen(QPen())
            marker.setBrush(brush)
        else:
            # Default to circle
            marker = QGraphicsEllipseItem(-size/2, -size/2, size, size)
            marker.setPen(pen)
            marker.setBrush(QBrush())
        
        if marker:
            marker.setPos(position)
            marker.setZValue(1000)  # Always on top
        
        return marker


class SnapEngine:
    """Engine for detecting and managing snap points."""
    
    # Snap priority order (higher numbers = higher priority)
    SNAP_PRIORITIES = {
        SnapType.INTERSECTION: 100,
        SnapType.ENDPOINT: 90,
        SnapType.CENTER: 80,
        SnapType.QUADRANT: 70,
        SnapType.MIDPOINT: 60,
        SnapType.PERPENDICULAR: 50,
        SnapType.TANGENT: 40,
        SnapType.NEAREST: 30,
        SnapType.GRID: 20
    }
    
    def __init__(self, scene, tolerance: float = 10.0):
        """Initialize snap engine.
        
        Args:
            scene: The graphics scene to search for snap points
            tolerance: Snap tolerance in pixels
        """
        self.scene = scene
        self.tolerance = tolerance
        self.world_tolerance = tolerance  # Will be updated based on zoom
        
        # Active snap types
        self.active_snaps: Set[SnapType] = {
            SnapType.ENDPOINT,
            SnapType.MIDPOINT,
            SnapType.CENTER,
            SnapType.INTERSECTION,
            SnapType.GRID
        }
        
        # Visual feedback
        self.snap_marker = SnapMarker()
        self._show_markers = True
        
        # Current state
        self._last_snap_point: Optional[SnapPoint] = None
        
        logger.info(f"Snap engine initialized with tolerance {tolerance}")
    
    def set_tolerance(self, tolerance: float):
        """Set snap tolerance in pixels."""
        self.tolerance = tolerance
    
    def set_world_tolerance(self, world_tolerance: float):
        """Set snap tolerance in world coordinates."""
        self.world_tolerance = world_tolerance
    
    def enable_snap_type(self, snap_type: SnapType, enabled: bool = True):
        """Enable or disable a specific snap type."""
        if enabled:
            self.active_snaps.add(snap_type)
        else:
            self.active_snaps.discard(snap_type)
        
        logger.debug(f"Snap type {snap_type.name} {'enabled' if enabled else 'disabled'}")
    
    def is_snap_type_active(self, snap_type: SnapType) -> bool:
        """Check if a snap type is active."""
        return snap_type in self.active_snaps
    
    def set_show_markers(self, show: bool):
        """Enable or disable visual snap markers."""
        self._show_markers = show
        if not show:
            self.hide_snap_marker()
    
    def find_snap_point(self, cursor_pos: QPointF, view_scale: float = 1.0) -> Optional[SnapPoint]:
        """Find the best snap point near the cursor position.
        
        Args:
            cursor_pos: Cursor position in scene coordinates
            view_scale: Current view scale factor for tolerance adjustment
            
        Returns:
            Best snap point or None if no snap found
        """
        # Adjust tolerance based on view scale
        self.world_tolerance = self.tolerance / view_scale
        
        # Create search rectangle
        search_rect = QRectF(
            cursor_pos.x() - self.world_tolerance,
            cursor_pos.y() - self.world_tolerance,
            self.world_tolerance * 2,
            self.world_tolerance * 2
        )
        
        # Find all potential snap points
        snap_points = []
        
        # Get items in search area
        items = self.scene.items(search_rect)
        
        for item in items:
            item_snaps = self._get_item_snap_points(item, cursor_pos)
            snap_points.extend(item_snaps)
        
        # Add grid snap if enabled
        if SnapType.GRID in self.active_snaps:
            grid_snap = self._get_grid_snap_point(cursor_pos)
            if grid_snap:
                snap_points.append(grid_snap)
        
        # Find intersections if enabled
        if SnapType.INTERSECTION in self.active_snaps:
            intersection_snaps = self._find_intersections(cursor_pos, items)
            snap_points.extend(intersection_snaps)
        
        # Filter snap points by tolerance
        valid_snaps = [
            sp for sp in snap_points 
            if sp.distance_to(cursor_pos) <= self.world_tolerance
        ]
        
        if not valid_snaps:
            return None
        
        # Sort by priority and distance
        def snap_priority(snap_point: SnapPoint) -> Tuple[int, float]:
            priority = self.SNAP_PRIORITIES.get(snap_point.snap_type, 0)
            distance = snap_point.distance_to(cursor_pos)
            return (-priority, distance)  # Negative priority for descending order
        
        valid_snaps.sort(key=snap_priority)
        
        return valid_snaps[0]
    
    def _get_item_snap_points(self, item: QGraphicsItem, cursor_pos: QPointF) -> List[SnapPoint]:
        """Get snap points for a specific graphics item."""
        snap_points = []
        
        if isinstance(item, QGraphicsLineItem):
            snap_points.extend(self._get_line_snap_points(item))
        elif isinstance(item, QGraphicsEllipseItem):
            snap_points.extend(self._get_ellipse_snap_points(item))
        elif isinstance(item, QGraphicsRectItem):
            snap_points.extend(self._get_rect_snap_points(item))
        
        return snap_points
    
    def _get_line_snap_points(self, line_item: QGraphicsLineItem) -> List[SnapPoint]:
        """Get snap points for a line item."""
        snap_points = []
        line = line_item.line()
        
        # Transform line to scene coordinates
        scene_line = line_item.mapToScene(line)
        start_point = scene_line.p1() if hasattr(scene_line, 'p1') else scene_line[0]
        end_point = scene_line.p2() if hasattr(scene_line, 'p2') else scene_line[1]
        
        # Endpoints
        if SnapType.ENDPOINT in self.active_snaps:
            snap_points.append(SnapPoint(start_point, SnapType.ENDPOINT, line_item))
            snap_points.append(SnapPoint(end_point, SnapType.ENDPOINT, line_item))
        
        # Midpoint
        if SnapType.MIDPOINT in self.active_snaps:
            mid_x = (start_point.x() + end_point.x()) / 2
            mid_y = (start_point.y() + end_point.y()) / 2
            snap_points.append(SnapPoint(QPointF(mid_x, mid_y), SnapType.MIDPOINT, line_item))
        
        return snap_points
    
    def _get_ellipse_snap_points(self, ellipse_item: QGraphicsEllipseItem) -> List[SnapPoint]:
        """Get snap points for an ellipse/circle item."""
        snap_points = []
        rect = ellipse_item.rect()
        
        # Transform to scene coordinates
        scene_rect = ellipse_item.mapRectToScene(rect)
        center = scene_rect.center()
        
        # Center
        if SnapType.CENTER in self.active_snaps:
            snap_points.append(SnapPoint(center, SnapType.CENTER, ellipse_item))
        
        # Quadrants (top, right, bottom, left)
        if SnapType.QUADRANT in self.active_snaps:
            rx = scene_rect.width() / 2
            ry = scene_rect.height() / 2
            
            quadrants = [
                QPointF(center.x(), center.y() - ry),  # Top
                QPointF(center.x() + rx, center.y()),  # Right
                QPointF(center.x(), center.y() + ry),  # Bottom
                QPointF(center.x() - rx, center.y())   # Left
            ]
            
            for point in quadrants:
                snap_points.append(SnapPoint(point, SnapType.QUADRANT, ellipse_item))
        
        return snap_points
    
    def _get_rect_snap_points(self, rect_item: QGraphicsRectItem) -> List[SnapPoint]:
        """Get snap points for a rectangle item."""
        snap_points = []
        rect = rect_item.rect()
        
        # Transform to scene coordinates
        scene_rect = rect_item.mapRectToScene(rect)
        
        # Corners (endpoints)
        if SnapType.ENDPOINT in self.active_snaps:
            corners = [
                scene_rect.topLeft(),
                scene_rect.topRight(),
                scene_rect.bottomLeft(),
                scene_rect.bottomRight()
            ]
            
            for corner in corners:
                snap_points.append(SnapPoint(corner, SnapType.ENDPOINT, rect_item))
        
        # Center
        if SnapType.CENTER in self.active_snaps:
            snap_points.append(SnapPoint(scene_rect.center(), SnapType.CENTER, rect_item))
        
        # Midpoints of sides
        if SnapType.MIDPOINT in self.active_snaps:
            midpoints = [
                QPointF(scene_rect.center().x(), scene_rect.top()),     # Top
                QPointF(scene_rect.right(), scene_rect.center().y()),   # Right
                QPointF(scene_rect.center().x(), scene_rect.bottom()),  # Bottom
                QPointF(scene_rect.left(), scene_rect.center().y())     # Left
            ]
            
            for midpoint in midpoints:
                snap_points.append(SnapPoint(midpoint, SnapType.MIDPOINT, rect_item))
        
        return snap_points
    
    def _get_grid_snap_point(self, cursor_pos: QPointF) -> Optional[SnapPoint]:
        """Get grid snap point if grid snapping is enabled."""
        # This would integrate with the grid overlay system
        # For now, return a simple grid snap
        grid_spacing = 1.0  # Default grid spacing
        
        snapped_x = round(cursor_pos.x() / grid_spacing) * grid_spacing
        snapped_y = round(cursor_pos.y() / grid_spacing) * grid_spacing
        
        grid_point = QPointF(snapped_x, snapped_y)
        
        # Only return if close enough to cursor
        distance = math.sqrt(
            (grid_point.x() - cursor_pos.x()) ** 2 + 
            (grid_point.y() - cursor_pos.y()) ** 2
        )
        
        if distance <= self.world_tolerance:
            return SnapPoint(grid_point, SnapType.GRID)
        
        return None
    
    def _find_intersections(self, cursor_pos: QPointF, items: List[QGraphicsItem]) -> List[SnapPoint]:
        """Find intersection points between items."""
        intersection_points = []
        
        # Simple implementation - can be enhanced for more complex intersections
        lines = [item for item in items if isinstance(item, QGraphicsLineItem)]
        
        for i, line1 in enumerate(lines):
            for line2 in lines[i+1:]:
                intersection = self._line_intersection(line1, line2)
                if intersection and intersection.distance_to(cursor_pos) <= self.world_tolerance:
                    intersection_points.append(SnapPoint(intersection, SnapType.INTERSECTION))
        
        return intersection_points
    
    def _line_intersection(self, line1: QGraphicsLineItem, line2: QGraphicsLineItem) -> Optional[QPointF]:
        """Calculate intersection point between two lines."""
        try:
            # Get lines in scene coordinates
            scene_line1 = line1.mapToScene(line1.line())
            scene_line2 = line2.mapToScene(line2.line())
            
            # Extract points
            p1 = scene_line1.p1() if hasattr(scene_line1, 'p1') else scene_line1[0]
            p2 = scene_line1.p2() if hasattr(scene_line1, 'p2') else scene_line1[1]
            p3 = scene_line2.p1() if hasattr(scene_line2, 'p1') else scene_line2[0]
            p4 = scene_line2.p2() if hasattr(scene_line2, 'p2') else scene_line2[1]
            
            # Calculate intersection using line equation
            denom = (p1.x() - p2.x()) * (p3.y() - p4.y()) - (p1.y() - p2.y()) * (p3.x() - p4.x())
            
            if abs(denom) < 1e-10:  # Lines are parallel
                return None
            
            t = ((p1.x() - p3.x()) * (p3.y() - p4.y()) - (p1.y() - p3.y()) * (p3.x() - p4.x())) / denom
            
            # Calculate intersection point
            intersection_x = p1.x() + t * (p2.x() - p1.x())
            intersection_y = p1.y() + t * (p2.y() - p1.y())
            
            return QPointF(intersection_x, intersection_y)
            
        except Exception as e:
            logger.debug(f"Error calculating line intersection: {e}")
            return None
    
    def show_snap_marker(self, snap_point: SnapPoint):
        """Show visual marker for snap point."""
        if self._show_markers:
            self.snap_marker.show_marker(self.scene, snap_point)
            self._last_snap_point = snap_point
    
    def hide_snap_marker(self):
        """Hide the current snap marker."""
        self.snap_marker.hide_marker(self.scene)
        self._last_snap_point = None
    
    def get_current_snap_point(self) -> Optional[SnapPoint]:
        """Get the currently active snap point."""
        return self._last_snap_point
    
    def clear_all_markers(self):
        """Clear all snap markers."""
        self.hide_snap_marker()
    
    def get_snap_settings(self) -> dict:
        """Get current snap settings."""
        return {
            "tolerance": self.tolerance,
            "active_snaps": [snap_type.name for snap_type in self.active_snaps],
            "show_markers": self._show_markers
        }
    
    def apply_snap_settings(self, settings: dict):
        """Apply snap settings."""
        if "tolerance" in settings:
            self.set_tolerance(settings["tolerance"])
        
        if "active_snaps" in settings:
            self.active_snaps.clear()
            for snap_name in settings["active_snaps"]:
                try:
                    snap_type = SnapType[snap_name]
                    self.active_snaps.add(snap_type)
                except KeyError:
                    logger.warning(f"Unknown snap type: {snap_name}")
        
        if "show_markers" in settings:
            self.set_show_markers(settings["show_markers"])