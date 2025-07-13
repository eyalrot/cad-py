"""Layer service implementation."""

import logging
from typing import Dict, Any, Optional

from backend.models import Layer, Color, LineType
from .converters import ProtobufConverters
from .document_service import DocumentService


logger = logging.getLogger(__name__)


class LayerService:
    """Service for layer operations."""
    
    def __init__(self, document_service: DocumentService):
        self.document_service = document_service
    
    def create_layer(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new layer in a document."""
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
            
            name = request.get("name", "")
            if not name:
                return ProtobufConverters.create_error_response(
                    error_message="Layer name is required"
                )
            
            # Create layer with properties
            color = Color.BLACK
            if "color" in request:
                color = ProtobufConverters.color_from_proto(request["color"])
            
            line_type = LineType.CONTINUOUS
            if "line_type" in request:
                line_type = ProtobufConverters.line_type_from_proto(request["line_type"])
            
            line_weight = request.get("line_weight", 0.25)
            
            layer = Layer(name, color, line_type, line_weight)
            
            # Add layer to document
            layer_id = document.add_layer(layer)
            
            logger.info(f"Created layer {layer_id} in document {document_id}")
            
            return ProtobufConverters.create_success_response({
                "layer": ProtobufConverters.layer_to_proto(layer)
            })
            
        except ValueError as e:
            logger.warning(f"Validation error creating layer: {e}")
            return ProtobufConverters.create_error_response(error_message=str(e))
        except Exception as e:
            logger.error(f"Error creating layer: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to create layer: {str(e)}"
            )
    
    def update_layer(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Update layer properties."""
        try:
            document_id = request.get("document_id", "")
            layer_id = request.get("layer_id", "")
            
            if not document_id or not layer_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID and Layer ID are required"
                )
            
            document = self.document_service.get_document(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )
            
            layer = document.get_layer(layer_id)
            if not layer:
                return ProtobufConverters.create_error_response(
                    error_message=f"Layer {layer_id} not found"
                )
            
            # Update properties if provided
            if "name" in request:
                document.rename_layer(layer_id, request["name"])
            
            if "color" in request:
                color = ProtobufConverters.color_from_proto(request["color"])
                layer.set_color(color)
            
            if "line_type" in request:
                line_type = ProtobufConverters.line_type_from_proto(request["line_type"])
                layer.set_line_type(line_type)
            
            if "line_weight" in request:
                layer.set_line_weight(request["line_weight"])
            
            if "visible" in request:
                layer.set_visible(request["visible"])
            
            if "locked" in request:
                layer.set_locked(request["locked"])
            
            if "printable" in request:
                layer.set_printable(request["printable"])
            
            if "frozen" in request:
                layer.set_frozen(request["frozen"])
            
            if "description" in request:
                layer.set_description(request["description"])
            
            if "properties" in request:
                layer.update_properties(**dict(request["properties"]))
            
            logger.info(f"Updated layer {layer_id} in document {document_id}")
            
            return ProtobufConverters.create_success_response({
                "layer": ProtobufConverters.layer_to_proto(layer)
            })
            
        except ValueError as e:
            logger.warning(f"Validation error updating layer: {e}")
            return ProtobufConverters.create_error_response(error_message=str(e))
        except Exception as e:
            logger.error(f"Error updating layer: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to update layer: {str(e)}"
            )
    
    def delete_layer(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a layer from a document."""
        try:
            document_id = request.get("document_id", "")
            layer_id = request.get("layer_id", "")
            
            if not document_id or not layer_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID and Layer ID are required"
                )
            
            document = self.document_service.get_document(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )
            
            success = document.remove_layer(layer_id)
            if not success:
                return ProtobufConverters.create_error_response(
                    error_message=f"Layer {layer_id} not found"
                )
            
            logger.info(f"Deleted layer {layer_id} from document {document_id}")
            
            return ProtobufConverters.create_success_response()
            
        except ValueError as e:
            logger.warning(f"Validation error deleting layer: {e}")
            return ProtobufConverters.create_error_response(error_message=str(e))
        except Exception as e:
            logger.error(f"Error deleting layer: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to delete layer: {str(e)}"
            )
    
    def get_layer(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get a specific layer."""
        try:
            document_id = request.get("document_id", "")
            layer_id = request.get("layer_id", "")
            
            if not document_id or not layer_id:
                return {
                    "found": False,
                    "error_message": "Document ID and Layer ID are required"
                }
            
            document = self.document_service.get_document(document_id)
            if not document:
                return {
                    "found": False,
                    "error_message": f"Document {document_id} not found"
                }
            
            layer = document.get_layer(layer_id)
            if not layer:
                return {
                    "found": False,
                    "error_message": f"Layer {layer_id} not found"
                }
            
            return {
                "layer": ProtobufConverters.layer_to_proto(layer),
                "found": True,
                "error_message": ""
            }
            
        except Exception as e:
            logger.error(f"Error getting layer: {e}")
            return {
                "found": False,
                "error_message": f"Failed to get layer: {str(e)}"
            }
    
    def list_layers(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """List all layers in a document."""
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
            
            layers = document.list_layers()
            
            return ProtobufConverters.create_success_response({
                "layers": [ProtobufConverters.layer_to_proto(layer) for layer in layers]
            })
            
        except Exception as e:
            logger.error(f"Error listing layers: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to list layers: {str(e)}"
            )
    
    def set_current_layer(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Set the current layer for a document."""
        try:
            document_id = request.get("document_id", "")
            layer_id = request.get("layer_id", "")
            
            if not document_id or not layer_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID and Layer ID are required"
                )
            
            document = self.document_service.get_document(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )
            
            document.set_current_layer(layer_id)
            
            logger.info(f"Set current layer to {layer_id} in document {document_id}")
            
            return ProtobufConverters.create_success_response()
            
        except ValueError as e:
            logger.warning(f"Validation error setting current layer: {e}")
            return ProtobufConverters.create_error_response(error_message=str(e))
        except Exception as e:
            logger.error(f"Error setting current layer: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to set current layer: {str(e)}"
            )