"""Tests for CADGrpcService."""

import pytest

from backend.api.cad_grpc_service import CADGrpcService


class TestCADGrpcService:
    """Test CADGrpcService integration."""

    def setup_method(self):
        """Setup test method."""
        self.service = CADGrpcService()

    def test_service_initialization(self):
        """Test service initialization."""
        assert self.service.document_service is not None
        assert self.service.layer_service is not None
        assert self.service.entity_service is not None
        assert self.service.drawing_service is not None

    def test_health_check(self):
        """Test health check."""
        health = self.service.health_check()

        assert health["status"] == "healthy"
        assert "document_count" in health
        assert health["message"] == "CAD service is running"

    def test_get_service_info(self):
        """Test service information."""
        info = self.service.get_service_info()

        assert info["service_name"] == "CAD gRPC Service"
        assert info["version"] == "1.0.0"
        assert "Document management" in info["supported_operations"]
        assert "JSON" in info["supported_formats"]
        assert info["streaming_supported"] is True

    def test_document_workflow(self):
        """Test complete document workflow."""
        # Create document
        create_request = {
            "name": "Workflow Test",
            "description": "Integration test document",
        }

        create_response = self.service.CreateDocument(create_request)
        assert create_response["success"] is True

        document_id = create_response["document"]["id"]

        # Open document
        open_request = {"document_id": document_id}
        open_response = self.service.OpenDocument(open_request)
        assert open_response["found"] is True

        # Update document
        update_request = {
            "document_id": document_id,
            "description": "Updated description",
        }
        update_response = self.service.UpdateDocument(update_request)
        assert update_response["success"] is True

        # Get statistics
        stats_request = {"document_id": document_id}
        stats_response = self.service.GetDocumentStatistics(stats_request)
        assert stats_response["success"] is True

        # List documents
        list_response = self.service.ListDocuments({})
        assert list_response["success"] is True
        assert len(list_response["documents"]) >= 1

        # Delete document
        delete_request = {"document_id": document_id}
        delete_response = self.service.DeleteDocument(delete_request)
        assert delete_response["success"] is True

    def test_layer_workflow(self):
        """Test complete layer workflow."""
        # Create document first
        doc_request = {"name": "Layer Test"}
        doc_response = self.service.CreateDocument(doc_request)
        document_id = doc_response["document"]["id"]

        # Create layer
        layer_request = {
            "document_id": document_id,
            "name": "Test Layer",
            "color": {"red": 255, "green": 0, "blue": 0, "alpha": 255},
        }
        layer_response = self.service.CreateLayer(layer_request)
        assert layer_response["success"] is True

        layer_id = layer_response["layer"]["id"]

        # Get layer
        get_request = {"document_id": document_id, "layer_id": layer_id}
        get_response = self.service.GetLayer(get_request)
        assert get_response["found"] is True

        # Update layer
        update_request = {
            "document_id": document_id,
            "layer_id": layer_id,
            "name": "Updated Layer",
        }
        update_response = self.service.UpdateLayer(update_request)
        assert update_response["success"] is True

        # Set current layer
        current_request = {"document_id": document_id, "layer_id": layer_id}
        current_response = self.service.SetCurrentLayer(current_request)
        assert current_response["success"] is True

        # List layers
        list_request = {"document_id": document_id}
        list_response = self.service.ListLayers(list_request)
        assert list_response["success"] is True
        assert len(list_response["layers"]) >= 2  # Default + created

        # Delete layer
        delete_request = {"document_id": document_id, "layer_id": layer_id}
        delete_response = self.service.DeleteLayer(delete_request)
        assert delete_response["success"] is True

    def test_drawing_workflow(self):
        """Test drawing operations workflow."""
        # Create document
        doc_request = {"name": "Drawing Test"}
        doc_response = self.service.CreateDocument(doc_request)
        document_id = doc_response["document"]["id"]

        # Draw line
        line_request = {
            "document_id": document_id,
            "start": {"x": 0, "y": 0},
            "end": {"x": 10, "y": 10},
            "properties": {"color": "red"},
        }
        line_response = self.service.DrawLine(line_request)
        assert line_response["success"] is True

        # Draw circle
        circle_request = {
            "document_id": document_id,
            "center": {"x": 5, "y": 5},
            "radius": 3.0,
            "properties": {"fill": "blue"},
        }
        circle_response = self.service.DrawCircle(circle_request)
        assert circle_response["success"] is True

        # Draw arc
        arc_request = {
            "document_id": document_id,
            "center": {"x": 0, "y": 0},
            "radius": 5.0,
            "start_angle": 0.0,
            "end_angle": 90.0,
        }
        arc_response = self.service.DrawArc(arc_request)
        assert arc_response["success"] is True

        # Draw rectangle
        rect_request = {
            "document_id": document_id,
            "corner1": {"x": 0, "y": 0},
            "corner2": {"x": 5, "y": 3},
        }
        rect_response = self.service.DrawRectangle(rect_request)
        assert rect_response["success"] is True

        # Draw polygon
        polygon_request = {
            "document_id": document_id,
            "vertices": [{"x": 0, "y": 0}, {"x": 2, "y": 0}, {"x": 1, "y": 2}],
            "closed": True,
        }
        polygon_response = self.service.DrawPolygon(polygon_request)
        assert polygon_response["success"] is True

    def test_entity_operations(self):
        """Test entity operations."""
        # Create document
        doc_request = {"name": "Entity Test"}
        doc_response = self.service.CreateDocument(doc_request)
        document_id = doc_response["document"]["id"]

        # Create entity
        entity_request = {
            "document_id": document_id,
            "entity_type": "test",
            "geometry": {"test": "data"},
            "properties": {"name": "test_entity"},
        }
        entity_response = self.service.CreateEntity(entity_request)
        assert entity_response["success"] is True

        entity_id = entity_response["entity"]["id"]

        # Get entity
        get_request = {"document_id": document_id, "entity_id": entity_id}
        get_response = self.service.GetEntity(get_request)
        assert get_response["found"] is True

        # Update entity
        update_request = {
            "document_id": document_id,
            "entity_id": entity_id,
            "properties": {"updated": "true"},
        }
        update_response = self.service.UpdateEntity(update_request)
        assert update_response["success"] is True

        # Query entities
        query_request = {"document_id": document_id}
        entities = list(self.service.QueryEntities(query_request))
        assert len(entities) >= 1

        # Delete entity
        delete_request = {"document_id": document_id, "entity_id": entity_id}
        delete_response = self.service.DeleteEntity(delete_request)
        assert delete_response["success"] is True

    def test_batch_operations(self):
        """Test batch entity operations."""
        # Create document
        doc_request = {"name": "Batch Test"}
        doc_response = self.service.CreateDocument(doc_request)
        document_id = doc_response["document"]["id"]

        # Batch create entities
        batch_create_request = {
            "document_id": document_id,
            "entities": [
                {
                    "entity_type": "line",
                    "geometry": {"start": {"x": 0, "y": 0}, "end": {"x": 1, "y": 1}},
                },
                {
                    "entity_type": "circle",
                    "geometry": {"center": {"x": 2, "y": 2}, "radius": 1},
                },
            ],
        }

        batch_create_response = self.service.BatchCreateEntities(batch_create_request)
        assert batch_create_response["success_count"] == 2
        assert len(batch_create_response["created_entities"]) == 2

        # Batch delete entities
        entity_ids = [
            entity["id"] for entity in batch_create_response["created_entities"]
        ]
        batch_delete_request = {"document_id": document_id, "entity_ids": entity_ids}

        batch_delete_response = self.service.BatchDeleteEntities(batch_delete_request)
        assert batch_delete_response["success"] is True
        assert batch_delete_response["deleted_count"] == 2

    def test_error_handling(self):
        """Test error handling across services."""
        # Test with invalid document ID
        invalid_request = {"document_id": "invalid"}

        # Document operations
        open_response = self.service.OpenDocument(invalid_request)
        assert open_response["found"] is False

        # Layer operations
        layer_request = invalid_request.copy()
        layer_request["name"] = "Test"
        layer_response = self.service.CreateLayer(layer_request)
        assert layer_response["success"] is False

        # Entity operations
        entity_request = invalid_request.copy()
        entity_request["entity_type"] = "test"
        entity_response = self.service.CreateEntity(entity_request)
        assert entity_response["success"] is False

        # Drawing operations
        line_request = invalid_request.copy()
        line_request.update({"start": {"x": 0, "y": 0}, "end": {"x": 1, "y": 1}})
        line_response = self.service.DrawLine(line_request)
        assert line_response["success"] is False
