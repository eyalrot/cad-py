"""Layers panel for managing drawing layers."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class LayerDialog(QDialog):
    """Dialog for creating or editing layers."""

    def __init__(self, parent=None, layer_data=None):
        super().__init__(parent)
        self.layer_data = layer_data or {}
        self._setup_ui()

    def _setup_ui(self):
        """Setup the layer dialog UI."""
        self.setWindowTitle("Layer Properties" if self.layer_data else "New Layer")
        self.setModal(True)
        self.resize(400, 300)

        layout = QVBoxLayout(self)

        # Form layout
        form_layout = QFormLayout()

        # Layer name
        self.name_edit = QLineEdit()
        self.name_edit.setText(self.layer_data.get("name", ""))
        self.name_edit.setPlaceholderText("Enter layer name")
        form_layout.addRow("Name:", self.name_edit)

        # Color
        color_layout = QHBoxLayout()
        self.color_button = QPushButton()
        self.color_button.setFixedSize(50, 25)
        self.color = QColor(self.layer_data.get("color", "#FFFFFF"))
        self._update_color_button()
        self.color_button.clicked.connect(self._choose_color)
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()
        form_layout.addRow("Color:", color_layout)

        # Line type
        self.line_type_combo = QComboBox()
        self.line_type_combo.addItems(["continuous", "dashed", "dotted", "dash_dot"])
        self.line_type_combo.setCurrentText(
            self.layer_data.get("line_type", "continuous")
        )
        form_layout.addRow("Line Type:", self.line_type_combo)

        # Line weight
        self.line_weight_spin = QDoubleSpinBox()
        self.line_weight_spin.setDecimals(2)
        self.line_weight_spin.setRange(0.01, 10.0)
        self.line_weight_spin.setValue(self.layer_data.get("line_weight", 0.25))
        form_layout.addRow("Line Weight:", self.line_weight_spin)

        # Properties
        properties_layout = QVBoxLayout()

        self.visible_check = QCheckBox("Visible")
        self.visible_check.setChecked(self.layer_data.get("visible", True))
        properties_layout.addWidget(self.visible_check)

        self.locked_check = QCheckBox("Locked")
        self.locked_check.setChecked(self.layer_data.get("locked", False))
        properties_layout.addWidget(self.locked_check)

        self.printable_check = QCheckBox("Printable")
        self.printable_check.setChecked(self.layer_data.get("printable", True))
        properties_layout.addWidget(self.printable_check)

        form_layout.addRow("Properties:", properties_layout)

        layout.addLayout(form_layout)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Set focus to name field
        self.name_edit.setFocus()
        self.name_edit.selectAll()

    def _update_color_button(self):
        """Update the color button appearance."""
        pixmap = QPixmap(48, 23)
        pixmap.fill(self.color)
        self.color_button.setIcon(QIcon(pixmap))
        self.color_button.setText(self.color.name().upper())

    def _choose_color(self):
        """Open color dialog."""
        color = QColorDialog.getColor(self.color, self, "Choose Layer Color")
        if color.isValid():
            self.color = color
            self._update_color_button()

    def get_layer_data(self) -> Dict[str, Any]:
        """Get the layer data from dialog."""
        return {
            "name": self.name_edit.text().strip(),
            "color": self.color,
            "line_type": self.line_type_combo.currentText(),
            "line_weight": self.line_weight_spin.value(),
            "visible": self.visible_check.isChecked(),
            "locked": self.locked_check.isChecked(),
            "printable": self.printable_check.isChecked(),
        }


class LayersPanel(QWidget):
    """Panel for managing drawing layers."""

    # Signals
    layer_created = Signal(str, dict)  # layer_name, layer_properties
    layer_deleted = Signal(str)  # layer_name
    layer_modified = Signal(str, dict)  # layer_name, layer_properties
    layer_selected = Signal(str)  # layer_name
    layer_visibility_changed = Signal(str, bool)  # layer_name, visible

    def __init__(self, parent: Optional[QWidget] = None, api_client=None):
        super().__init__(parent)

        self._api_client = api_client
        self._document_id = None  # Will be set when document is opened
        self._layers: Dict[str, Dict[str, Any]] = {}
        self._current_layer = "0"

        self._setup_ui()
        self._create_default_layer()

        logger.info("Layers panel initialized")

    def _setup_ui(self):
        """Setup the layers panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Title
        title_label = QLabel("Layers")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Toolbar
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(2)

        # New layer button
        self.new_button = QToolButton()
        self.new_button.setIcon(self._create_icon("+"))
        self.new_button.setToolTip("New Layer")
        self.new_button.clicked.connect(self._new_layer)
        toolbar_layout.addWidget(self.new_button)

        # Delete layer button
        self.delete_button = QToolButton()
        self.delete_button.setIcon(self._create_icon("-"))
        self.delete_button.setToolTip("Delete Layer")
        self.delete_button.clicked.connect(self._delete_layer)
        toolbar_layout.addWidget(self.delete_button)

        # Edit layer button
        self.edit_button = QToolButton()
        self.edit_button.setIcon(self._create_icon("✎"))
        self.edit_button.setToolTip("Edit Layer")
        self.edit_button.clicked.connect(self._edit_layer)
        toolbar_layout.addWidget(self.edit_button)

        toolbar_layout.addStretch()

        # Layer options menu
        self.options_button = QToolButton()
        self.options_button.setIcon(self._create_icon("⋯"))
        self.options_button.setToolTip("Layer Options")
        self.options_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._setup_options_menu()
        toolbar_layout.addWidget(self.options_button)

        layout.addLayout(toolbar_layout)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        # Layers tree
        self.layers_tree = QTreeWidget()
        self.layers_tree.setHeaderLabels(["", "Name", "Color", "Type"])
        self.layers_tree.setRootIsDecorated(False)
        self.layers_tree.setAlternatingRowColors(True)
        self.layers_tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)

        # Set column widths
        header = self.layers_tree.header()
        header.resizeSection(0, 20)  # Visibility icon
        header.resizeSection(1, 80)  # Name
        header.resizeSection(2, 40)  # Color
        header.setStretchLastSection(True)  # Type

        # Connect signals
        self.layers_tree.itemChanged.connect(self._on_item_changed)
        self.layers_tree.itemClicked.connect(self._on_item_clicked)
        self.layers_tree.itemDoubleClicked.connect(self._on_item_double_clicked)

        layout.addWidget(self.layers_tree)

        # Current layer info
        current_layout = QHBoxLayout()
        current_layout.addWidget(QLabel("Current:"))

        self.current_label = QLabel("0")
        current_font = QFont()
        current_font.setBold(True)
        self.current_label.setFont(current_font)
        current_layout.addWidget(self.current_label)
        current_layout.addStretch()

        layout.addLayout(current_layout)

        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

    def _create_icon(self, text: str) -> QIcon:
        """Create a simple text-based icon."""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, text)
        painter.end()

        return QIcon(pixmap)

    def _setup_options_menu(self):
        """Setup the options menu."""
        menu = QMenu(self)

        # Show all layers
        show_all_action = QAction("Show All Layers", self)
        show_all_action.triggered.connect(self._show_all_layers)
        menu.addAction(show_all_action)

        # Hide all layers
        hide_all_action = QAction("Hide All Layers", self)
        hide_all_action.triggered.connect(self._hide_all_layers)
        menu.addAction(hide_all_action)

        menu.addSeparator()

        # Lock all layers
        lock_all_action = QAction("Lock All Layers", self)
        lock_all_action.triggered.connect(self._lock_all_layers)
        menu.addAction(lock_all_action)

        # Unlock all layers
        unlock_all_action = QAction("Unlock All Layers", self)
        unlock_all_action.triggered.connect(self._unlock_all_layers)
        menu.addAction(unlock_all_action)

        self.options_button.setMenu(menu)

    def _create_default_layer(self):
        """Create the default layer."""
        default_layer = {
            "name": "0",
            "color": QColor(255, 255, 255),  # White
            "line_type": "continuous",
            "line_weight": 0.25,
            "visible": True,
            "locked": False,
            "printable": True,
        }
        self.add_layer("0", default_layer)
        self.set_current_layer("0")

    def add_layer(self, name: str, properties: Dict[str, Any]):
        """Add a new layer."""
        self._layers[name] = properties.copy()
        self._add_layer_item(name, properties)
        logger.info(f"Added layer: {name}")

    def _add_layer_item(self, name: str, properties: Dict[str, Any]):
        """Add a layer item to the tree."""
        item = QTreeWidgetItem(self.layers_tree)

        # Set item data
        item.setData(0, Qt.ItemDataRole.UserRole, name)

        # Visibility checkbox
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(
            0,
            Qt.CheckState.Checked if properties["visible"] else Qt.CheckState.Unchecked,
        )

        # Layer name
        item.setText(1, name)
        if properties.get("locked", False):
            item.setIcon(1, self._create_icon("🔒"))

        # Color
        color_pixmap = QPixmap(20, 16)
        color_pixmap.fill(properties["color"])
        item.setIcon(2, QIcon(color_pixmap))
        item.setText(2, properties["color"].name().upper())

        # Line type
        item.setText(3, properties["line_type"])

        # Mark current layer
        if name == self._current_layer:
            font = item.font(1)
            font.setBold(True)
            item.setFont(1, font)

    def remove_layer(self, name: str):
        """Remove a layer."""
        if name == "0":
            logger.warning("Cannot delete default layer 0")
            return False

        if name not in self._layers:
            logger.warning(f"Layer {name} does not exist")
            return False

        # Remove from tree
        for i in range(self.layers_tree.topLevelItemCount()):
            item = self.layers_tree.topLevelItem(i)
            if item and item.data(0, Qt.ItemDataRole.UserRole) == name:
                self.layers_tree.takeTopLevelItem(i)
                break

        # Remove from layers dict
        del self._layers[name]

        # Switch current layer if needed
        if self._current_layer == name:
            self.set_current_layer("0")

        logger.info(f"Removed layer: {name}")
        return True

    def set_current_layer(self, name: str):
        """Set the current layer."""
        if name not in self._layers:
            logger.warning(f"Layer {name} does not exist")
            return

        old_current = self._current_layer
        self._current_layer = name

        # Update UI
        self.current_label.setText(name)

        # Update tree items formatting
        for i in range(self.layers_tree.topLevelItemCount()):
            item = self.layers_tree.topLevelItem(i)
            if item:
                layer_name = item.data(0, Qt.ItemDataRole.UserRole)
                font = item.font(1)
                font.setBold(layer_name == name)
                item.setFont(1, font)

        self.layer_selected.emit(name)
        logger.debug(f"Current layer changed from {old_current} to {name}")

    def get_current_layer(self) -> str:
        """Get the current layer name."""
        return self._current_layer

    def get_layers(self) -> Dict[str, Dict[str, Any]]:
        """Get all layers."""
        return self._layers.copy()

    def update_layer(self, name: str, properties: Dict[str, Any]):
        """Update layer properties."""
        if name not in self._layers:
            return

        self._layers[name].update(properties)

        # Update tree item
        for i in range(self.layers_tree.topLevelItemCount()):
            item = self.layers_tree.topLevelItem(i)
            if item and item.data(0, Qt.ItemDataRole.UserRole) == name:
                self._update_layer_item(item, name, self._layers[name])
                break

        self.layer_modified.emit(name, self._layers[name])

    def _update_layer_item(
        self, item: QTreeWidgetItem, name: str, properties: Dict[str, Any]
    ):
        """Update a layer item in the tree."""
        # Visibility
        item.setCheckState(
            0,
            Qt.CheckState.Checked if properties["visible"] else Qt.CheckState.Unchecked,
        )

        # Name and lock icon
        item.setText(1, name)
        if properties.get("locked", False):
            item.setIcon(1, self._create_icon("🔒"))
        else:
            item.setIcon(1, QIcon())

        # Color
        color_pixmap = QPixmap(20, 16)
        color_pixmap.fill(properties["color"])
        item.setIcon(2, QIcon(color_pixmap))
        item.setText(2, properties["color"].name().upper())

        # Line type
        item.setText(3, properties["line_type"])

    def _new_layer(self):
        """Create a new layer."""
        dialog = LayerDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            layer_data = dialog.get_layer_data()
            name = layer_data["name"]

            if not name:
                return

            if name in self._layers:
                logger.warning(f"Layer {name} already exists")
                return

            # Create layer locally first
            self.add_layer(name, layer_data)
            self.layer_created.emit(name, layer_data)

            # Send to backend if API client is available
            if self._api_client and self._document_id:
                asyncio.create_task(self._create_layer_backend(layer_data))

    def _delete_layer(self):
        """Delete the selected layer."""
        current_item = self.layers_tree.currentItem()
        if not current_item:
            return

        layer_name = current_item.data(0, Qt.ItemDataRole.UserRole)
        if self.remove_layer(layer_name):
            self.layer_deleted.emit(layer_name)

            # Send to backend if API client is available
            if self._api_client and self._document_id:
                asyncio.create_task(self._delete_layer_backend(layer_name))

    def _edit_layer(self):
        """Edit the selected layer."""
        current_item = self.layers_tree.currentItem()
        if not current_item:
            return

        layer_name = current_item.data(0, Qt.ItemDataRole.UserRole)
        layer_data = self._layers.get(layer_name, {})

        dialog = LayerDialog(self, layer_data)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_data = dialog.get_layer_data()
            new_name = new_data["name"]

            # Handle name change
            if new_name != layer_name:
                if new_name in self._layers:
                    logger.warning(f"Layer {new_name} already exists")
                    return

                # Remove old layer and add new one
                self.remove_layer(layer_name)
                self.add_layer(new_name, new_data)

                # Update current layer if needed
                if self._current_layer == layer_name:
                    self.set_current_layer(new_name)

                self.layer_deleted.emit(layer_name)
                self.layer_created.emit(new_name, new_data)
            else:
                # Just update properties
                self.update_layer(layer_name, new_data)

                # Send update to backend
                if self._api_client and self._document_id:
                    asyncio.create_task(
                        self._update_layer_backend(layer_name, new_data)
                    )

    def _on_item_changed(self, item: QTreeWidgetItem, column: int):
        """Handle item change (visibility checkbox)."""
        if column == 0:  # Visibility column
            layer_name = item.data(0, Qt.ItemDataRole.UserRole)
            visible = item.checkState(0) == Qt.CheckState.Checked

            # Update layer properties
            if layer_name in self._layers:
                self._layers[layer_name]["visible"] = visible
                self.layer_visibility_changed.emit(layer_name, visible)

                # Send update to backend
                if self._api_client and self._document_id:
                    asyncio.create_task(
                        self._update_layer_backend(layer_name, self._layers[layer_name])
                    )

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click."""
        layer_name = item.data(0, Qt.ItemDataRole.UserRole)
        if column == 1:  # Name column - set as current layer
            self.set_current_layer(layer_name)

            # Send to backend
            if self._api_client and self._document_id:
                asyncio.create_task(self._set_current_layer_backend(layer_name))

    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item double click - edit layer."""
        self._edit_layer()

    def _show_all_layers(self):
        """Show all layers."""
        for name in self._layers:
            self._layers[name]["visible"] = True
            self.layer_visibility_changed.emit(name, True)
        self._refresh_tree()

    def _hide_all_layers(self):
        """Hide all layers."""
        for name in self._layers:
            self._layers[name]["visible"] = False
            self.layer_visibility_changed.emit(name, False)
        self._refresh_tree()

    def _lock_all_layers(self):
        """Lock all layers."""
        for name in self._layers:
            self._layers[name]["locked"] = True
            self.layer_modified.emit(name, self._layers[name])
        self._refresh_tree()

    def _unlock_all_layers(self):
        """Unlock all layers."""
        for name in self._layers:
            self._layers[name]["locked"] = False
            self.layer_modified.emit(name, self._layers[name])
        self._refresh_tree()

    def _refresh_tree(self):
        """Refresh the layers tree."""
        self.layers_tree.clear()
        for name, properties in self._layers.items():
            self._add_layer_item(name, properties)

    def set_api_client(self, api_client):
        """Set the API client for backend communication."""
        self._api_client = api_client
        logger.debug("API client set for layers panel")

    def set_document_id(self, document_id: str):
        """Set the current document ID."""
        self._document_id = document_id
        if self._api_client:
            # Load layers from backend
            asyncio.create_task(self._load_layers_from_backend())
        logger.debug(f"Document ID set to: {document_id}")

    async def _load_layers_from_backend(self):
        """Load layers from backend API."""
        if not self._api_client or not self._document_id:
            return

        try:
            response = await self._api_client.list_layers(self._document_id)
            if response.get("success", False):
                layers_data = response.get("data", {}).get("layers", [])

                # Clear current layers and load from backend
                self._layers.clear()
                self.layers_tree.clear()

                for layer_proto in layers_data:
                    layer_properties = self._proto_to_layer_properties(layer_proto)
                    self._layers[layer_properties["name"]] = layer_properties
                    self._add_layer_item(layer_properties["name"], layer_properties)

                logger.info(f"Loaded {len(layers_data)} layers from backend")
            else:
                logger.error(
                    f"Failed to load layers: {response.get('error_message', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Error loading layers from backend: {e}")

    def _proto_to_layer_properties(self, layer_proto) -> Dict[str, Any]:
        """Convert layer protobuf to layer properties dict."""
        color_proto = layer_proto.get("color", {})

        return {
            "name": layer_proto.get("name", ""),
            "color": QColor(
                color_proto.get("red", 255),
                color_proto.get("green", 255),
                color_proto.get("blue", 255),
                color_proto.get("alpha", 255),
            ),
            "line_type": layer_proto.get("line_type", "continuous"),
            "line_weight": layer_proto.get("line_weight", 0.25),
            "visible": layer_proto.get("visible", True),
            "locked": layer_proto.get("locked", False),
            "printable": layer_proto.get("printable", True),
        }

    def _layer_properties_to_proto(self, layer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert layer properties dict to protobuf format."""
        color = layer_data.get("color", QColor(255, 255, 255))

        return {
            "name": layer_data.get("name", ""),
            "color": {
                "red": color.red(),
                "green": color.green(),
                "blue": color.blue(),
                "alpha": color.alpha(),
            },
            "line_type": layer_data.get("line_type", "continuous"),
            "line_weight": layer_data.get("line_weight", 0.25),
            "visible": layer_data.get("visible", True),
            "locked": layer_data.get("locked", False),
            "printable": layer_data.get("printable", True),
        }

    async def _create_layer_backend(self, layer_data: Dict[str, Any]):
        """Create layer in backend."""
        if not self._api_client or not self._document_id:
            return

        try:
            proto_data = self._layer_properties_to_proto(layer_data)
            proto_data["document_id"] = self._document_id

            response = await self._api_client.create_layer(proto_data)
            if response.get("success", False):
                logger.info(
                    f"Successfully created layer '{layer_data['name']}' in backend"
                )
            else:
                logger.error(
                    f"Failed to create layer in backend: {response.get('error_message', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Error creating layer in backend: {e}")

    async def _delete_layer_backend(self, layer_name: str):
        """Delete layer from backend."""
        if not self._api_client or not self._document_id:
            return

        try:
            response = await self._api_client.delete_layer(
                {
                    "document_id": self._document_id,
                    "layer_id": layer_name,  # Using layer name as ID for now
                }
            )
            if response.get("success", False):
                logger.info(f"Successfully deleted layer '{layer_name}' from backend")
            else:
                logger.error(
                    f"Failed to delete layer from backend: {response.get('error_message', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Error deleting layer from backend: {e}")

    async def _update_layer_backend(self, layer_name: str, layer_data: Dict[str, Any]):
        """Update layer in backend."""
        if not self._api_client or not self._document_id:
            return

        try:
            proto_data = self._layer_properties_to_proto(layer_data)
            proto_data["document_id"] = self._document_id
            proto_data["layer_id"] = layer_name

            response = await self._api_client.update_layer(proto_data)
            if response.get("success", False):
                logger.info(f"Successfully updated layer '{layer_name}' in backend")
            else:
                logger.error(
                    f"Failed to update layer in backend: {response.get('error_message', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Error updating layer in backend: {e}")

    async def _set_current_layer_backend(self, layer_name: str):
        """Set current layer in backend."""
        if not self._api_client or not self._document_id:
            return

        try:
            response = await self._api_client.set_current_layer(
                {"document_id": self._document_id, "layer_id": layer_name}
            )
            if response.get("success", False):
                logger.info(
                    f"Successfully set current layer to '{layer_name}' in backend"
                )
            else:
                logger.error(
                    f"Failed to set current layer in backend: {response.get('error_message', 'Unknown error')}"
                )

        except Exception as e:
            logger.error(f"Error setting current layer in backend: {e}")
