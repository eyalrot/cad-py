"""
Enhanced CAD canvas view with integrated grid and ruler systems.

This module provides a complete CAD drawing view with grid overlay,
rulers, snap functionality, and tool integration.
"""

import logging
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent, QPainter, QWheelEvent
from PySide6.QtWidgets import QGraphicsScene, QGraphicsView

from ...graphics.snap_engine import SnapEngine
from ...graphics.tools.tool_manager import ToolManager
from .grid_overlay import GridOverlay
from .ruler_overlay import RulerGuides, RulerOverlay

logger = logging.getLogger(__name__)


class CADCanvasView(QGraphicsView):
    """
    Enhanced CAD canvas view with integrated grid, rulers, and drawing tools.

    Features:
    - Grid overlay with adaptive spacing
    - Horizontal and vertical rulers
    - Ruler guides for alignment
    - Tool integration with snap support
    - Zoom and pan controls
    - Coordinate display
    """

    # Signals
    coordinates_changed = Signal(float, float)  # x, y world coordinates
    zoom_changed = Signal(float)  # zoom factor
    view_changed = Signal()  # view area changed

    def __init__(self, scene: QGraphicsScene, parent=None):
        super().__init__(scene, parent)

        # Initialize components
        self.grid_overlay = GridOverlay(self)
        self.ruler_overlay = RulerOverlay(self)
        self.ruler_guides = RulerGuides(self)
        self.snap_engine = SnapEngine(self)
        self.tool_manager: Optional[ToolManager] = None

        # View properties
        self.zoom_factor = 1.0
        self.min_zoom = 0.01
        self.max_zoom = 100.0
        self.zoom_step = 1.2

        # Interaction state
        self.pan_active = False
        self.last_pan_point = QPointF()
        self.guide_drag_active = False
        self.dragged_guide = None

        # Setup view
        self.setup_view()
        self.connect_signals()
        self.setup_snap_engine()

        logger.debug("CAD canvas view initialized")

    def setup_view(self):
        """Setup view properties and rendering."""
        # Configure view
        self.setDragMode(QGraphicsView.NoDrag)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.TextAntialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # Enable mouse tracking for coordinate display
        self.setMouseTracking(True)

        # Set focus policy for keyboard events
        self.setFocusPolicy(Qt.StrongFocus)

        # Initial viewport setup
        self.centerOn(0, 0)
        self.scale(1.0, -1.0)  # Flip Y-axis for standard CAD coordinates

    def connect_signals(self):
        """Connect internal signals."""
        self.grid_overlay.grid_changed.connect(self.update)
        self.ruler_overlay.ruler_changed.connect(self.update)
        self.ruler_guides.guide_added.connect(self.update)
        self.ruler_guides.guide_removed.connect(self.update)
        self.ruler_guides.guide_moved.connect(self.update)

    def set_tool_manager(self, tool_manager: ToolManager):
        """Set the tool manager for event routing."""
        self.tool_manager = tool_manager
        # Connect snap engine to tool manager if needed
        if hasattr(tool_manager, "set_snap_engine"):
            tool_manager.set_snap_engine(self.snap_engine)

    def setup_snap_engine(self):
        """Setup snap engine with references."""
        self.snap_engine.set_grid_overlay(self.grid_overlay)
        self.snap_engine.set_ruler_guides(self.ruler_guides)
        self.snap_engine.set_scene(self.scene())

    # View control methods
    def zoom_in(self):
        """Zoom in by zoom step."""
        new_zoom = min(self.zoom_factor * self.zoom_step, self.max_zoom)
        self.set_zoom(new_zoom)

    def zoom_out(self):
        """Zoom out by zoom step."""
        new_zoom = max(self.zoom_factor / self.zoom_step, self.min_zoom)
        self.set_zoom(new_zoom)

    def zoom_to_fit(self):
        """Zoom to fit all content."""
        scene_rect = self.scene().itemsBoundingRect()
        if not scene_rect.isEmpty():
            self.fitInView(scene_rect, Qt.KeepAspectRatio)
            self._update_zoom_from_transform()

    def zoom_to_selection(self):
        """Zoom to fit selected items."""
        selected_items = self.scene().selectedItems()
        if selected_items:
            # Calculate bounding rect of selected items
            bounds = QRectF()
            for item in selected_items:
                bounds = bounds.united(item.boundingRect())

            if not bounds.isEmpty():
                # Add some padding
                padding = max(bounds.width(), bounds.height()) * 0.1
                bounds.adjust(-padding, -padding, padding, padding)
                self.fitInView(bounds, Qt.KeepAspectRatio)
                self._update_zoom_from_transform()

    def set_zoom(self, zoom: float):
        """Set specific zoom level."""
        zoom = max(self.min_zoom, min(self.max_zoom, zoom))

        if abs(zoom - self.zoom_factor) > 1e-6:
            # Get center point in scene coordinates
            center_scene = self.mapToScene(self.rect().center())

            # Reset transform and apply new zoom
            self.resetTransform()
            self.scale(zoom, -zoom)  # Negative Y for CAD coordinates

            # Center on the same point
            self.centerOn(center_scene)

            # Update zoom factor
            self.zoom_factor = zoom

            # Update overlays for new zoom
            self._update_overlays_for_zoom()

            # Emit signals
            self.zoom_changed.emit(zoom)
            self.view_changed.emit()

    def _update_zoom_from_transform(self):
        """Update zoom factor from current transform."""
        transform = self.transform()
        self.zoom_factor = abs(transform.m11())  # X-scale factor
        self._update_overlays_for_zoom()
        self.zoom_changed.emit(self.zoom_factor)
        self.view_changed.emit()

    def _update_overlays_for_zoom(self):
        """Update overlays for current zoom level."""
        self.grid_overlay.update_for_zoom(self.zoom_factor)
        self.ruler_overlay.update_for_zoom(self.zoom_factor)

    # Grid and ruler access methods
    def get_grid_overlay(self) -> GridOverlay:
        """Get grid overlay instance."""
        return self.grid_overlay

    def get_ruler_overlay(self) -> RulerOverlay:
        """Get ruler overlay instance."""
        return self.ruler_overlay

    def get_ruler_guides(self) -> RulerGuides:
        """Get ruler guides instance."""
        return self.ruler_guides

    def get_snap_engine(self) -> SnapEngine:
        """Get snap engine instance."""
        return self.snap_engine

    def toggle_grid(self):
        """Toggle grid visibility."""
        self.grid_overlay.setVisible(not self.grid_overlay.visible)
        self.update()

    def toggle_rulers(self):
        """Toggle ruler visibility."""
        self.ruler_overlay.set_visible(not self.ruler_overlay.visible)
        self.update()

    def snap_to_grid(self, world_point: QPointF) -> QPointF:
        """Snap world point to grid."""
        return self.grid_overlay.snap_to_grid(world_point)

    def snap_point(self, world_point: QPointF, exclude_point: Optional[QPointF] = None):
        """Snap world point using all enabled snap modes."""
        return self.snap_engine.snap_point(world_point, self, exclude_point)

    # Event handlers
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events."""
        world_pos = self.mapToScene(event.pos())

        # Check for ruler guide interaction
        if event.button() == Qt.LeftButton:
            guide_hit = self.ruler_guides.hit_test_guides(world_pos, 1.0)
            if guide_hit:
                self.guide_drag_active = True
                self.dragged_guide = guide_hit
                return

        # Check for middle mouse pan
        if event.button() == Qt.MiddleButton:
            self.pan_active = True
            self.last_pan_point = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            return

        # Route to tool manager
        if self.tool_manager:
            if self.tool_manager.route_mouse_press(event):
                return

        # Default handling
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move events."""
        world_pos = self.mapToScene(event.pos())

        # Update coordinate display
        self.coordinates_changed.emit(world_pos.x(), world_pos.y())

        # Handle guide dragging
        if self.guide_drag_active and self.dragged_guide:
            orientation, index = self.dragged_guide
            if orientation == "horizontal":
                old_pos = self.ruler_guides.horizontal_guides[index]
                self.ruler_guides.horizontal_guides[index] = world_pos.y()
                self.ruler_guides.guide_moved.emit("horizontal", old_pos, world_pos.y())
            elif orientation == "vertical":
                old_pos = self.ruler_guides.vertical_guides[index]
                self.ruler_guides.vertical_guides[index] = world_pos.x()
                self.ruler_guides.guide_moved.emit("vertical", old_pos, world_pos.x())
            self.update()
            return

        # Handle panning
        if self.pan_active:
            delta = event.pos() - self.last_pan_point
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            self.last_pan_point = event.pos()
            return

        # Route to tool manager
        if self.tool_manager:
            if self.tool_manager.route_mouse_move(event):
                return

        # Default handling
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release events."""
        # Handle guide dragging
        if self.guide_drag_active:
            self.guide_drag_active = False
            self.dragged_guide = None
            return

        # Handle panning
        if self.pan_active and event.button() == Qt.MiddleButton:
            self.pan_active = False
            self.setCursor(Qt.ArrowCursor)
            return

        # Route to tool manager
        if self.tool_manager:
            if self.tool_manager.route_mouse_release(event):
                return

        # Default handling
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel events for zooming."""
        # Get zoom direction
        delta = event.angleDelta().y()

        if delta > 0:
            zoom_factor = self.zoom_step
        else:
            zoom_factor = 1.0 / self.zoom_step

        # Get mouse position in scene coordinates before zoom
        scene_pos = self.mapToScene(event.position().toPoint())

        # Apply zoom
        new_zoom = self.zoom_factor * zoom_factor
        new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))

        if abs(new_zoom - self.zoom_factor) > 1e-6:
            # Reset transform and apply new zoom
            self.resetTransform()
            self.scale(new_zoom, -new_zoom)

            # Keep mouse position at same scene location
            self.centerOn(scene_pos)

            # Update zoom factor
            self.zoom_factor = new_zoom

            # Update overlays
            self._update_overlays_for_zoom()

            # Emit signals
            self.zoom_changed.emit(new_zoom)
            self.view_changed.emit()

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events."""
        # View control keys
        if event.key() == Qt.Key_Plus or event.key() == Qt.Key_Equal:
            self.zoom_in()
            return
        elif event.key() == Qt.Key_Minus:
            self.zoom_out()
            return
        elif event.key() == Qt.Key_0:
            self.set_zoom(1.0)
            return
        elif event.key() == Qt.Key_F:
            self.zoom_to_fit()
            return
        elif event.key() == Qt.Key_G:
            self.toggle_grid()
            return
        elif event.key() == Qt.Key_R:
            self.toggle_rulers()
            return

        # Route to tool manager
        if self.tool_manager:
            if self.tool_manager.route_key_press(event):
                return

        # Default handling
        super().keyPressEvent(event)

    def paintEvent(self, event):
        """Paint the view with overlays."""
        # Paint the scene first
        super().paintEvent(event)

        # Create painter for overlays
        painter = QPainter(self.viewport())

        try:
            # Get visible scene rect
            visible_rect = self.mapToScene(self.rect()).boundingRect()

            # Paint grid overlay
            if self.grid_overlay.visible:
                self.grid_overlay.paint_overlay(self)

            # Paint ruler guides
            self.ruler_guides.paint_guides(painter, self, visible_rect)

            # Paint rulers on top
            if self.ruler_overlay.visible:
                self.ruler_overlay.paint_rulers(painter, self)

            # Paint snap feedback
            self.snap_engine.paint_snap_feedback(painter, self, visible_rect)

        except Exception as e:
            logger.warning(f"Error painting overlays: {e}")
        finally:
            painter.end()

    def resizeEvent(self, event):
        """Handle view resize."""
        super().resizeEvent(event)

        # Update overlays for new size
        new_size = event.size()
        self.grid_overlay.update_for_view_size(new_size)
        self.ruler_overlay.update_for_view_size(new_size)

        self.view_changed.emit()

    def get_view_info(self) -> dict:
        """Get current view information."""
        visible_rect = self.mapToScene(self.rect()).boundingRect()

        return {
            "zoom_factor": self.zoom_factor,
            "center": {"x": visible_rect.center().x(), "y": visible_rect.center().y()},
            "visible_rect": {
                "left": visible_rect.left(),
                "top": visible_rect.top(),
                "width": visible_rect.width(),
                "height": visible_rect.height(),
            },
            "grid_info": self.grid_overlay.get_grid_info(),
            "ruler_info": self.ruler_overlay.get_ruler_info(),
            "guides": {
                "horizontal": self.ruler_guides.horizontal_guides.copy(),
                "vertical": self.ruler_guides.vertical_guides.copy(),
            },
            "snap_info": self.snap_engine.get_snap_info(),
        }
