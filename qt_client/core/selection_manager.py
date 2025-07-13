"""Selection manager for CAD drawing operations with multiple selection modes."""

import logging
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsRectItem, QGraphicsScene

logger = logging.getLogger(__name__)


class SelectionMode(Enum):
    """Selection modes."""

    SINGLE = auto()  # Single pick selection
    WINDOW = auto()  # Window selection (items completely inside)
    CROSSING = auto()  # Crossing selection (items intersecting)
    FENCE = auto()  # Fence line selection
    POLYGON = auto()  # Polygon selection


class SelectionFilter(Enum):
    """Selection filter types."""

    ALL = auto()
    LINES = auto()
    CIRCLES = auto()
    ARCS = auto()
    RECTANGLES = auto()
    TEXT = auto()
    DIMENSIONS = auto()
    LAYER = auto()


class SelectionRubberBand:
    """Visual feedback for window/crossing selection."""

    def __init__(self):
        self._rect_item: Optional[QGraphicsRectItem] = None
        self._start_point: Optional[QPointF] = None
        self._is_crossing = False

    def start_selection(
        self, scene: QGraphicsScene, start_point: QPointF, is_crossing: bool = False
    ):
        """Start rubber band selection."""
        self._start_point = start_point
        self._is_crossing = is_crossing

        # Create rubber band rectangle
        self._rect_item = QGraphicsRectItem()

        # Set style based on selection type
        if is_crossing:
            # Crossing selection - dashed green line
            pen = QPen(QColor(0, 255, 0), 1, Qt.PenStyle.DashLine)
            brush = QBrush(QColor(0, 255, 0, 30))  # Semi-transparent green
        else:
            # Window selection - solid blue line
            pen = QPen(QColor(0, 0, 255), 1, Qt.PenStyle.SolidLine)
            brush = QBrush(QColor(0, 0, 255, 30))  # Semi-transparent blue

        pen.setCosmetic(True)  # Keep line width constant
        self._rect_item.setPen(pen)
        self._rect_item.setBrush(brush)
        self._rect_item.setZValue(999)  # On top of everything

        scene.addItem(self._rect_item)

    def update_selection(self, current_point: QPointF):
        """Update rubber band rectangle."""
        if not self._rect_item or not self._start_point:
            return

        # Calculate rectangle bounds
        left = min(self._start_point.x(), current_point.x())
        top = min(self._start_point.y(), current_point.y())
        width = abs(current_point.x() - self._start_point.x())
        height = abs(current_point.y() - self._start_point.y())

        rect = QRectF(left, top, width, height)
        self._rect_item.setRect(rect)

        # Update crossing mode based on drag direction
        if current_point.x() < self._start_point.x():
            # Dragging left-to-right: crossing mode
            if not self._is_crossing:
                self._is_crossing = True
                pen = QPen(QColor(0, 255, 0), 1, Qt.PenStyle.DashLine)
                brush = QBrush(QColor(0, 255, 0, 30))
                pen.setCosmetic(True)
                self._rect_item.setPen(pen)
                self._rect_item.setBrush(brush)
        else:
            # Dragging right-to-left: window mode
            if self._is_crossing:
                self._is_crossing = False
                pen = QPen(QColor(0, 0, 255), 1, Qt.PenStyle.SolidLine)
                brush = QBrush(QColor(0, 0, 255, 30))
                pen.setCosmetic(True)
                self._rect_item.setPen(pen)
                self._rect_item.setBrush(brush)

    def finish_selection(self, scene: QGraphicsScene) -> Optional[QRectF]:
        """Finish selection and return selection rectangle."""
        if not self._rect_item:
            return None

        selection_rect = self._rect_item.rect()
        scene.removeItem(self._rect_item)

        self._rect_item = None
        self._start_point = None

        return selection_rect

    def cancel_selection(self, scene: QGraphicsScene):
        """Cancel selection."""
        if self._rect_item:
            scene.removeItem(self._rect_item)
            self._rect_item = None
            self._start_point = None

    def is_crossing_mode(self) -> bool:
        """Check if in crossing selection mode."""
        return self._is_crossing


class SelectionManager(QObject):
    """Manager for handling object selection with multiple modes and filters."""

    # Signals
    selection_changed = Signal(list)  # List of selected item IDs
    selection_mode_changed = Signal(SelectionMode)
    selection_filter_changed = Signal(SelectionFilter)

    def __init__(self, scene: QGraphicsScene, parent: Optional[QObject] = None):
        super().__init__(parent)

        self.scene = scene
        self._selected_items: Set[QGraphicsItem] = set()
        self._selected_ids: Set[str] = set()

        # Selection settings
        self._selection_mode = SelectionMode.SINGLE
        self._selection_filter = SelectionFilter.ALL
        self._filter_layers: Set[str] = set()

        # Visual feedback
        self._rubber_band = SelectionRubberBand()
        self._highlight_color = QColor(255, 255, 0)  # Yellow highlight
        self._original_pens: Dict[QGraphicsItem, QPen] = {}

        # Selection state
        self._is_selecting = False
        self._multi_select_enabled = False

        logger.info("Selection manager initialized")

    @property
    def selection_mode(self) -> SelectionMode:
        """Get current selection mode."""
        return self._selection_mode

    @selection_mode.setter
    def selection_mode(self, mode: SelectionMode):
        """Set selection mode."""
        if self._selection_mode != mode:
            self._selection_mode = mode
            self.selection_mode_changed.emit(mode)
            logger.debug(f"Selection mode changed to {mode.name}")

    @property
    def selection_filter(self) -> SelectionFilter:
        """Get current selection filter."""
        return self._selection_filter

    @selection_filter.setter
    def selection_filter(self, filter_type: SelectionFilter):
        """Set selection filter."""
        if self._selection_filter != filter_type:
            self._selection_filter = filter_type
            self.selection_filter_changed.emit(filter_type)
            logger.debug(f"Selection filter changed to {filter_type.name}")

    def set_filter_layers(self, layers: Set[str]):
        """Set layers to filter selection by."""
        self._filter_layers = layers.copy()

    def get_selected_items(self) -> List[QGraphicsItem]:
        """Get list of selected graphics items."""
        return list(self._selected_items)

    def get_selected_ids(self) -> List[str]:
        """Get list of selected item IDs."""
        return list(self._selected_ids)

    def get_selection_count(self) -> int:
        """Get number of selected items."""
        return len(self._selected_items)

    def is_item_selected(self, item: QGraphicsItem) -> bool:
        """Check if an item is selected."""
        return item in self._selected_items

    def pick_select(
        self,
        point: QPointF,
        modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier,
    ):
        """Perform single pick selection at point."""
        # Find item at point
        items = self.scene.items(point)
        target_item = None

        # Find first selectable item
        for item in items:
            if self._passes_filter(item) and self._is_selectable(item):
                target_item = item
                break

        # Handle selection based on modifiers
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Toggle selection (multi-select)
            if target_item:
                if self.is_item_selected(target_item):
                    self._remove_from_selection(target_item)
                else:
                    self._add_to_selection(target_item)
        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            # Add to selection
            if target_item:
                self._add_to_selection(target_item)
        else:
            # Replace selection
            self.clear_selection()
            if target_item:
                self._add_to_selection(target_item)

        self._emit_selection_changed()

    def start_window_selection(self, start_point: QPointF):
        """Start window/crossing selection."""
        if self._is_selecting:
            return

        self._is_selecting = True
        self._rubber_band.start_selection(self.scene, start_point)

    def update_window_selection(self, current_point: QPointF):
        """Update window/crossing selection."""
        if not self._is_selecting:
            return

        self._rubber_band.update_selection(current_point)

    def finish_window_selection(
        self, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier
    ) -> bool:
        """Finish window/crossing selection."""
        if not self._is_selecting:
            return False

        selection_rect = self._rubber_band.finish_selection(self.scene)
        self._is_selecting = False

        if not selection_rect or selection_rect.isEmpty():
            return False

        # Determine selection method
        is_crossing = self._rubber_band.is_crossing_mode()

        # Get items in rectangle
        if is_crossing:
            # Crossing selection - items intersecting rectangle
            items = self.scene.items(
                selection_rect, Qt.ItemSelectionMode.IntersectsItemBoundingRect
            )
        else:
            # Window selection - items completely inside rectangle
            items = self.scene.items(
                selection_rect, Qt.ItemSelectionMode.ContainsItemBoundingRect
            )

        # Filter items
        valid_items = [
            item
            for item in items
            if self._passes_filter(item) and self._is_selectable(item)
        ]

        # Handle selection based on modifiers
        if not (
            modifiers
            & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
        ):
            # Replace selection
            self.clear_selection()

        # Add items to selection
        for item in valid_items:
            if modifiers & Qt.KeyboardModifier.ControlModifier:
                # Toggle selection
                if self.is_item_selected(item):
                    self._remove_from_selection(item)
                else:
                    self._add_to_selection(item)
            else:
                # Add to selection
                self._add_to_selection(item)

        self._emit_selection_changed()
        return len(valid_items) > 0

    def cancel_window_selection(self):
        """Cancel window/crossing selection."""
        if self._is_selecting:
            self._rubber_band.cancel_selection(self.scene)
            self._is_selecting = False

    def select_all(self):
        """Select all items that pass the current filter."""
        all_items = self.scene.items()
        valid_items = [
            item
            for item in all_items
            if self._passes_filter(item) and self._is_selectable(item)
        ]

        self.clear_selection()
        for item in valid_items:
            self._add_to_selection(item)

        self._emit_selection_changed()

    def select_similar(self, reference_item: QGraphicsItem):
        """Select all items similar to the reference item."""
        if not reference_item:
            return

        # Determine similarity criteria
        reference_type = type(reference_item)
        reference_layer = reference_item.data(1)  # Layer stored in data(1)

        all_items = self.scene.items()
        similar_items = []

        for item in all_items:
            if (
                self._passes_filter(item)
                and self._is_selectable(item)
                and type(item) == reference_type
                and item.data(1) == reference_layer
            ):
                similar_items.append(item)

        self.clear_selection()
        for item in similar_items:
            self._add_to_selection(item)

        self._emit_selection_changed()

    def invert_selection(self):
        """Invert the current selection."""
        all_items = self.scene.items()
        valid_items = [
            item
            for item in all_items
            if self._passes_filter(item) and self._is_selectable(item)
        ]

        currently_selected = self._selected_items.copy()

        self.clear_selection()
        for item in valid_items:
            if item not in currently_selected:
                self._add_to_selection(item)

        self._emit_selection_changed()

    def clear_selection(self):
        """Clear all selected items."""
        # Remove highlighting from all selected items
        for item in self._selected_items.copy():
            self._remove_highlight(item)

        self._selected_items.clear()
        self._selected_ids.clear()
        self._emit_selection_changed()

    def _add_to_selection(self, item: QGraphicsItem):
        """Add an item to the selection."""
        if item not in self._selected_items:
            self._selected_items.add(item)

            # Get item ID if available
            item_id = item.data(0)  # ID stored in data(0)
            if item_id:
                self._selected_ids.add(str(item_id))

            # Add visual highlight
            self._add_highlight(item)

            logger.debug(f"Added item to selection: {item_id}")

    def _remove_from_selection(self, item: QGraphicsItem):
        """Remove an item from the selection."""
        if item in self._selected_items:
            self._selected_items.remove(item)

            # Remove item ID
            item_id = item.data(0)
            if item_id and str(item_id) in self._selected_ids:
                self._selected_ids.remove(str(item_id))

            # Remove visual highlight
            self._remove_highlight(item)

            logger.debug(f"Removed item from selection: {item_id}")

    def _add_highlight(self, item: QGraphicsItem):
        """Add selection highlight to an item."""
        try:
            # Store original pen if item has one
            if hasattr(item, "pen"):
                self._original_pens[item] = item.pen()

                # Create highlight pen
                highlight_pen = QPen(self._highlight_color, 2)
                highlight_pen.setCosmetic(True)
                item.setPen(highlight_pen)

            # Set selection flag
            item.setSelected(True)

        except Exception as e:
            logger.debug(f"Could not add highlight to item: {e}")

    def _remove_highlight(self, item: QGraphicsItem):
        """Remove selection highlight from an item."""
        try:
            # Restore original pen if available
            if item in self._original_pens:
                item.setPen(self._original_pens[item])
                del self._original_pens[item]

            # Clear selection flag
            item.setSelected(False)

        except Exception as e:
            logger.debug(f"Could not remove highlight from item: {e}")

    def _passes_filter(self, item: QGraphicsItem) -> bool:
        """Check if an item passes the current selection filter."""
        if self._selection_filter == SelectionFilter.ALL:
            return True

        # Check layer filter
        if self._filter_layers:
            item_layer = item.data(1)  # Layer stored in data(1)
            if item_layer not in self._filter_layers:
                return False

        # Check type filter
        if self._selection_filter == SelectionFilter.LINES:
            from PySide6.QtWidgets import QGraphicsLineItem

            return isinstance(item, QGraphicsLineItem)
        elif self._selection_filter == SelectionFilter.CIRCLES:
            from PySide6.QtWidgets import QGraphicsEllipseItem

            return isinstance(item, QGraphicsEllipseItem)
        elif self._selection_filter == SelectionFilter.RECTANGLES:
            from PySide6.QtWidgets import QGraphicsRectItem

            return isinstance(item, QGraphicsRectItem)
        # Add more type filters as needed

        return True

    def _is_selectable(self, item: QGraphicsItem) -> bool:
        """Check if an item is selectable."""
        # Check if item is visible and not locked
        if not item.isVisible():
            return False

        # Check if item has selectable flag
        if not (item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable):
            return False

        # Skip selection helper items (like snap markers, rubber band)
        if item.zValue() > 900:  # Helper items have high Z values
            return False

        return True

    def _emit_selection_changed(self):
        """Emit selection changed signal."""
        self.selection_changed.emit(list(self._selected_ids))
        logger.debug(f"Selection changed: {len(self._selected_items)} items selected")

    def get_selection_bounds(self) -> Optional[QRectF]:
        """Get bounding rectangle of all selected items."""
        if not self._selected_items:
            return None

        bounds = None
        for item in self._selected_items:
            item_bounds = item.sceneBoundingRect()
            if bounds is None:
                bounds = item_bounds
            else:
                bounds = bounds.united(item_bounds)

        return bounds

    def get_selection_center(self) -> Optional[QPointF]:
        """Get center point of selection."""
        bounds = self.get_selection_bounds()
        if bounds:
            return bounds.center()
        return None

    def get_selection_info(self) -> Dict[str, Any]:
        """Get information about the current selection."""
        type_counts = {}
        layer_counts = {}

        for item in self._selected_items:
            # Count by type
            item_type = type(item).__name__
            type_counts[item_type] = type_counts.get(item_type, 0) + 1

            # Count by layer
            item_layer = item.data(1) or "0"
            layer_counts[item_layer] = layer_counts.get(item_layer, 0) + 1

        bounds = self.get_selection_bounds()
        center = self.get_selection_center()

        return {
            "count": len(self._selected_items),
            "types": type_counts,
            "layers": layer_counts,
            "bounds": bounds,
            "center": center,
            "mode": self._selection_mode.name,
            "filter": self._selection_filter.name,
        }

    def apply_to_selection(self, operation: Callable[[QGraphicsItem], None]):
        """Apply an operation to all selected items."""
        for (
            item
        ) in self._selected_items.copy():  # Copy to avoid modification during iteration
            try:
                operation(item)
            except Exception as e:
                logger.error(f"Error applying operation to selected item: {e}")

    def move_selection(self, delta: QPointF):
        """Move all selected items by the given delta."""

        def move_item(item: QGraphicsItem):
            item.moveBy(delta.x(), delta.y())

        self.apply_to_selection(move_item)

    def delete_selection(self):
        """Delete all selected items."""
        items_to_delete = list(self._selected_items)
        self.clear_selection()

        for item in items_to_delete:
            if item.scene():
                item.scene().removeItem(item)
