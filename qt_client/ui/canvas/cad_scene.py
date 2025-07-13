"""CAD graphics scene for managing drawing objects."""

import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene

logger = logging.getLogger(__name__)


class CADScene(QGraphicsScene):
    """Custom graphics scene for CAD drawing operations."""

    # Signals
    item_added = Signal(QGraphicsItem)
    item_removed = Signal(QGraphicsItem)
    selection_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Scene properties
        self._background_color = QColor(250, 250, 250)
        self._grid_visible = True
        self._snap_enabled = True

        # CAD-specific items tracking
        self._cad_items: Dict[str, QGraphicsItem] = {}
        self._layers: Dict[str, Dict] = {}
        self._current_layer = "0"  # Default layer

        # Setup scene
        self._setup_scene()

        logger.info("CAD scene initialized")

    def _setup_scene(self):
        """Setup scene properties."""
        # Set background
        self.setBackgroundBrush(QBrush(self._background_color))

        # Connect selection changed signal
        self.selectionChanged.connect(self._on_selection_changed)

        # Create default layer
        self._create_default_layer()

    def _create_default_layer(self):
        """Create default layer."""
        self._layers["0"] = {
            "name": "0",
            "color": QColor(255, 255, 255),  # White
            "line_type": "continuous",
            "line_weight": 0.25,
            "visible": True,
            "locked": False,
            "printable": True,
        }

    def add_cad_item(
        self, item: QGraphicsItem, item_id: str, layer: str = None
    ) -> bool:
        """Add a CAD item to the scene with tracking."""
        try:
            if item_id in self._cad_items:
                logger.warning(f"Item with ID {item_id} already exists")
                return False

            # Set layer
            if layer is None:
                layer = self._current_layer

            if layer not in self._layers:
                logger.warning(f"Layer {layer} does not exist, using default layer")
                layer = "0"

            # Add to scene
            self.addItem(item)

            # Track the item
            self._cad_items[item_id] = item

            # Set item properties based on layer
            self._apply_layer_properties(item, layer)

            # Store layer info with item
            item.setData(0, item_id)  # Store ID
            item.setData(1, layer)  # Store layer

            self.item_added.emit(item)
            logger.debug(f"Added CAD item {item_id} to layer {layer}")

            return True

        except Exception as e:
            logger.error(f"Error adding CAD item {item_id}: {e}")
            return False

    def remove_cad_item(self, item_id: str) -> bool:
        """Remove a CAD item from the scene."""
        try:
            if item_id not in self._cad_items:
                logger.warning(f"Item {item_id} not found")
                return False

            item = self._cad_items[item_id]

            # Remove from scene
            self.removeItem(item)

            # Remove from tracking
            del self._cad_items[item_id]

            self.item_removed.emit(item)
            logger.debug(f"Removed CAD item {item_id}")

            return True

        except Exception as e:
            logger.error(f"Error removing CAD item {item_id}: {e}")
            return False

    def get_cad_item(self, item_id: str) -> Optional[QGraphicsItem]:
        """Get a CAD item by ID."""
        return self._cad_items.get(item_id)

    def get_items_on_layer(self, layer: str) -> List[QGraphicsItem]:
        """Get all items on a specific layer."""
        items = []
        for item in self._cad_items.values():
            if item.data(1) == layer:
                items.append(item)
        return items

    def create_layer(
        self,
        name: str,
        color: QColor = None,
        line_type: str = "continuous",
        line_weight: float = 0.25,
    ) -> bool:
        """Create a new layer."""
        try:
            if name in self._layers:
                logger.warning(f"Layer {name} already exists")
                return False

            if color is None:
                color = QColor(255, 255, 255)

            self._layers[name] = {
                "name": name,
                "color": color,
                "line_type": line_type,
                "line_weight": line_weight,
                "visible": True,
                "locked": False,
                "printable": True,
            }

            logger.info(f"Created layer {name}")
            return True

        except Exception as e:
            logger.error(f"Error creating layer {name}: {e}")
            return False

    def delete_layer(self, name: str) -> bool:
        """Delete a layer (must be empty)."""
        try:
            if name not in self._layers:
                logger.warning(f"Layer {name} does not exist")
                return False

            if name == "0":
                logger.warning("Cannot delete default layer 0")
                return False

            # Check if layer has items
            items_on_layer = self.get_items_on_layer(name)
            if items_on_layer:
                logger.warning(
                    f"Cannot delete layer {name}: has {len(items_on_layer)} items"
                )
                return False

            del self._layers[name]

            # Switch current layer if deleted
            if self._current_layer == name:
                self._current_layer = "0"

            logger.info(f"Deleted layer {name}")
            return True

        except Exception as e:
            logger.error(f"Error deleting layer {name}: {e}")
            return False

    def set_layer_visible(self, name: str, visible: bool):
        """Set layer visibility."""
        if name in self._layers:
            self._layers[name]["visible"] = visible

            # Update items on layer
            for item in self.get_items_on_layer(name):
                item.setVisible(visible)

    def set_layer_locked(self, name: str, locked: bool):
        """Set layer locked state."""
        if name in self._layers:
            self._layers[name]["locked"] = locked

            # Update items on layer
            for item in self.get_items_on_layer(name):
                flags = item.flags()
                if locked:
                    flags &= ~QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
                    flags &= ~QGraphicsItem.GraphicsItemFlag.ItemIsMovable
                else:
                    flags |= QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
                    flags |= QGraphicsItem.GraphicsItemFlag.ItemIsMovable
                item.setFlags(flags)

    def set_current_layer(self, name: str):
        """Set the current layer for new items."""
        if name in self._layers:
            self._current_layer = name
            logger.debug(f"Current layer set to {name}")
        else:
            logger.warning(f"Layer {name} does not exist")

    def get_current_layer(self) -> str:
        """Get the current layer name."""
        return self._current_layer

    def get_layers(self) -> Dict[str, Dict]:
        """Get all layers."""
        return self._layers.copy()

    def _apply_layer_properties(self, item: QGraphicsItem, layer: str):
        """Apply layer properties to an item."""
        if layer not in self._layers:
            return

        layer_props = self._layers[layer]

        # Set visibility
        item.setVisible(layer_props["visible"])

        # Set selection/movement based on lock state
        flags = item.flags()
        if layer_props["locked"]:
            flags &= ~QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            flags &= ~QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        else:
            flags |= QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            flags |= QGraphicsItem.GraphicsItemFlag.ItemIsMovable
        item.setFlags(flags)

        # Apply pen/brush properties if item supports them
        try:
            color = layer_props["color"]
            line_weight = layer_props["line_weight"]

            # Create pen
            pen = QPen(color)
            pen.setWidthF(line_weight)

            # Set line style based on line type
            line_type = layer_props["line_type"]
            if line_type == "dashed":
                pen.setStyle(Qt.PenStyle.DashLine)
            elif line_type == "dotted":
                pen.setStyle(Qt.PenStyle.DotLine)
            elif line_type == "dash_dot":
                pen.setStyle(Qt.PenStyle.DashDotLine)
            else:
                pen.setStyle(Qt.PenStyle.SolidLine)

            # Apply to item if it has setPen method
            if hasattr(item, "setPen"):
                item.setPen(pen)

        except Exception as e:
            logger.debug(f"Could not apply layer properties to item: {e}")

    def clear_selection(self):
        """Clear all selected items."""
        self.clearSelection()

    def select_all(self):
        """Select all items."""
        for item in self.items():
            if item.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable:
                item.setSelected(True)

    def get_selected_items(self) -> List[QGraphicsItem]:
        """Get all selected items."""
        return self.selectedItems()

    def get_selected_cad_items(self) -> List[str]:
        """Get IDs of selected CAD items."""
        selected_ids = []
        for item in self.selectedItems():
            item_id = item.data(0)
            if item_id and item_id in self._cad_items:
                selected_ids.append(item_id)
        return selected_ids

    def _on_selection_changed(self):
        """Handle selection change."""
        selected_count = len(self.selectedItems())
        logger.debug(f"Selection changed: {selected_count} items selected")
        self.selection_changed.emit()

    def get_bounds(self) -> QRectF:
        """Get bounding rectangle of all items."""
        return self.itemsBoundingRect()

    def zoom_to_fit(self):
        """Get rectangle to zoom to fit all items."""
        bounds = self.get_bounds()
        if bounds.isEmpty():
            # Return default area if no items
            return QRectF(-50, -50, 100, 100)
        return bounds
