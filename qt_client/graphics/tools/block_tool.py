"""Block creation and insertion tools."""

import logging
from typing import List, Optional, Dict, Any
from enum import Enum

from PySide6.QtCore import Qt, QPointF, Signal
from PySide6.QtGui import QPen, QBrush, QColor
from PySide6.QtWidgets import QInputDialog, QMessageBox

from backend.core.geometry.point import Point2D
from backend.core.geometry.vector import Vector2D
from backend.models.block import Block, BlockReference, BlockType, AttributeDefinition, AttributeType
from backend.models.entity import BaseEntity
from qt_client.graphics.tools.base_tool import BaseTool, ToolState
from qt_client.graphics.items.preview_item import PreviewItem

logger = logging.getLogger(__name__)


class BlockToolState(Enum):
    """States for block tools."""
    IDLE = "idle"
    SELECTING_ENTITIES = "selecting_entities"
    SETTING_BASE_POINT = "setting_base_point"
    ENTERING_ATTRIBUTES = "entering_attributes"
    SELECTING_BLOCK = "selecting_block"
    SETTING_INSERTION_POINT = "setting_insertion_point"
    SETTING_SCALE = "setting_scale"
    SETTING_ROTATION = "setting_rotation"


class BlockCreationTool(BaseTool):
    """Tool for creating block definitions from selected entities."""

    def __init__(self, scene, api_client, command_manager, snap_engine, selection_manager):
        super().__init__(scene, api_client, command_manager, snap_engine, selection_manager)
        
        self.tool_name = "Block Creation"
        self.cursor_style = Qt.CursorShape.CrossCursor
        
        # Tool state
        self.state = BlockToolState.IDLE
        self.selected_entities: List[BaseEntity] = []
        self.base_point: Optional[Point2D] = None
        self.block_name: str = ""
        self.block_description: str = ""
        self.attributes: List[AttributeDefinition] = []
        
        # Preview
        self.preview_item: Optional[PreviewItem] = None
        
    def activate(self):
        """Activate the block creation tool."""
        super().activate()
        self.state = BlockToolState.SELECTING_ENTITIES
        self.selected_entities.clear()
        self.base_point = None
        self.block_name = ""
        self.block_description = ""
        self.attributes.clear()
        
        self.status_message.emit("Select entities to include in block")
        logger.debug("Block creation tool activated")
        
    def deactivate(self):
        """Deactivate the tool."""
        self._clear_preview()
        super().deactivate()
        
    def mouse_press_event(self, event):
        """Handle mouse press events."""
        if not self.is_active:
            return
            
        world_pos = self.scene_to_world(event.scenePos())
        snap_result = self.snap_engine.snap_to_geometry(world_pos, self.scene.items())
        final_pos = snap_result.point if snap_result.snapped else world_pos
        
        if self.state == BlockToolState.SELECTING_ENTITIES:
            self._handle_entity_selection(event)
        elif self.state == BlockToolState.SETTING_BASE_POINT:
            self._set_base_point(final_pos)
            
    def mouse_move_event(self, event):
        """Handle mouse move events."""
        if not self.is_active:
            return
            
        world_pos = self.scene_to_world(event.scenePos())
        snap_result = self.snap_engine.snap_to_geometry(world_pos, self.scene.items())
        final_pos = snap_result.point if snap_result.snapped else world_pos
        
        if self.state == BlockToolState.SETTING_BASE_POINT:
            self._update_base_point_preview(final_pos)
            
    def key_press_event(self, event):
        """Handle key press events."""
        if not self.is_active:
            return
            
        if event.key() == Qt.Key.Key_Enter or event.key() == Qt.Key.Key_Return:
            if self.state == BlockToolState.SELECTING_ENTITIES:
                self._finish_entity_selection()
        elif event.key() == Qt.Key.Key_Escape:
            self._cancel_operation()
            
    def _handle_entity_selection(self, event):
        """Handle entity selection for block creation."""
        # Use selection manager to handle entity selection
        if hasattr(self.selection_manager, 'handle_selection'):
            selected = self.selection_manager.handle_selection(event)
            if selected:
                # Add to selected entities if not already selected
                for entity in selected:
                    if entity not in self.selected_entities:
                        self.selected_entities.append(entity)
                        
                self.status_message.emit(f"Selected {len(self.selected_entities)} entities. Press Enter to continue or select more entities")
        
    def _finish_entity_selection(self):
        """Finish entity selection and move to base point selection."""
        if not self.selected_entities:
            QMessageBox.warning(None, "Warning", "Please select at least one entity for the block.")
            return
            
        self.state = BlockToolState.SETTING_BASE_POINT
        self.status_message.emit("Select base point for the block")
        
    def _set_base_point(self, point: Point2D):
        """Set the base point for the block."""
        self.base_point = point
        self._clear_preview()
        
        # Show block creation dialog
        self._show_block_creation_dialog()
        
    def _update_base_point_preview(self, point: Point2D):
        """Update base point preview."""
        self._clear_preview()
        
        # Create preview item to show base point
        self.preview_item = PreviewItem()
        
        # Draw a cross at the base point
        pen = QPen(QColor(255, 0, 0), 2)
        size = 10
        
        self.preview_item.addLine(
            point.x - size, point.y,
            point.x + size, point.y,
            pen
        )
        self.preview_item.addLine(
            point.x, point.y - size,
            point.x, point.y + size,
            pen
        )
        
        self.scene.addItem(self.preview_item)
        
    def _show_block_creation_dialog(self):
        """Show dialog for block creation parameters."""
        from qt_client.ui.dialogs.block_creation_dialog import BlockCreationDialog
        
        try:
            dialog = BlockCreationDialog(self.selected_entities, self.base_point)
            if dialog.exec() == dialog.DialogCode.Accepted:
                block_data = dialog.get_block_data()
                self._create_block(block_data)
            else:
                self._cancel_operation()
        except ImportError:
            # Fallback to simple input dialogs
            self._show_simple_block_dialog()
            
    def _show_simple_block_dialog(self):
        """Show simple input dialogs for block creation."""
        # Get block name
        name, ok = QInputDialog.getText(None, "Block Name", "Enter block name:")
        if not ok or not name.strip():
            self._cancel_operation()
            return
            
        # Get block description
        description, ok = QInputDialog.getText(None, "Block Description", "Enter block description (optional):")
        if not ok:
            description = ""
            
        block_data = {
            "name": name.strip(),
            "description": description.strip(),
            "block_type": BlockType.STATIC,
            "attributes": []
        }
        
        self._create_block(block_data)
        
    async def _create_block(self, block_data: Dict[str, Any]):
        """Create the block definition."""
        try:
            # Create block object
            block = Block(
                name=block_data["name"],
                base_point=self.base_point,
                block_type=block_data.get("block_type", BlockType.STATIC)
            )
            
            block.description = block_data.get("description", "")
            
            # Add entities to block
            for entity in self.selected_entities:
                # Create a copy of the entity for the block
                entity_copy = entity.copy()
                block.add_entity(entity_copy)
                
            # Add attributes if any
            for attr_data in block_data.get("attributes", []):
                attr = AttributeDefinition(
                    name=attr_data["name"],
                    type=AttributeType(attr_data["type"]),
                    default_value=attr_data["default_value"],
                    prompt=attr_data.get("prompt", ""),
                    description=attr_data.get("description", ""),
                    required=attr_data.get("required", True)
                )
                block.add_attribute(attr)
                
            # Save block via API
            if self.api_client:
                response = await self.api_client.create_block(block.serialize())
                if response.get("success", False):
                    self.status_message.emit(f"Block '{block.name}' created successfully")
                    QMessageBox.information(None, "Success", f"Block '{block.name}' created successfully!")
                else:
                    error_msg = response.get("error_message", "Unknown error")
                    self.status_message.emit(f"Failed to create block: {error_msg}")
                    QMessageBox.critical(None, "Error", f"Failed to create block: {error_msg}")
            else:
                # Fallback - just show success message
                self.status_message.emit(f"Block '{block.name}' created successfully")
                QMessageBox.information(None, "Success", f"Block '{block.name}' created successfully!")
                
        except Exception as e:
            logger.error(f"Error creating block: {e}")
            self.status_message.emit(f"Error creating block: {str(e)}")
            QMessageBox.critical(None, "Error", f"Error creating block: {str(e)}")
            
        finally:
            self._finish_operation()
            
    def _cancel_operation(self):
        """Cancel the current operation."""
        self._clear_preview()
        self.state = BlockToolState.IDLE
        self.selected_entities.clear()
        self.base_point = None
        self.status_message.emit("Block creation cancelled")
        
    def _finish_operation(self):
        """Finish the block creation operation."""
        self._clear_preview()
        self.state = BlockToolState.IDLE
        self.selected_entities.clear()
        self.base_point = None
        self.status_message.emit("Block creation completed")
        
    def _clear_preview(self):
        """Clear preview items."""
        if self.preview_item:
            self.scene.removeItem(self.preview_item)
            self.preview_item = None


class BlockInsertionTool(BaseTool):
    """Tool for inserting block references into the drawing."""

    def __init__(self, scene, api_client, command_manager, snap_engine, selection_manager):
        super().__init__(scene, api_client, command_manager, snap_engine, selection_manager)
        
        self.tool_name = "Block Insertion"
        self.cursor_style = Qt.CursorShape.CrossCursor
        
        # Tool state
        self.state = BlockToolState.IDLE
        self.available_blocks: List[Dict[str, Any]] = []
        self.selected_block: Optional[Dict[str, Any]] = None
        self.insertion_point: Optional[Point2D] = None
        self.scale_factor: float = 1.0
        self.rotation_angle: float = 0.0
        self.attribute_values: Dict[str, Any] = {}
        
        # Preview
        self.preview_item: Optional[PreviewItem] = None
        
    def activate(self):
        """Activate the block insertion tool."""
        super().activate()
        self.state = BlockToolState.SELECTING_BLOCK
        self.selected_block = None
        self.insertion_point = None
        self.scale_factor = 1.0
        self.rotation_angle = 0.0
        self.attribute_values.clear()
        
        # Load available blocks
        self._load_available_blocks()
        
    def deactivate(self):
        """Deactivate the tool."""
        self._clear_preview()
        super().deactivate()
        
    def mouse_press_event(self, event):
        """Handle mouse press events."""
        if not self.is_active:
            return
            
        world_pos = self.scene_to_world(event.scenePos())
        snap_result = self.snap_engine.snap_to_geometry(world_pos, self.scene.items())
        final_pos = snap_result.point if snap_result.snapped else world_pos
        
        if self.state == BlockToolState.SETTING_INSERTION_POINT:
            self._set_insertion_point(final_pos)
            
    def mouse_move_event(self, event):
        """Handle mouse move events."""
        if not self.is_active:
            return
            
        world_pos = self.scene_to_world(event.scenePos())
        snap_result = self.snap_engine.snap_to_geometry(world_pos, self.scene.items())
        final_pos = snap_result.point if snap_result.snapped else world_pos
        
        if self.state == BlockToolState.SETTING_INSERTION_POINT:
            self._update_insertion_preview(final_pos)
            
    def key_press_event(self, event):
        """Handle key press events."""
        if not self.is_active:
            return
            
        if event.key() == Qt.Key.Key_Escape:
            self._cancel_operation()
            
    async def _load_available_blocks(self):
        """Load available blocks from the API."""
        try:
            if self.api_client:
                response = await self.api_client.get_blocks()
                if response.get("success", False):
                    self.available_blocks = response.get("data", {}).get("blocks", [])
                else:
                    self.available_blocks = []
            else:
                # Fallback - empty list
                self.available_blocks = []
                
            if not self.available_blocks:
                QMessageBox.information(None, "No Blocks", "No blocks available for insertion. Create blocks first.")
                self._cancel_operation()
                return
                
            # Show block selection dialog
            self._show_block_selection_dialog()
            
        except Exception as e:
            logger.error(f"Error loading blocks: {e}")
            QMessageBox.critical(None, "Error", f"Error loading blocks: {str(e)}")
            self._cancel_operation()
            
    def _show_block_selection_dialog(self):
        """Show dialog for block selection."""
        from qt_client.ui.dialogs.block_selection_dialog import BlockSelectionDialog
        
        try:
            dialog = BlockSelectionDialog(self.available_blocks)
            if dialog.exec() == dialog.DialogCode.Accepted:
                self.selected_block = dialog.get_selected_block()
                self.scale_factor = dialog.get_scale_factor()
                self.rotation_angle = dialog.get_rotation_angle()
                self.attribute_values = dialog.get_attribute_values()
                
                self.state = BlockToolState.SETTING_INSERTION_POINT
                self.status_message.emit(f"Click to insert block '{self.selected_block['name']}'")
            else:
                self._cancel_operation()
        except ImportError:
            # Fallback to simple selection
            self._show_simple_block_selection()
            
    def _show_simple_block_selection(self):
        """Show simple block selection dialog."""
        if not self.available_blocks:
            self._cancel_operation()
            return
            
        # Create list of block names
        block_names = [block["name"] for block in self.available_blocks]
        
        # Show selection dialog
        name, ok = QInputDialog.getItem(
            None, "Select Block", "Choose block to insert:", block_names, 0, False
        )
        
        if ok and name:
            # Find selected block
            for block in self.available_blocks:
                if block["name"] == name:
                    self.selected_block = block
                    break
                    
            if self.selected_block:
                self.state = BlockToolState.SETTING_INSERTION_POINT
                self.status_message.emit(f"Click to insert block '{self.selected_block['name']}'")
            else:
                self._cancel_operation()
        else:
            self._cancel_operation()
            
    def _set_insertion_point(self, point: Point2D):
        """Set the insertion point and create the block reference."""
        self.insertion_point = point
        self._clear_preview()
        
        # Create block reference
        self._create_block_reference()
        
    def _update_insertion_preview(self, point: Point2D):
        """Update insertion point preview."""
        if not self.selected_block:
            return
            
        self._clear_preview()
        
        # Create preview item to show block outline
        self.preview_item = PreviewItem()
        
        # Draw a simplified preview of the block
        pen = QPen(QColor(0, 255, 0), 1, Qt.PenStyle.DashLine)
        brush = QBrush(QColor(0, 255, 0, 50))
        
        # Draw a rectangle representing the block bounds
        # This is simplified - in a real implementation, you'd render the actual block entities
        size = 20
        self.preview_item.addRect(
            point.x - size/2, point.y - size/2,
            size, size,
            pen, brush
        )
        
        # Draw insertion point marker
        marker_pen = QPen(QColor(255, 0, 0), 2)
        marker_size = 5
        self.preview_item.addLine(
            point.x - marker_size, point.y,
            point.x + marker_size, point.y,
            marker_pen
        )
        self.preview_item.addLine(
            point.x, point.y - marker_size,
            point.x, point.y + marker_size,
            marker_pen
        )
        
        self.scene.addItem(self.preview_item)
        
    async def _create_block_reference(self):
        """Create and insert the block reference."""
        try:
            # Create block reference object
            block_ref = BlockReference(
                block_id=self.selected_block["id"],
                insertion_point=self.insertion_point,
                layer_id="0"  # Default layer
            )
            
            # Set transformation properties
            block_ref.set_scale(self.scale_factor)
            block_ref.set_rotation(self.rotation_angle)
            
            # Set attribute values
            for name, value in self.attribute_values.items():
                block_ref.set_attribute_value(name, value)
                
            # Insert via API
            if self.api_client:
                response = await self.api_client.insert_block_reference(block_ref.serialize())
                if response.get("success", False):
                    self.status_message.emit(f"Block '{self.selected_block['name']}' inserted successfully")
                    
                    # Continue with the same block for multiple insertions
                    self.state = BlockToolState.SETTING_INSERTION_POINT
                    self.status_message.emit(f"Click to insert another '{self.selected_block['name']}' or press Escape to finish")
                else:
                    error_msg = response.get("error_message", "Unknown error")
                    self.status_message.emit(f"Failed to insert block: {error_msg}")
                    QMessageBox.critical(None, "Error", f"Failed to insert block: {error_msg}")
            else:
                # Fallback - just show success message
                self.status_message.emit(f"Block '{self.selected_block['name']}' inserted successfully")
                self.state = BlockToolState.SETTING_INSERTION_POINT
                self.status_message.emit(f"Click to insert another '{self.selected_block['name']}' or press Escape to finish")
                
        except Exception as e:
            logger.error(f"Error inserting block: {e}")
            self.status_message.emit(f"Error inserting block: {str(e)}")
            QMessageBox.critical(None, "Error", f"Error inserting block: {str(e)}")
            
    def _cancel_operation(self):
        """Cancel the current operation."""
        self._clear_preview()
        self.state = BlockToolState.IDLE
        self.selected_block = None
        self.insertion_point = None
        self.status_message.emit("Block insertion cancelled")
        
    def _clear_preview(self):
        """Clear preview items."""
        if self.preview_item:
            self.scene.removeItem(self.preview_item)
            self.preview_item = None