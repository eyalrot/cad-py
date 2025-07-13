"""Block API service implementation."""

import logging
import uuid
from typing import Any, Dict, List, Optional

from backend.models.block import Block, BlockReference, BlockLibrary, BlockType, AttributeType, AttributeDefinition
from backend.core.geometry.point import Point2D
from backend.core.geometry.vector import Vector2D
from .converters import ProtobufConverters
from .document_service import DocumentService

logger = logging.getLogger(__name__)


class BlockAPIService:
    """API service for block operations."""

    def __init__(self, document_service: DocumentService):
        self.document_service = document_service
        # In-memory storage for blocks and libraries
        # In a real implementation, this would be backed by a database
        self.blocks: Dict[str, Block] = {}
        self.block_libraries: Dict[str, BlockLibrary] = {}
        self.document_block_refs: Dict[str, List[BlockReference]] = {}  # document_id -> block_refs
        
        # Create default library
        self._create_default_library()

    def _create_default_library(self):
        """Create a default block library."""
        default_lib = BlockLibrary("Default", "Default block library")
        self.block_libraries[default_lib.id] = default_lib

    def create_block(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new block definition."""
        try:
            # Parse block data
            block_data = request.get("block_data", {})
            if not block_data:
                return ProtobufConverters.create_error_response(
                    error_message="Block data is required"
                )

            name = block_data.get("name", "")
            if not name:
                return ProtobufConverters.create_error_response(
                    error_message="Block name is required"
                )

            # Check if block name already exists
            for existing_block in self.blocks.values():
                if existing_block.name == name:
                    return ProtobufConverters.create_error_response(
                        error_message=f"Block with name '{name}' already exists"
                    )

            # Parse base point
            base_point_data = block_data.get("base_point", [0, 0])
            base_point = Point2D(base_point_data[0], base_point_data[1])

            # Parse block type
            block_type_str = block_data.get("block_type", "static")
            block_type = BlockType(block_type_str)

            # Create block
            block = Block(name, base_point, block_type)
            
            # Set optional properties
            block.description = block_data.get("description", "")
            block.category = block_data.get("category", "General")
            block.tags = block_data.get("tags", [])
            block.author = block_data.get("author", "")
            block.version = block_data.get("version", "1.0")
            block.units = block_data.get("units", "mm")
            block.scale = block_data.get("scale", 1.0)

            # Parse and add entities
            entities_data = block_data.get("entities", [])
            for entity_data in entities_data:
                entity = self._parse_entity(entity_data)
                if entity:
                    block.add_entity(entity)

            # Parse and add attributes
            attributes_data = block_data.get("attributes", {})
            for attr_name, attr_data in attributes_data.items():
                attribute = self._parse_attribute_definition(attr_data)
                if attribute:
                    block.add_attribute(attribute)

            # Store block
            self.blocks[block.id] = block

            # Add to default library
            default_lib = list(self.block_libraries.values())[0]
            default_lib.add_block(block)

            return ProtobufConverters.create_success_response({
                "block": {
                    "id": block.id,
                    "name": block.name,
                    "description": block.description,
                    "entity_count": len(block.entities),
                    "attribute_count": len(block.attributes)
                }
            })

        except Exception as e:
            logger.error(f"Error creating block: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to create block: {str(e)}"
            )

    def get_blocks(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of available blocks."""
        try:
            library_id = request.get("library_id")
            category = request.get("category")
            search_query = request.get("search_query", "")

            blocks_list = []

            if library_id:
                # Get blocks from specific library
                library = self.block_libraries.get(library_id)
                if library:
                    if category:
                        library_blocks = library.get_blocks_by_category(category)
                    else:
                        library_blocks = list(library.blocks.values())
                else:
                    library_blocks = []
            else:
                # Get all blocks
                library_blocks = list(self.blocks.values())

            # Apply search filter
            if search_query:
                filtered_blocks = []
                for block in library_blocks:
                    if search_query.lower() in block.name.lower() or \
                       search_query.lower() in block.description.lower() or \
                       any(search_query.lower() in tag.lower() for tag in block.tags):
                        filtered_blocks.append(block)
                library_blocks = filtered_blocks

            # Convert to response format
            for block in library_blocks:
                block_info = {
                    "id": block.id,
                    "name": block.name,
                    "description": block.description,
                    "category": block.category,
                    "tags": block.tags,
                    "entity_count": len(block.entities),
                    "attribute_count": len(block.attributes),
                    "block_type": block.block_type.value,
                    "created_at": block.created_at.isoformat(),
                    "modified_at": block.modified_at.isoformat(),
                    "author": block.author,
                    "version": block.version,
                    "preview_image_path": block.preview_image_path
                }
                blocks_list.append(block_info)

            return ProtobufConverters.create_success_response({
                "blocks": blocks_list,
                "total_count": len(blocks_list)
            })

        except Exception as e:
            logger.error(f"Error getting blocks: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to get blocks: {str(e)}"
            )

    def get_block(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific block."""
        try:
            block_id = request.get("block_id", "")
            if not block_id:
                return ProtobufConverters.create_error_response(
                    error_message="Block ID is required"
                )

            block = self.blocks.get(block_id)
            if not block:
                return ProtobufConverters.create_error_response(
                    error_message=f"Block {block_id} not found"
                )

            # Include full block data
            block_data = block.serialize()

            return ProtobufConverters.create_success_response({
                "block": block_data
            })

        except Exception as e:
            logger.error(f"Error getting block: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to get block: {str(e)}"
            )

    def update_block(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing block definition."""
        try:
            block_id = request.get("block_id", "")
            if not block_id:
                return ProtobufConverters.create_error_response(
                    error_message="Block ID is required"
                )

            block = self.blocks.get(block_id)
            if not block:
                return ProtobufConverters.create_error_response(
                    error_message=f"Block {block_id} not found"
                )

            # Update block properties
            updates = request.get("updates", {})
            
            if "name" in updates:
                # Check for name conflicts
                new_name = updates["name"]
                for existing_id, existing_block in self.blocks.items():
                    if existing_id != block_id and existing_block.name == new_name:
                        return ProtobufConverters.create_error_response(
                            error_message=f"Block with name '{new_name}' already exists"
                        )
                block.name = new_name

            if "description" in updates:
                block.description = updates["description"]
            if "category" in updates:
                block.category = updates["category"]
            if "tags" in updates:
                block.tags = updates["tags"]
            if "author" in updates:
                block.author = updates["author"]
            if "version" in updates:
                block.version = updates["version"]

            # Update modification time
            from datetime import datetime
            block.modified_at = datetime.utcnow()

            return ProtobufConverters.create_success_response({
                "block": {
                    "id": block.id,
                    "name": block.name,
                    "modified_at": block.modified_at.isoformat()
                }
            })

        except Exception as e:
            logger.error(f"Error updating block: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to update block: {str(e)}"
            )

    def delete_block(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a block definition."""
        try:
            block_id = request.get("block_id", "")
            if not block_id:
                return ProtobufConverters.create_error_response(
                    error_message="Block ID is required"
                )

            if block_id not in self.blocks:
                return ProtobufConverters.create_error_response(
                    error_message=f"Block {block_id} not found"
                )

            # Check if block is in use (has references)
            in_use = False
            for doc_refs in self.document_block_refs.values():
                if any(ref.block_id == block_id for ref in doc_refs):
                    in_use = True
                    break

            force_delete = request.get("force", False)
            if in_use and not force_delete:
                return ProtobufConverters.create_error_response(
                    error_message=f"Block {block_id} is in use and cannot be deleted. Use force=true to override."
                )

            # Remove from libraries
            for library in self.block_libraries.values():
                library.remove_block(block_id)

            # Remove block
            del self.blocks[block_id]

            # Remove all references if force delete
            if force_delete:
                for doc_refs in self.document_block_refs.values():
                    self.document_block_refs[doc_refs] = [
                        ref for ref in doc_refs if ref.block_id != block_id
                    ]

            return ProtobufConverters.create_success_response({
                "deleted_block_id": block_id
            })

        except Exception as e:
            logger.error(f"Error deleting block: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to delete block: {str(e)}"
            )

    def insert_block_reference(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a block reference into a document."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )

            # Get document to ensure it exists
            document = self.document_service.get_document(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )

            block_ref_data = request.get("block_reference", {})
            if not block_ref_data:
                return ProtobufConverters.create_error_response(
                    error_message="Block reference data is required"
                )

            # Parse block reference
            block_ref = self._parse_block_reference(block_ref_data)
            if not block_ref:
                return ProtobufConverters.create_error_response(
                    error_message="Invalid block reference data"
                )

            # Verify block exists
            if block_ref.block_id not in self.blocks:
                return ProtobufConverters.create_error_response(
                    error_message=f"Block {block_ref.block_id} not found"
                )

            # Add to document's block references
            if document_id not in self.document_block_refs:
                self.document_block_refs[document_id] = []
            
            self.document_block_refs[document_id].append(block_ref)

            return ProtobufConverters.create_success_response({
                "block_reference": {
                    "id": block_ref.id,
                    "block_id": block_ref.block_id,
                    "insertion_point": [block_ref.insertion_point.x, block_ref.insertion_point.y],
                    "layer_id": block_ref.layer_id
                }
            })

        except Exception as e:
            logger.error(f"Error inserting block reference: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to insert block reference: {str(e)}"
            )

    def get_block_references(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get block references in a document."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )

            block_refs = self.document_block_refs.get(document_id, [])
            
            refs_data = []
            for ref in block_refs:
                block = self.blocks.get(ref.block_id)
                ref_data = {
                    "id": ref.id,
                    "block_id": ref.block_id,
                    "block_name": block.name if block else "Unknown",
                    "insertion_point": [ref.insertion_point.x, ref.insertion_point.y],
                    "layer_id": ref.layer_id,
                    "scale": [ref.scale.x, ref.scale.y],
                    "rotation": ref.rotation,
                    "visible": ref.visible,
                    "locked": ref.locked,
                    "attribute_values": ref.attribute_values
                }
                refs_data.append(ref_data)

            return ProtobufConverters.create_success_response({
                "block_references": refs_data,
                "total_count": len(refs_data)
            })

        except Exception as e:
            logger.error(f"Error getting block references: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to get block references: {str(e)}"
            )

    def _parse_entity(self, entity_data: Dict[str, Any]):
        """Parse entity data into entity object."""
        # This would parse the entity data based on type
        # For now, return None as entity parsing is complex
        # In a real implementation, this would use the entity serialization system
        logger.warning("Entity parsing not implemented in block service")
        return None

    def _parse_attribute_definition(self, attr_data: Dict[str, Any]) -> Optional[AttributeDefinition]:
        """Parse attribute definition data."""
        try:
            return AttributeDefinition(
                name=attr_data["name"],
                type=AttributeType(attr_data["type"]),
                default_value=attr_data["default_value"],
                prompt=attr_data.get("prompt", ""),
                description=attr_data.get("description", ""),
                required=attr_data.get("required", True),
                choices=attr_data.get("choices"),
                min_value=attr_data.get("min_value"),
                max_value=attr_data.get("max_value"),
                visible=attr_data.get("visible", True)
            )
        except Exception as e:
            logger.error(f"Error parsing attribute definition: {e}")
            return None

    def _parse_block_reference(self, ref_data: Dict[str, Any]) -> Optional[BlockReference]:
        """Parse block reference data."""
        try:
            insertion_point_data = ref_data.get("insertion_point", [0, 0])
            insertion_point = Point2D(insertion_point_data[0], insertion_point_data[1])
            
            block_ref = BlockReference(
                block_id=ref_data["block_id"],
                insertion_point=insertion_point,
                layer_id=ref_data.get("layer_id", "0")
            )
            
            # Set transformation properties
            if "scale" in ref_data:
                scale_data = ref_data["scale"]
                if isinstance(scale_data, list) and len(scale_data) >= 2:
                    block_ref.set_scale(scale_data[0], scale_data[1])
                else:
                    block_ref.set_scale(float(scale_data))
                    
            if "rotation" in ref_data:
                block_ref.set_rotation(float(ref_data["rotation"]))
                
            # Set attribute values
            if "attribute_values" in ref_data:
                for name, value in ref_data["attribute_values"].items():
                    block_ref.set_attribute_value(name, value)
                    
            # Set other properties
            if "visible" in ref_data:
                block_ref.visible = bool(ref_data["visible"])
            if "locked" in ref_data:
                block_ref.locked = bool(ref_data["locked"])
                
            return block_ref
            
        except Exception as e:
            logger.error(f"Error parsing block reference: {e}")
            return None