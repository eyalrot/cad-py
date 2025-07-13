"""Tests for LayerService."""

import pytest

from backend.api.document_service import DocumentService
from backend.api.layer_service import LayerService


class TestLayerService:
    """Test LayerService class."""

    def setup_method(self):
        """Setup test method."""
        self.document_service = DocumentService()
        self.layer_service = LayerService(self.document_service)

        # Create a test document
        doc_request = {"name": "Test Document"}
        doc_response = self.document_service.create_document(doc_request)
        self.document_id = doc_response["document"]["id"]

    def test_create_layer(self):
        """Test layer creation."""
        request = {
            "document_id": self.document_id,
            "name": "Test Layer",
            "color": {"red": 255, "green": 0, "blue": 0, "alpha": 255},
            "line_type": "DASHED",
            "line_weight": 0.5,
        }

        response = self.layer_service.create_layer(request)

        assert response["success"] is True
        assert response["error_message"] == ""

        layer = response["layer"]
        assert layer["name"] == "Test Layer"
        assert layer["color"]["red"] == 255
        assert layer["line_type"] == "DASHED"
        assert layer["line_weight"] == 0.5

    def test_create_layer_without_name(self):
        """Test layer creation without name."""
        request = {"document_id": self.document_id}

        response = self.layer_service.create_layer(request)

        assert response["success"] is False
        assert "name is required" in response["error_message"]

    def test_create_layer_nonexistent_document(self):
        """Test layer creation in non-existent document."""
        request = {"document_id": "nonexistent", "name": "Test Layer"}

        response = self.layer_service.create_layer(request)

        assert response["success"] is False
        assert "not found" in response["error_message"]

    def test_create_duplicate_layer_name(self):
        """Test creating layer with duplicate name."""
        # Create first layer
        request = {"document_id": self.document_id, "name": "Duplicate Name"}
        response = self.layer_service.create_layer(request)
        assert response["success"] is True

        # Try to create another with same name
        response = self.layer_service.create_layer(request)
        assert response["success"] is False
        assert "already exists" in response["error_message"]

    def test_update_layer(self):
        """Test layer update."""
        # Create layer
        create_request = {"document_id": self.document_id, "name": "Update Test"}
        create_response = self.layer_service.create_layer(create_request)
        layer_id = create_response["layer"]["id"]

        # Update layer
        update_request = {
            "document_id": self.document_id,
            "layer_id": layer_id,
            "name": "Updated Name",
            "color": {"red": 0, "green": 255, "blue": 0, "alpha": 255},
            "line_type": "DOTTED",
            "visible": False,
            "locked": True,
            "description": "Updated description",
        }

        response = self.layer_service.update_layer(update_request)

        assert response["success"] is True
        layer = response["layer"]
        assert layer["name"] == "Updated Name"
        assert layer["color"]["green"] == 255
        assert layer["line_type"] == "DOTTED"
        assert layer["visible"] is False
        assert layer["locked"] is True
        assert layer["description"] == "Updated description"

    def test_update_nonexistent_layer(self):
        """Test updating non-existent layer."""
        request = {
            "document_id": self.document_id,
            "layer_id": "nonexistent",
            "name": "New Name",
        }

        response = self.layer_service.update_layer(request)

        assert response["success"] is False
        assert "not found" in response["error_message"]

    def test_delete_layer(self):
        """Test layer deletion."""
        # Create layer
        create_request = {"document_id": self.document_id, "name": "Delete Test"}
        create_response = self.layer_service.create_layer(create_request)
        layer_id = create_response["layer"]["id"]

        # Delete layer
        delete_request = {"document_id": self.document_id, "layer_id": layer_id}

        response = self.layer_service.delete_layer(delete_request)

        assert response["success"] is True

        # Verify layer is gone
        document = self.document_service.get_document(self.document_id)
        assert document.get_layer(layer_id) is None

    def test_delete_nonexistent_layer(self):
        """Test deleting non-existent layer."""
        request = {"document_id": self.document_id, "layer_id": "nonexistent"}

        response = self.layer_service.delete_layer(request)

        assert response["success"] is False
        assert "not found" in response["error_message"]

    def test_get_layer(self):
        """Test getting a specific layer."""
        # Create layer
        create_request = {"document_id": self.document_id, "name": "Get Test"}
        create_response = self.layer_service.create_layer(create_request)
        layer_id = create_response["layer"]["id"]

        # Get layer
        get_request = {"document_id": self.document_id, "layer_id": layer_id}

        response = self.layer_service.get_layer(get_request)

        assert response["found"] is True
        assert response["error_message"] == ""
        assert response["layer"]["name"] == "Get Test"

    def test_get_nonexistent_layer(self):
        """Test getting non-existent layer."""
        request = {"document_id": self.document_id, "layer_id": "nonexistent"}

        response = self.layer_service.get_layer(request)

        assert response["found"] is False
        assert "not found" in response["error_message"]

    def test_list_layers(self):
        """Test listing all layers."""
        # Create additional layers
        for i in range(3):
            request = {"document_id": self.document_id, "name": f"Layer {i}"}
            self.layer_service.create_layer(request)

        # List layers
        request = {"document_id": self.document_id}
        response = self.layer_service.list_layers(request)

        assert response["success"] is True
        assert len(response["layers"]) == 4  # 3 created + 1 default

    def test_set_current_layer(self):
        """Test setting current layer."""
        # Create layer
        create_request = {"document_id": self.document_id, "name": "Current Test"}
        create_response = self.layer_service.create_layer(create_request)
        layer_id = create_response["layer"]["id"]

        # Set as current
        current_request = {"document_id": self.document_id, "layer_id": layer_id}

        response = self.layer_service.set_current_layer(current_request)

        assert response["success"] is True

        # Verify current layer is set
        document = self.document_service.get_document(self.document_id)
        assert document.current_layer_id == layer_id

    def test_set_current_layer_nonexistent(self):
        """Test setting non-existent layer as current."""
        request = {"document_id": self.document_id, "layer_id": "nonexistent"}

        response = self.layer_service.set_current_layer(request)

        assert response["success"] is False
        assert "does not exist" in response["error_message"]
