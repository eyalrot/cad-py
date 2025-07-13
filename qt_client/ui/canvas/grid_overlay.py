"""Grid overlay for the CAD drawing canvas."""

import logging
import math
from typing import Optional

from PyQt6.QtCore import Qt, QPointF, QRectF, QSize
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtWidgets import QWidget


logger = logging.getLogger(__name__)


class GridOverlay:
    """Grid overlay for drawing canvas with automatic spacing adjustment."""
    
    def __init__(self, parent: Optional[QWidget] = None):
        self.parent = parent
        
        # Grid properties
        self._major_spacing = 10.0    # Major grid lines spacing in world units
        self._minor_spacing = 1.0     # Minor grid lines spacing in world units
        self._subdivision = 10        # Number of minor lines between major lines
        
        # Visual properties
        self._major_color = QColor(180, 180, 180, 128)
        self._minor_color = QColor(220, 220, 220, 128)
        self._major_width = 1.0
        self._minor_width = 0.5
        
        # Adaptive properties
        self._min_pixel_spacing = 5    # Minimum pixels between grid lines
        self._max_pixel_spacing = 100  # Maximum pixels between grid lines
        
        # Current state
        self._visible = True
        self._current_spacing = self._major_spacing
        self._view_size = QSize(800, 600)
        
        logger.debug("Grid overlay initialized")
    
    @property
    def visible(self) -> bool:
        """Get grid visibility."""
        return self._visible
    
    def setVisible(self, visible: bool):
        """Set grid visibility."""
        self._visible = visible
    
    @property
    def major_spacing(self) -> float:
        """Get major grid spacing."""
        return self._major_spacing
    
    @major_spacing.setter
    def major_spacing(self, spacing: float):
        """Set major grid spacing."""
        if spacing > 0:
            self._major_spacing = spacing
            self._minor_spacing = spacing / self._subdivision
    
    @property
    def minor_spacing(self) -> float:
        """Get minor grid spacing."""
        return self._minor_spacing
    
    def set_colors(self, major_color: QColor, minor_color: QColor):
        """Set grid colors."""
        self._major_color = major_color
        self._minor_color = minor_color
    
    def set_line_widths(self, major_width: float, minor_width: float):
        """Set grid line widths."""
        self._major_width = major_width
        self._minor_width = minor_width
    
    def update_for_zoom(self, zoom_factor: float):
        """Update grid for zoom level."""
        # Calculate pixel spacing at current zoom
        pixel_spacing = self._major_spacing * zoom_factor
        
        # Adjust grid spacing to maintain readable grid
        if pixel_spacing < self._min_pixel_spacing:
            # Zoom out: increase spacing
            while pixel_spacing < self._min_pixel_spacing and self._major_spacing < 10000:
                self._major_spacing *= 10
                pixel_spacing = self._major_spacing * zoom_factor
        elif pixel_spacing > self._max_pixel_spacing:
            # Zoom in: decrease spacing
            while pixel_spacing > self._max_pixel_spacing and self._major_spacing > 0.001:
                self._major_spacing /= 10
                pixel_spacing = self._major_spacing * zoom_factor
        
        # Update minor spacing
        self._minor_spacing = self._major_spacing / self._subdivision
        self._current_spacing = self._major_spacing
        
        logger.debug(f"Grid updated for zoom {zoom_factor:.3f}: major={self._major_spacing}, minor={self._minor_spacing}")
    
    def update_for_view_size(self, size: QSize):
        """Update grid for view size change."""
        self._view_size = size
    
    def snap_to_grid(self, world_pos: QPointF) -> QPointF:
        """Snap world position to grid."""
        if not self._visible:
            return world_pos
        
        # Snap to minor grid
        snap_spacing = self._minor_spacing
        
        snapped_x = round(world_pos.x() / snap_spacing) * snap_spacing
        snapped_y = round(world_pos.y() / snap_spacing) * snap_spacing
        
        return QPointF(snapped_x, snapped_y)
    
    def paint_overlay(self, view):
        """Paint grid overlay on the view."""
        if not self._visible:
            return
        
        # Get painter
        painter = QPainter(view.viewport())
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)  # Grid should be crisp
        
        try:
            # Get visible area in world coordinates
            visible_rect = view.mapToScene(view.rect()).boundingRect()
            
            # Calculate grid bounds with some padding
            padding = max(self._major_spacing * 2, 50)
            grid_rect = visible_rect.adjusted(-padding, -padding, padding, padding)
            
            # Draw minor grid lines
            if self._minor_spacing > 0:
                self._draw_grid_lines(painter, view, grid_rect, self._minor_spacing, 
                                    self._minor_color, self._minor_width)
            
            # Draw major grid lines
            if self._major_spacing > 0:
                self._draw_grid_lines(painter, view, grid_rect, self._major_spacing, 
                                    self._major_color, self._major_width)
            
        except Exception as e:
            logger.warning(f"Error drawing grid overlay: {e}")
        finally:
            painter.end()
    
    def _draw_grid_lines(self, painter: QPainter, view, rect: QRectF, 
                        spacing: float, color: QColor, width: float):
        """Draw grid lines with specified spacing and style."""
        # Create pen
        pen = QPen(color)
        pen.setWidthF(width)
        pen.setCosmetic(True)  # Keep line width constant regardless of zoom
        painter.setPen(pen)
        
        # Calculate line positions
        left = math.floor(rect.left() / spacing) * spacing
        right = math.ceil(rect.right() / spacing) * spacing
        top = math.floor(rect.top() / spacing) * spacing
        bottom = math.ceil(rect.bottom() / spacing) * spacing
        
        # Draw vertical lines
        x = left
        while x <= right:
            # Convert to view coordinates
            start_scene = QPointF(x, rect.top())
            end_scene = QPointF(x, rect.bottom())
            start_view = view.mapFromScene(start_scene)
            end_view = view.mapFromScene(end_scene)
            
            painter.drawLine(start_view, end_view)
            x += spacing
        
        # Draw horizontal lines
        y = top
        while y <= bottom:
            # Convert to view coordinates
            start_scene = QPointF(rect.left(), y)
            end_scene = QPointF(rect.right(), y)
            start_view = view.mapFromScene(start_scene)
            end_view = view.mapFromScene(end_scene)
            
            painter.drawLine(start_view, end_view)
            y += spacing
    
    def get_snap_points_near(self, world_pos: QPointF, radius: float) -> list[QPointF]:
        """Get grid snap points near the specified position."""
        snap_points = []
        
        if not self._visible:
            return snap_points
        
        # Use minor grid for snapping
        spacing = self._minor_spacing
        
        # Calculate grid points in the radius
        steps = int(radius / spacing) + 1
        
        center_x = round(world_pos.x() / spacing) * spacing
        center_y = round(world_pos.y() / spacing) * spacing
        
        for dx in range(-steps, steps + 1):
            for dy in range(-steps, steps + 1):
                point = QPointF(center_x + dx * spacing, center_y + dy * spacing)
                distance = math.sqrt((point.x() - world_pos.x())**2 + (point.y() - world_pos.y())**2)
                
                if distance <= radius:
                    snap_points.append(point)
        
        return snap_points
    
    def is_on_major_grid(self, world_pos: QPointF, tolerance: float = 0.001) -> bool:
        """Check if position is on a major grid line."""
        if not self._visible:
            return False
        
        # Check if position aligns with major grid
        x_remainder = abs(world_pos.x() % self._major_spacing)
        y_remainder = abs(world_pos.y() % self._major_spacing)
        
        return (x_remainder < tolerance or x_remainder > self._major_spacing - tolerance) and \
               (y_remainder < tolerance or y_remainder > self._major_spacing - tolerance)
    
    def get_grid_info(self) -> dict:
        """Get current grid information."""
        return {
            "visible": self._visible,
            "major_spacing": self._major_spacing,
            "minor_spacing": self._minor_spacing,
            "subdivision": self._subdivision,
            "major_color": self._major_color.name(),
            "minor_color": self._minor_color.name()
        }