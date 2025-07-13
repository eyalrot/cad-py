"""CAD drawing view based on QGraphicsView."""

import logging
import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPen,
    QTransform,
    QWheelEvent,
)
from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsView

from qt_client.core.selection_manager import SelectionManager, SelectionMode
from qt_client.core.snap_engine import SnapEngine, SnapPoint
from qt_client.ui.canvas.cad_scene import CADScene
from qt_client.ui.canvas.grid_overlay import GridOverlay

logger = logging.getLogger(__name__)


class CADView(QGraphicsView):
    """CAD drawing view with pan, zoom, and coordinate tracking."""

    # Signals
    mouse_moved = Signal(QPointF)  # World coordinates
    zoom_changed = Signal(float)  # Zoom factor
    selection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create scene
        self._scene = CADScene(self)
        self.setScene(self._scene)

        # View properties
        self._zoom_factor = 1.0
        self._min_zoom = 0.01
        self._max_zoom = 100.0
        self._pan_speed = 1.0

        # Grid and snap
        self._grid_overlay: Optional[GridOverlay] = None
        self._grid_visible = True
        self._snap_enabled = True
        self._snap_distance = 10.0  # Pixels

        # Snap engine
        self._snap_engine: Optional[SnapEngine] = None

        # Selection manager
        self._selection_manager: Optional[SelectionManager] = None

        # Mouse interaction
        self._last_mouse_pos = QPointF()
        self._middle_button_pressed = False
        self._space_pressed = False
        self._left_button_pressed = False
        self._selection_start_pos: Optional[QPointF] = None

        # Setup view
        self._setup_view()
        self._setup_grid()
        self._setup_snap_engine()
        self._setup_selection_manager()

        logger.info("CAD view initialized")

    def _setup_view(self):
        """Setup view properties."""
        # Enable antialiasing
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # Set view properties
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Set background
        self.setBackgroundBrush(QBrush(QColor(250, 250, 250)))

        # Set scene rect to large area
        scene_size = 100000  # 100 units in each direction
        scene_rect = QRectF(-scene_size / 2, -scene_size / 2, scene_size, scene_size)
        self._scene.setSceneRect(scene_rect)

        # Center view
        self.centerOn(0, 0)

    def _setup_grid(self):
        """Setup grid overlay."""
        self._grid_overlay = GridOverlay(self)
        self._grid_overlay.setVisible(self._grid_visible)

    def _setup_snap_engine(self):
        """Setup snap engine."""
        self._snap_engine = SnapEngine(self._scene, self._snap_distance)
        self._snap_engine.set_show_markers(self._snap_enabled)

    def _setup_selection_manager(self):
        """Setup selection manager."""
        self._selection_manager = SelectionManager(self._scene, self)

        # Connect selection signals
        self._selection_manager.selection_changed.connect(self.selection_changed)

        # Set initial selection mode
        self._selection_manager.selection_mode = SelectionMode.SINGLE

    @property
    def zoom_factor(self) -> float:
        """Get current zoom factor."""
        return self._zoom_factor

    @property
    def grid_visible(self) -> bool:
        """Get grid visibility."""
        return self._grid_visible

    @grid_visible.setter
    def grid_visible(self, visible: bool):
        """Set grid visibility."""
        self._grid_visible = visible
        if self._grid_overlay:
            self._grid_overlay.setVisible(visible)
        self.update()

    @property
    def snap_enabled(self) -> bool:
        """Get snap enabled state."""
        return self._snap_enabled

    @snap_enabled.setter
    def snap_enabled(self, enabled: bool):
        """Set snap enabled state."""
        self._snap_enabled = enabled
        if self._snap_engine:
            self._snap_engine.set_show_markers(enabled)

    def map_to_world(self, view_pos: QPointF) -> QPointF:
        """Map view coordinates to world coordinates."""
        return self.mapToScene(view_pos.toPoint())

    def map_to_view(self, world_pos: QPointF) -> QPointF:
        """Map world coordinates to view coordinates."""
        return QPointF(self.mapFromScene(world_pos))

    def snap_to_grid(self, world_pos: QPointF) -> QPointF:
        """Snap world position to grid if snap is enabled."""
        if not self._snap_enabled or not self._grid_overlay:
            return world_pos

        return self._grid_overlay.snap_to_grid(world_pos)

    def find_snap_point(self, world_pos: QPointF) -> Optional[SnapPoint]:
        """Find snap point near the given world position."""
        if not self._snap_enabled or not self._snap_engine:
            return None

        return self._snap_engine.find_snap_point(world_pos, self.get_view_scale())

    def show_snap_feedback(self, world_pos: QPointF) -> Optional[QPointF]:
        """Show snap feedback and return snapped position."""
        if not self._snap_enabled or not self._snap_engine:
            return world_pos

        # Find snap point
        snap_point = self._snap_engine.find_snap_point(world_pos, self.get_view_scale())

        if snap_point:
            # Show visual feedback
            self._snap_engine.show_snap_marker(snap_point)
            return snap_point.position
        else:
            # Hide snap marker if no snap found
            self._snap_engine.hide_snap_marker()
            return world_pos

    def hide_snap_feedback(self):
        """Hide snap feedback markers."""
        if self._snap_engine:
            self._snap_engine.hide_snap_marker()

    def zoom_in(self, factor: float = 1.25):
        """Zoom in by the specified factor."""
        self.zoom_by_factor(factor)

    def zoom_out(self, factor: float = 0.8):
        """Zoom out by the specified factor."""
        self.zoom_by_factor(factor)

    def zoom_by_factor(self, factor: float):
        """Zoom by the specified factor."""
        new_zoom = self._zoom_factor * factor
        new_zoom = max(self._min_zoom, min(self._max_zoom, new_zoom))

        if new_zoom != self._zoom_factor:
            # Apply zoom
            scale_factor = new_zoom / self._zoom_factor
            self.scale(scale_factor, scale_factor)

            self._zoom_factor = new_zoom
            self.zoom_changed.emit(self._zoom_factor)

            # Update grid if visible
            if self._grid_overlay:
                self._grid_overlay.update_for_zoom(self._zoom_factor)

    def zoom_to_rect(self, rect: QRectF):
        """Zoom to fit the specified rectangle."""
        if rect.isEmpty():
            return

        # Add margin
        margin = 0.1  # 10% margin
        expanded_rect = rect.adjusted(
            -rect.width() * margin,
            -rect.height() * margin,
            rect.width() * margin,
            rect.height() * margin,
        )

        # Fit in view
        self.fitInView(expanded_rect, Qt.AspectRatioMode.KeepAspectRatio)

        # Update zoom factor
        transform = self.transform()
        self._zoom_factor = transform.m11()  # Assuming uniform scaling
        self.zoom_changed.emit(self._zoom_factor)

        if self._grid_overlay:
            self._grid_overlay.update_for_zoom(self._zoom_factor)

    def zoom_fit(self):
        """Zoom to fit all items in the scene."""
        items_rect = self._scene.itemsBoundingRect()

        if items_rect.isEmpty():
            # No items, zoom to reasonable area around origin
            items_rect = QRectF(-50, -50, 100, 100)

        self.zoom_to_rect(items_rect)

    def zoom_to_actual_size(self):
        """Zoom to actual size (1:1)."""
        # Reset transform
        self.resetTransform()
        self._zoom_factor = 1.0
        self.zoom_changed.emit(self._zoom_factor)

        if self._grid_overlay:
            self._grid_overlay.update_for_zoom(self._zoom_factor)

    def pan_to(self, world_pos: QPointF):
        """Pan to center on the specified world position."""
        self.centerOn(world_pos)

    def pan_by(self, delta: QPointF):
        """Pan by the specified delta in view coordinates."""
        # Convert delta to scene coordinates
        scene_delta = self.mapToScene(delta.toPoint()) - self.mapToScene(
            QPointF(0, 0).toPoint()
        )

        # Move scene rect
        current_center = self.mapToScene(self.rect().center())
        new_center = current_center - scene_delta
        self.centerOn(new_center)

    # Event handlers
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel zoom."""
        if event.angleDelta().y() == 0:
            return

        # Get zoom factor
        zoom_in = event.angleDelta().y() > 0
        factor = 1.25 if zoom_in else 0.8

        # Zoom around mouse cursor
        old_pos = self.mapToScene(event.position().toPoint())

        self.zoom_by_factor(factor)

        # Keep mouse position in same place
        new_pos = self.mapToScene(event.position().toPoint())
        delta = new_pos - old_pos
        self.pan_by(QPointF(delta))

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press events."""
        self._last_mouse_pos = event.position()
        world_pos = self.mapToScene(event.position().toPoint())

        if event.button() == Qt.MouseButton.MiddleButton or self._space_pressed:
            # Start panning
            self._middle_button_pressed = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton:
            # Handle selection
            self._left_button_pressed = True
            self._selection_start_pos = world_pos

            # Check if clicking on an existing selected item for potential move
            clicked_item = None
            items = self._scene.items(world_pos)
            for item in items:
                if (
                    item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
                    and item.zValue() <= 900
                ):  # Skip helper items
                    clicked_item = item
                    break

            # If not clicking on a selected item, start new selection
            if not clicked_item or not self._selection_manager.is_item_selected(
                clicked_item
            ):
                modifiers = event.modifiers()
                self._selection_manager.pick_select(world_pos, modifiers)

            event.accept()
        else:
            # Pass to scene
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move events."""
        current_pos = event.position()
        world_pos = self.mapToScene(current_pos.toPoint())

        # Handle panning
        if self._middle_button_pressed:
            delta = current_pos - self._last_mouse_pos
            self.pan_by(delta)
            event.accept()
        # Handle window selection
        elif self._left_button_pressed and self._selection_start_pos:
            # Check if we should start window selection (minimum drag distance)
            start_view_pos = self.mapFromScene(self._selection_start_pos)
            delta = (current_pos - start_view_pos).manhattanLength()

            if delta > 5:  # Minimum drag distance in pixels
                # Start/update window selection
                if not self._selection_manager._is_selecting:
                    self._selection_manager.start_window_selection(
                        self._selection_start_pos
                    )
                else:
                    self._selection_manager.update_window_selection(world_pos)
            event.accept()
        else:
            # Show snap feedback and get snapped position
            snapped_pos = self.show_snap_feedback(world_pos)
            self.mouse_moved.emit(snapped_pos)
            super().mouseMoveEvent(event)

        self._last_mouse_pos = current_pos

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self._middle_button_pressed = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton:
            self._left_button_pressed = False

            # Finish window selection if active
            if self._selection_manager._is_selecting:
                modifiers = event.modifiers()
                self._selection_manager.finish_window_selection(modifiers)

            # Reset selection state
            self._selection_start_pos = None
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events."""
        if event.key() == Qt.Key.Key_Space:
            self._space_pressed = True
            if not self._middle_button_pressed:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            # Cancel current operation or clear selection
            if self._selection_manager and self._selection_manager._is_selecting:
                self._selection_manager.cancel_window_selection()
            else:
                self.clear_selection()
            event.accept()
        elif (
            event.key() == Qt.Key.Key_A
            and event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            # Ctrl+A: Select all
            self.select_all()
            event.accept()
        elif event.key() == Qt.Key.Key_Delete:
            # Delete selected items
            if self._selection_manager:
                self._selection_manager.delete_selection()
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        """Handle key release events."""
        if event.key() == Qt.Key.Key_Space:
            self._space_pressed = False
            if not self._middle_button_pressed:
                self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def paintEvent(self, event):
        """Custom paint event to draw grid overlay."""
        super().paintEvent(event)

        # Draw grid overlay if visible
        if self._grid_overlay and self._grid_visible:
            self._grid_overlay.paint_overlay(self)

    def resizeEvent(self, event):
        """Handle resize events."""
        super().resizeEvent(event)

        # Update grid overlay
        if self._grid_overlay:
            self._grid_overlay.update_for_view_size(self.size())

    def get_visible_rect(self) -> QRectF:
        """Get the currently visible rectangle in world coordinates."""
        return self.mapToScene(self.rect()).boundingRect()

    def is_point_visible(self, world_pos: QPointF) -> bool:
        """Check if a world point is visible in the current view."""
        visible_rect = self.get_visible_rect()
        return visible_rect.contains(world_pos)

    def get_view_scale(self) -> float:
        """Get the current view scale factor."""
        return self.transform().m11()  # Assuming uniform scaling

    @property
    def snap_engine(self) -> Optional[SnapEngine]:
        """Get the snap engine."""
        return self._snap_engine

    @property
    def selection_manager(self) -> Optional[SelectionManager]:
        """Get the selection manager."""
        return self._selection_manager

    def get_snap_settings(self) -> dict:
        """Get current snap settings."""
        if self._snap_engine:
            return self._snap_engine.get_snap_settings()
        return {}

    def apply_snap_settings(self, settings: dict):
        """Apply snap settings."""
        if self._snap_engine:
            self._snap_engine.apply_snap_settings(settings)

    def get_selected_items(self) -> List:
        """Get currently selected items."""
        if self._selection_manager:
            return self._selection_manager.get_selected_items()
        return []

    def get_selected_ids(self) -> List[str]:
        """Get currently selected item IDs."""
        if self._selection_manager:
            return self._selection_manager.get_selected_ids()
        return []

    def clear_selection(self):
        """Clear current selection."""
        if self._selection_manager:
            self._selection_manager.clear_selection()

    def select_all(self):
        """Select all items."""
        if self._selection_manager:
            self._selection_manager.select_all()

    def get_selection_info(self) -> dict:
        """Get information about current selection."""
        if self._selection_manager:
            return self._selection_manager.get_selection_info()
        return {"count": 0}
