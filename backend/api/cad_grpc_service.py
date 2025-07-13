"""Main CAD gRPC service implementation."""

import logging
from typing import Any, Dict, Iterator

from .document_service import DocumentService
from .drawing_service import DrawingService
from .entity_service import EntityService
from .layer_service import LayerService
from .block_service import BlockAPIService
from .export_service import ExportAPIService

logger = logging.getLogger(__name__)


class CADGrpcService:
    """Main CAD gRPC service that orchestrates all operations.

    This service implements the gRPC interface defined in cad_service.proto.
    In a real implementation, this would inherit from the generated
    cad_service_pb2_grpc.CADServiceServicer class.
    """

    def __init__(self):
        """Initialize the CAD gRPC service."""
        self.document_service = DocumentService()
        self.layer_service = LayerService(self.document_service)
        self.entity_service = EntityService(self.document_service)
        self.drawing_service = DrawingService(
            self.document_service, self.entity_service
        )
        self.block_service = BlockAPIService(self.document_service)
        self.export_service = ExportAPIService(self.document_service)

        logger.info("CAD gRPC service initialized")

    # Document operations
    def CreateDocument(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Create a new document."""
        return self.document_service.create_document(request)

    def OpenDocument(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Open an existing document."""
        return self.document_service.open_document(request)

    def SaveDocument(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Save a document to file."""
        return self.document_service.save_document(request)

    def LoadDocument(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Load a document from file."""
        return self.document_service.load_document(request)

    def UpdateDocument(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Update document properties."""
        return self.document_service.update_document(request)

    def DeleteDocument(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Delete a document."""
        return self.document_service.delete_document(request)

    def GetDocumentStatistics(
        self, request: Dict[str, Any], context=None
    ) -> Dict[str, Any]:
        """Get document statistics."""
        return self.document_service.get_document_statistics(request)

    def ListDocuments(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """List all documents."""
        return self.document_service.list_documents(request)

    # Layer operations
    def CreateLayer(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Create a new layer."""
        return self.layer_service.create_layer(request)

    def UpdateLayer(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Update layer properties."""
        return self.layer_service.update_layer(request)

    def DeleteLayer(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Delete a layer."""
        return self.layer_service.delete_layer(request)

    def GetLayer(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Get a specific layer."""
        return self.layer_service.get_layer(request)

    def ListLayers(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """List all layers in a document."""
        return self.layer_service.list_layers(request)

    def SetCurrentLayer(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Set the current layer for a document."""
        return self.layer_service.set_current_layer(request)

    # Entity operations
    def CreateEntity(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Create a new entity."""
        return self.entity_service.create_entity(request)

    def UpdateEntity(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Update entity properties."""
        return self.entity_service.update_entity(request)

    def DeleteEntity(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Delete an entity."""
        return self.entity_service.delete_entity(request)

    def GetEntity(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Get a specific entity."""
        return self.entity_service.get_entity(request)

    def QueryEntities(
        self, request: Dict[str, Any], context=None
    ) -> Iterator[Dict[str, Any]]:
        """Query entities with optional filter (streaming)."""
        return self.entity_service.query_entities(request)

    def MoveEntities(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Move entities to a different layer."""
        return self.entity_service.move_entities(request)

    # Batch operations
    def BatchCreateEntities(
        self, request: Dict[str, Any], context=None
    ) -> Dict[str, Any]:
        """Create multiple entities in a batch."""
        return self.entity_service.batch_create_entities(request)

    def BatchDeleteEntities(
        self, request: Dict[str, Any], context=None
    ) -> Dict[str, Any]:
        """Delete multiple entities in a batch."""
        return self.entity_service.batch_delete_entities(request)

    # Drawing operations (convenience methods)
    def DrawLine(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Draw a line entity."""
        return self.drawing_service.draw_line(request)

    def DrawCircle(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Draw a circle entity."""
        return self.drawing_service.draw_circle(request)

    def DrawArc(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Draw an arc entity."""
        return self.drawing_service.draw_arc(request)

    def DrawRectangle(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Draw a rectangle entity."""
        return self.drawing_service.draw_rectangle(request)

    def DrawPolygon(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Draw a polygon entity."""
        return self.drawing_service.draw_polygon(request)

    # Block operations
    def CreateBlock(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Create a new block definition."""
        return self.block_service.create_block(request)

    def GetBlocks(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Get list of available blocks."""
        return self.block_service.get_blocks(request)

    def GetBlock(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Get detailed information about a specific block."""
        return self.block_service.get_block(request)

    def UpdateBlock(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Update an existing block definition."""
        return self.block_service.update_block(request)

    def DeleteBlock(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Delete a block definition."""
        return self.block_service.delete_block(request)

    def InsertBlockReference(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Insert a block reference into a document."""
        return self.block_service.insert_block_reference(request)

    def GetBlockReferences(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Get block references in a document."""
        return self.block_service.get_block_references(request)

    # Export operations
    def GetSupportedExportFormats(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Get list of supported export formats."""
        return self.export_service.get_supported_formats(request)

    def ExportDocument(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Export a document to specified format."""
        return self.export_service.export_document(request)

    def GetExportOptions(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Get available export options for a format."""
        return self.export_service.get_export_options(request)

    def PreviewExport(self, request: Dict[str, Any], context=None) -> Dict[str, Any]:
        """Generate export preview information."""
        return self.export_service.preview_export(request)

    # Health check and utility methods
    def health_check(self) -> Dict[str, Any]:
        """Check service health."""
        try:
            document_count = len(self.document_service._documents)
            return {
                "status": "healthy",
                "document_count": document_count,
                "message": "CAD service is running",
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "message": f"Service error: {str(e)}"}

    def get_service_info(self) -> Dict[str, Any]:
        """Get service information."""
        return {
            "service_name": "CAD gRPC Service",
            "version": "1.0.0",
            "supported_operations": [
                "Document management",
                "Layer operations",
                "Entity CRUD",
                "Drawing tools",
                "Batch operations",
                "Block system",
                "Export operations",
            ],
            "supported_formats": ["JSON", "Binary"],
            "max_entities_per_document": 100000,
            "streaming_supported": True,
        }
