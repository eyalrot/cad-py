"""Properties panel for displaying and editing object properties."""

import logging
from typing import Optional, Dict, Any, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton,
    QGroupBox, QScrollArea, QFormLayout, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont


logger = logging.getLogger(__name__)


class PropertiesPanel(QWidget):
    """Panel for displaying and editing properties of selected objects."""
    
    # Signals
    property_changed = pyqtSignal(str, str, object)  # object_id, property_name, value
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        
        self._current_objects: List[str] = []
        self._properties: Dict[str, Dict[str, Any]] = {}
        self._property_widgets: Dict[str, QWidget] = {}
        
        self._setup_ui()
        logger.info("Properties panel initialized")
    
    def _setup_ui(self):
        """Setup the properties panel UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Title
        title_label = QLabel("Properties")
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(10)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Scroll area for properties
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Properties widget
        self._properties_widget = QWidget()
        self._properties_layout = QVBoxLayout(self._properties_widget)
        self._properties_layout.setContentsMargins(5, 5, 5, 5)
        self._properties_layout.setSpacing(10)
        
        scroll_area.setWidget(self._properties_widget)
        layout.addWidget(scroll_area)
        
        # Initially show "No selection" message
        self._show_no_selection()
        
        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
    
    def _show_no_selection(self):
        """Show message when no objects are selected."""
        self._clear_properties()
        
        label = QLabel("No objects selected")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: gray; font-style: italic;")
        self._properties_layout.addWidget(label)
        self._properties_layout.addStretch()
    
    def _clear_properties(self):
        """Clear all property widgets."""
        while self._properties_layout.count():
            item = self._properties_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._property_widgets.clear()
    
    def set_selected_objects(self, object_ids: List[str], properties: Dict[str, Dict[str, Any]]):
        """Set the currently selected objects and their properties."""
        self._current_objects = object_ids.copy()
        self._properties = properties.copy()
        
        if not object_ids:
            self._show_no_selection()
            return
        
        self._update_properties_display()
    
    def _update_properties_display(self):
        """Update the properties display based on selected objects."""
        self._clear_properties()
        
        if not self._current_objects:
            self._show_no_selection()
            return
        
        if len(self._current_objects) == 1:
            self._show_single_object_properties()
        else:
            self._show_multiple_objects_properties()
    
    def _show_single_object_properties(self):
        """Show properties for a single selected object."""
        object_id = self._current_objects[0]
        properties = self._properties.get(object_id, {})
        
        # Object info group
        self._create_object_info_group(object_id, properties)
        
        # Geometry group (if applicable)
        if self._has_geometry_properties(properties):
            self._create_geometry_group(object_id, properties)
        
        # Layer properties group
        self._create_layer_group(object_id, properties)
        
        # Visual properties group
        self._create_visual_group(object_id, properties)
        
        # Add stretch to push everything to top
        self._properties_layout.addStretch()
    
    def _show_multiple_objects_properties(self):
        """Show properties for multiple selected objects."""
        # Summary group
        summary_group = QGroupBox(f"Selection ({len(self._current_objects)} objects)")
        summary_layout = QFormLayout(summary_group)
        
        # Object types summary
        object_types = {}
        for obj_id in self._current_objects:
            obj_props = self._properties.get(obj_id, {})
            obj_type = obj_props.get('type', 'Unknown')
            object_types[obj_type] = object_types.get(obj_type, 0) + 1
        
        types_text = ", ".join([f"{count} {obj_type}" for obj_type, count in object_types.items()])
        summary_layout.addRow("Types:", QLabel(types_text))
        
        self._properties_layout.addWidget(summary_group)
        
        # Common properties that can be edited for multiple objects
        self._create_common_properties_group()
        
        self._properties_layout.addStretch()
    
    def _create_object_info_group(self, object_id: str, properties: Dict[str, Any]):
        """Create object information group."""
        group = QGroupBox("Object Information")
        layout = QFormLayout(group)
        
        # Object ID
        layout.addRow("ID:", QLabel(object_id))
        
        # Object type
        obj_type = properties.get('type', 'Unknown')
        layout.addRow("Type:", QLabel(obj_type))
        
        # Layer
        layer = properties.get('layer', '0')
        layer_combo = QComboBox()
        layer_combo.addItems(['0', '1', '2', '3'])  # Placeholder layers
        layer_combo.setCurrentText(layer)
        layer_combo.currentTextChanged.connect(
            lambda value: self._on_property_changed(object_id, 'layer', value)
        )
        layout.addRow("Layer:", layer_combo)
        self._property_widgets[f"{object_id}_layer"] = layer_combo
        
        self._properties_layout.addWidget(group)
    
    def _create_geometry_group(self, object_id: str, properties: Dict[str, Any]):
        """Create geometry properties group."""
        group = QGroupBox("Geometry")
        layout = QFormLayout(group)
        
        # Position (if applicable)
        if 'x' in properties and 'y' in properties:
            x_spin = QDoubleSpinBox()
            x_spin.setDecimals(3)
            x_spin.setRange(-999999, 999999)
            x_spin.setValue(properties.get('x', 0.0))
            x_spin.valueChanged.connect(
                lambda value: self._on_property_changed(object_id, 'x', value)
            )
            layout.addRow("X:", x_spin)
            self._property_widgets[f"{object_id}_x"] = x_spin
            
            y_spin = QDoubleSpinBox()
            y_spin.setDecimals(3)
            y_spin.setRange(-999999, 999999)
            y_spin.setValue(properties.get('y', 0.0))
            y_spin.valueChanged.connect(
                lambda value: self._on_property_changed(object_id, 'y', value)
            )
            layout.addRow("Y:", y_spin)
            self._property_widgets[f"{object_id}_y"] = y_spin
        
        # Dimensions (if applicable)
        if 'width' in properties:
            width_spin = QDoubleSpinBox()
            width_spin.setDecimals(3)
            width_spin.setRange(0.001, 999999)
            width_spin.setValue(properties.get('width', 1.0))
            width_spin.valueChanged.connect(
                lambda value: self._on_property_changed(object_id, 'width', value)
            )
            layout.addRow("Width:", width_spin)
            self._property_widgets[f"{object_id}_width"] = width_spin
        
        if 'height' in properties:
            height_spin = QDoubleSpinBox()
            height_spin.setDecimals(3)
            height_spin.setRange(0.001, 999999)
            height_spin.setValue(properties.get('height', 1.0))
            height_spin.valueChanged.connect(
                lambda value: self._on_property_changed(object_id, 'height', value)
            )
            layout.addRow("Height:", height_spin)
            self._property_widgets[f"{object_id}_height"] = height_spin
        
        if 'radius' in properties:
            radius_spin = QDoubleSpinBox()
            radius_spin.setDecimals(3)
            radius_spin.setRange(0.001, 999999)
            radius_spin.setValue(properties.get('radius', 1.0))
            radius_spin.valueChanged.connect(
                lambda value: self._on_property_changed(object_id, 'radius', value)
            )
            layout.addRow("Radius:", radius_spin)
            self._property_widgets[f"{object_id}_radius"] = radius_spin
        
        self._properties_layout.addWidget(group)
    
    def _create_layer_group(self, object_id: str, properties: Dict[str, Any]):
        """Create layer properties group."""
        group = QGroupBox("Layer Properties")
        layout = QFormLayout(group)
        
        # Layer visibility
        visible_check = QCheckBox()
        visible_check.setChecked(properties.get('visible', True))
        visible_check.toggled.connect(
            lambda checked: self._on_property_changed(object_id, 'visible', checked)
        )
        layout.addRow("Visible:", visible_check)
        self._property_widgets[f"{object_id}_visible"] = visible_check
        
        # Layer locked
        locked_check = QCheckBox()
        locked_check.setChecked(properties.get('locked', False))
        locked_check.toggled.connect(
            lambda checked: self._on_property_changed(object_id, 'locked', checked)
        )
        layout.addRow("Locked:", locked_check)
        self._property_widgets[f"{object_id}_locked"] = locked_check
        
        self._properties_layout.addWidget(group)
    
    def _create_visual_group(self, object_id: str, properties: Dict[str, Any]):
        """Create visual properties group."""
        group = QGroupBox("Visual Properties")
        layout = QFormLayout(group)
        
        # Line weight
        weight_spin = QDoubleSpinBox()
        weight_spin.setDecimals(2)
        weight_spin.setRange(0.01, 10.0)
        weight_spin.setValue(properties.get('line_weight', 0.25))
        weight_spin.valueChanged.connect(
            lambda value: self._on_property_changed(object_id, 'line_weight', value)
        )
        layout.addRow("Line Weight:", weight_spin)
        self._property_widgets[f"{object_id}_line_weight"] = weight_spin
        
        # Line type
        line_type_combo = QComboBox()
        line_type_combo.addItems(['continuous', 'dashed', 'dotted', 'dash_dot'])
        line_type_combo.setCurrentText(properties.get('line_type', 'continuous'))
        line_type_combo.currentTextChanged.connect(
            lambda value: self._on_property_changed(object_id, 'line_type', value)
        )
        layout.addRow("Line Type:", line_type_combo)
        self._property_widgets[f"{object_id}_line_type"] = line_type_combo
        
        self._properties_layout.addWidget(group)
    
    def _create_common_properties_group(self):
        """Create group for properties common to multiple objects."""
        group = QGroupBox("Common Properties")
        layout = QFormLayout(group)
        
        # Layer (can be changed for all selected objects)
        layer_combo = QComboBox()
        layer_combo.addItems(['0', '1', '2', '3'])  # Placeholder layers
        layer_combo.currentTextChanged.connect(self._on_multiple_layer_changed)
        layout.addRow("Layer:", layer_combo)
        
        # Visibility
        visible_check = QCheckBox()
        visible_check.setTristate(True)  # Allow indeterminate state
        visible_check.setCheckState(Qt.CheckState.PartiallyChecked)
        visible_check.stateChanged.connect(self._on_multiple_visibility_changed)
        layout.addRow("Visible:", visible_check)
        
        # Line weight
        weight_spin = QDoubleSpinBox()
        weight_spin.setDecimals(2)
        weight_spin.setRange(0.01, 10.0)
        weight_spin.setValue(0.25)
        weight_spin.valueChanged.connect(self._on_multiple_line_weight_changed)
        layout.addRow("Line Weight:", weight_spin)
        
        self._properties_layout.addWidget(group)
    
    def _has_geometry_properties(self, properties: Dict[str, Any]) -> bool:
        """Check if object has geometry properties to display."""
        geometry_props = ['x', 'y', 'width', 'height', 'radius', 'start_x', 'start_y', 'end_x', 'end_y']
        return any(prop in properties for prop in geometry_props)
    
    def _on_property_changed(self, object_id: str, property_name: str, value: Any):
        """Handle property change for a single object."""
        # Update internal properties
        if object_id in self._properties:
            self._properties[object_id][property_name] = value
        
        # Emit signal
        self.property_changed.emit(object_id, property_name, value)
        logger.debug(f"Property changed: {object_id}.{property_name} = {value}")
    
    def _on_multiple_layer_changed(self, layer: str):
        """Handle layer change for multiple objects."""
        for object_id in self._current_objects:
            self._on_property_changed(object_id, 'layer', layer)
    
    def _on_multiple_visibility_changed(self, state: int):
        """Handle visibility change for multiple objects."""
        visible = state == Qt.CheckState.Checked.value
        for object_id in self._current_objects:
            self._on_property_changed(object_id, 'visible', visible)
    
    def _on_multiple_line_weight_changed(self, weight: float):
        """Handle line weight change for multiple objects."""
        for object_id in self._current_objects:
            self._on_property_changed(object_id, 'line_weight', weight)
    
    def update_property_value(self, object_id: str, property_name: str, value: Any):
        """Update a property value from external source."""
        if object_id in self._properties:
            self._properties[object_id][property_name] = value
            
            # Update widget if it exists
            widget_key = f"{object_id}_{property_name}"
            if widget_key in self._property_widgets:
                widget = self._property_widgets[widget_key]
                
                # Block signals to prevent recursion
                widget.blockSignals(True)
                
                if isinstance(widget, QDoubleSpinBox):
                    widget.setValue(float(value))
                elif isinstance(widget, QSpinBox):
                    widget.setValue(int(value))
                elif isinstance(widget, QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QComboBox):
                    widget.setCurrentText(str(value))
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(bool(value))
                
                widget.blockSignals(False)
    
    def clear_selection(self):
        """Clear the current selection."""
        self._current_objects.clear()
        self._properties.clear()
        self._show_no_selection()
    
    def get_selected_objects(self) -> List[str]:
        """Get the currently selected object IDs."""
        return self._current_objects.copy()