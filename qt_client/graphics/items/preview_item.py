"""Preview item for showing temporary geometry during tool operations."""

from typing import List, Optional
from PySide6.QtCore import QRectF
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtWidgets import QGraphicsItem

from backend.core.geometry.point import Point2D


class PreviewItem(QGraphicsItem):
    """Graphics item for displaying preview geometry during tool operations."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.preview_geometry = []
        self.preview_pen = QPen(QColor(100, 150, 255), 1.5)
        from PySide6.QtCore import Qt
        self.preview_pen.setStyle(Qt.PenStyle.DashLine)  # Dashed line
        
    def add_line(self, start_point: Point2D, end_point: Point2D):
        """Add a line to the preview."""
        self.preview_geometry.append({
            'type': 'line',
            'start': start_point,
            'end': end_point
        })
        self.update()
        
    def add_circle(self, center: Point2D, radius: float):
        """Add a circle to the preview."""
        self.preview_geometry.append({
            'type': 'circle',
            'center': center,
            'radius': radius
        })
        self.update()
        
    def clear(self):
        """Clear all preview geometry."""
        self.preview_geometry.clear()
        self.update()
        
    def boundingRect(self) -> QRectF:
        """Return the bounding rectangle of the preview."""
        if not self.preview_geometry:
            return QRectF()
            
        # Calculate bounds from preview geometry
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for geom in self.preview_geometry:
            if geom['type'] == 'line':
                start, end = geom['start'], geom['end']
                min_x = min(min_x, start.x, end.x)
                max_x = max(max_x, start.x, end.x)
                min_y = min(min_y, start.y, end.y)
                max_y = max(max_y, start.y, end.y)
            elif geom['type'] == 'circle':
                center, radius = geom['center'], geom['radius']
                min_x = min(min_x, center.x - radius)
                max_x = max(max_x, center.x + radius)
                min_y = min(min_y, center.y - radius)
                max_y = max(max_y, center.y + radius)
                
        if min_x == float('inf'):
            return QRectF()
            
        return QRectF(min_x, min_y, max_x - min_x, max_y - min_y)
        
    def paint(self, painter: QPainter, option, widget=None):
        """Paint the preview geometry."""
        painter.setPen(self.preview_pen)
        
        for geom in self.preview_geometry:
            if geom['type'] == 'line':
                start, end = geom['start'], geom['end']
                painter.drawLine(start.x, start.y, end.x, end.y)
            elif geom['type'] == 'circle':
                center, radius = geom['center'], geom['radius']
                painter.drawEllipse(
                    center.x - radius, center.y - radius,
                    radius * 2, radius * 2
                )