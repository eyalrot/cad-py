"""Entity service implementation."""

import logging
from typing import Dict, Any, Optional, List, Iterator

from backend.models import EntityFilter
from .converters import ProtobufConverters
from .document_service import DocumentService


logger = logging.getLogger(__name__)


class MockGeometryEntity:
    """Mock entity for geometry operations until geometry entities are implemented."""
    
    def __init__(self, layer_id: str, entity_type: str, geometry_data: Dict[str, Any]):
        from backend.models.entity import BaseEntity
        
        # Create a minimal entity for testing
        self.id = None  # Will be set by BaseEntity
        self.entity_type = entity_type
        self.layer_id = layer_id
        self.geometry_data = geometry_data
        self.properties = {}
        self.visible = True
        self.locked = False
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize entity to dictionary."""
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "layer_id": self.layer_id,
            "geometry": self.geometry_data,
            "properties": self.properties,
            "visible": self.visible,
            "locked": self.locked
        }


class EntityService:
    """Service for entity operations."""
    
    def __init__(self, document_service: DocumentService):
        self.document_service = document_service
    
    def create_entity(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new entity in a document."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )
            
            document = self.document_service.get_document(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )
            
            entity_type = request.get("entity_type", "")
            if not entity_type:
                return ProtobufConverters.create_error_response(
                    error_message="Entity type is required"
                )
            
            layer_id = request.get("layer_id", document.current_layer_id)
            
            # Validate layer exists
            layer = document.get_layer(layer_id)
            if not layer:
                return ProtobufConverters.create_error_response(
                    error_message=f"Layer {layer_id} not found"
                )
            
            # Extract geometry data
            geometry = request.get("geometry", {})
            properties = dict(request.get("properties", {}))
            
            # Create mock entity (would be replaced with actual geometry entities)
            entity = MockGeometryEntity(layer_id, entity_type, geometry)
            entity.properties = properties
            
            # Note: In real implementation, would call document.add_entity(entity)
            # For now, just simulate success
            
            logger.info(f"Created {entity_type} entity in document {document_id}")
            
            # Mock entity response
            entity_proto = {
                "id": "mock-entity-id",
                "entity_type": entity_type,
                "layer_id": layer_id,
                "geometry": geometry,
                "properties": properties,
                "visible": True,
                "locked": False,
                "created_at": "2023-01-01T00:00:00",
                "modified_at": "2023-01-01T00:00:00"
            }
            
            return ProtobufConverters.create_success_response({
                "entity": entity_proto
            })
            
        except Exception as e:
            logger.error(f"Error creating entity: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to create entity: {str(e)}"
            )
    
    def update_entity(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Update entity properties."""
        try:
            document_id = request.get("document_id", "")
            entity_id = request.get("entity_id", "")
            
            if not document_id or not entity_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID and Entity ID are required"
                )
            
            document = self.document_service.get_document(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )
            
            # In real implementation: entity = document.get_entity(entity_id)
            # For now, simulate success
            
            logger.info(f"Updated entity {entity_id} in document {document_id}")
            
            # Mock updated entity response
            entity_proto = {
                "id": entity_id,
                "entity_type": "mock",
                "layer_id": request.get("layer_id", document.current_layer_id),
                "geometry": request.get("geometry", {}),
                "properties": dict(request.get("properties", {})),
                "visible": request.get("visible", True),
                "locked": request.get("locked", False),
                "created_at": "2023-01-01T00:00:00",
                "modified_at": "2023-01-01T00:00:00"
            }
            
            return ProtobufConverters.create_success_response({
                "entity": entity_proto
            })
            
        except Exception as e:
            logger.error(f"Error updating entity: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to update entity: {str(e)}"
            )
    
    def delete_entity(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Delete an entity from a document."""
        try:
            document_id = request.get("document_id", "")
            entity_id = request.get("entity_id", "")
            
            if not document_id or not entity_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID and Entity ID are required"
                )
            
            document = self.document_service.get_document(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )
            
            # In real implementation: success = document.remove_entity(entity_id)
            # For now, simulate success
            
            logger.info(f"Deleted entity {entity_id} from document {document_id}")
            
            return ProtobufConverters.create_success_response()
            
        except Exception as e:
            logger.error(f"Error deleting entity: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to delete entity: {str(e)}"
            )
    
    def get_entity(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific entity."""
        try:
            document_id = request.get("document_id", "")
            entity_id = request.get("entity_id", "")
            
            if not document_id or not entity_id:
                return {
                    "found": False,
                    "error_message": "Document ID and Entity ID are required"
                }
            
            document = self.document_service.get_document(document_id)
            if not document:
                return {
                    "found": False,
                    "error_message": f"Document {document_id} not found"
                }
            
            # In real implementation: entity = document.get_entity(entity_id)
            # For now, simulate found entity
            
            entity_proto = {
                "id": entity_id,
                "entity_type": "mock",
                "layer_id": document.current_layer_id,
                "geometry": {},
                "properties": {},
                "visible": True,
                "locked": False,
                "created_at": "2023-01-01T00:00:00",
                "modified_at": "2023-01-01T00:00:00"
            }
            
            return {
                "entity": entity_proto,
                "found": True,
                "error_message": ""
            }
            
        except Exception as e:
            logger.error(f"Error getting entity: {e}")
            return {
                "found": False,
                "error_message": f"Failed to get entity: {str(e)}"
            }
    
    def query_entities(self, request: Dict[str, Any]) -> Iterator[Dict[str, Any]]:
        """Query entities with optional filter (streaming)."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                logger.error("Document ID is required for entity query")
                return
            
            document = self.document_service.get_document(document_id)
            if not document:
                logger.error(f"Document {document_id} not found")
                return
            
            # Parse filter if provided
            entity_filter = None
            if "filter" in request:
                entity_filter = ProtobufConverters.entity_filter_from_proto(request["filter"])
            
            # In real implementation: entities = document.query_entities(entity_filter)
            # For now, return mock entities
            
            limit = request.get("limit", 100)
            offset = request.get("offset", 0)
            
            # Generate mock entities
            for i in range(offset, min(offset + limit, offset + 5)):  # Mock 5 entities
                entity_proto = {
                    "id": f"mock-entity-{i}",
                    "entity_type": "mock",
                    "layer_id": document.current_layer_id,
                    "geometry": {"mock_data": i},
                    "properties": {"index": str(i)},
                    "visible": True,
                    "locked": False,
                    "created_at": "2023-01-01T00:00:00",
                    "modified_at": "2023-01-01T00:00:00"
                }
                yield entity_proto
            
            logger.info(f"Queried entities in document {document_id}")
            
        except Exception as e:
            logger.error(f"Error querying entities: {e}")
    
    def move_entities(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Move entities to a different layer."""
        try:
            document_id = request.get("document_id", "")
            entity_ids = list(request.get("entity_ids", []))
            target_layer_id = request.get("target_layer_id", "")
            
            if not document_id or not entity_ids or not target_layer_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID, entity IDs, and target layer ID are required"
                )
            
            document = self.document_service.get_document(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )
            
            # Validate target layer exists
            target_layer = document.get_layer(target_layer_id)
            if not target_layer:
                return ProtobufConverters.create_error_response(
                    error_message=f"Target layer {target_layer_id} not found"
                )
            
            # In real implementation: moved_count = document.move_entities_to_layer(entity_ids, target_layer_id)
            moved_count = len(entity_ids)  # Mock success
            
            logger.info(f"Moved {moved_count} entities to layer {target_layer_id} in document {document_id}")
            
            return ProtobufConverters.create_success_response({
                "moved_count": moved_count
            })
            
        except Exception as e:
            logger.error(f"Error moving entities: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to move entities: {str(e)}"
            )
    
    def batch_create_entities(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create multiple entities in a batch."""
        try:
            document_id = request.get("document_id", "")
            entities_requests = request.get("entities", [])
            
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )
            
            document = self.document_service.get_document(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )
            
            created_entities = []
            error_messages = []
            
            for i, entity_request in enumerate(entities_requests):
                try:
                    # Create each entity (would use actual entity creation)
                    entity_proto = {
                        "id": f"batch-entity-{i}",
                        "entity_type": entity_request.get("entity_type", "mock"),
                        "layer_id": entity_request.get("layer_id", document.current_layer_id),
                        "geometry": entity_request.get("geometry", {}),
                        "properties": dict(entity_request.get("properties", {})),
                        "visible": True,
                        "locked": False,
                        "created_at": "2023-01-01T00:00:00",
                        "modified_at": "2023-01-01T00:00:00"
                    }
                    created_entities.append(entity_proto)
                except Exception as e:
                    error_messages.append(f"Entity {i}: {str(e)}")
            
            logger.info(f"Batch created {len(created_entities)} entities in document {document_id}")
            
            return {
                "created_entities": created_entities,
                "success_count": len(created_entities),
                "error_messages": error_messages
            }
            
        except Exception as e:
            logger.error(f"Error in batch create entities: {e}")
            return {
                "created_entities": [],
                "success_count": 0,
                "error_messages": [f"Batch operation failed: {str(e)}"]
            }
    
    def batch_delete_entities(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Delete multiple entities in a batch."""
        try:
            document_id = request.get("document_id", "")
            entity_ids = list(request.get("entity_ids", []))
            
            if not document_id or not entity_ids:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID and entity IDs are required"
                )
            
            document = self.document_service.get_document(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )
            
            # In real implementation: would delete each entity
            deleted_count = len(entity_ids)  # Mock success
            error_messages = []
            
            logger.info(f"Batch deleted {deleted_count} entities from document {document_id}")
            
            return {
                "deleted_count": deleted_count,
                "success": True,
                "error_messages": error_messages
            }
            
        except Exception as e:
            logger.error(f"Error in batch delete entities: {e}")
            return {
                "deleted_count": 0,
                "success": False,
                "error_messages": [f"Batch operation failed: {str(e)}"]
            }