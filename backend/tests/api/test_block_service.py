"""Tests for block API service functionality."""

import pytest
from unittest.mock import MagicMock

from backend.api.block_service import BlockAPIService
from backend.api.document_service import DocumentService
from backend.models.document import CADDocument
from backend.models.layer import Layer, Color
from backend.core.geometry.point import Point2D


class TestBlockAPIService:
    """Test block API service functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        # Mock document service
        self.document_service = MagicMock(spec=DocumentService)
        
        # Create test document
        self.test_doc = CADDocument("test_doc")
        layer = Layer("layer1", "Test Layer", Color(255, 0, 0))
        self.test_doc.add_layer(layer)
        
        self.document_service.get_document.return_value = self.test_doc
        
        # Create block service
        self.block_service = BlockAPIService(self.document_service)

    def test_create_block_success(self):
        """Test successful block creation."""
        request = {
            "block_data": {
                "name": "TestBlock",
                "base_point": [10, 20],
                "block_type": "static",
                "description": "Test block description",
                "category": "Test",
                "entities": [],
                "attributes": {}
            }
        }
        
        response = self.block_service.create_block(request)
        
        assert response["success"] is True
        assert "block" in response["data"]
        assert response["data"]["block"]["name"] == "TestBlock"
        assert len(self.block_service.blocks) == 1

    def test_create_block_missing_name(self):
        """Test block creation with missing name."""
        request = {
            "block_data": {
                "base_point": [10, 20]
            }
        }
        
        response = self.block_service.create_block(request)
        
        assert response["success"] is False
        assert "Block name is required" in response["error_message"]

    def test_create_block_duplicate_name(self):
        """Test block creation with duplicate name."""
        # Create first block
        request1 = {
            "block_data": {
                "name": "TestBlock",
                "base_point": [10, 20]
            }
        }
        self.block_service.create_block(request1)
        
        # Try to create second block with same name
        request2 = {
            "block_data": {
                "name": "TestBlock",
                "base_point": [30, 40]
            }
        }
        
        response = self.block_service.create_block(request2)
        
        assert response["success"] is False
        assert "already exists" in response["error_message"]

    def test_get_blocks_all(self):
        """Test getting all blocks."""
        # Create test blocks
        self._create_test_blocks()
        
        request = {}
        response = self.block_service.get_blocks(request)
        
        assert response["success"] is True
        assert "blocks" in response["data"]
        assert response["data"]["total_count"] == 3

    def test_get_blocks_by_category(self):
        """Test getting blocks by category."""
        # Create test blocks
        self._create_test_blocks()
        
        request = {"category": "Symbols"}
        response = self.block_service.get_blocks(request)
        
        assert response["success"] is True
        blocks = response["data"]["blocks"]
        assert len(blocks) == 2  # Only Symbol blocks
        assert all(block["category"] == "Symbols" for block in blocks)

    def test_get_blocks_search(self):
        """Test searching blocks."""
        # Create test blocks
        self._create_test_blocks()
        
        request = {"search_query": "door"}
        response = self.block_service.get_blocks(request)
        
        assert response["success"] is True
        blocks = response["data"]["blocks"]
        assert len(blocks) == 1
        assert blocks[0]["name"] == "Door"

    def test_get_block_success(self):
        """Test getting specific block."""
        # Create test block
        create_request = {
            "block_data": {
                "name": "TestBlock",
                "base_point": [10, 20],
                "description": "Test description"
            }
        }
        create_response = self.block_service.create_block(create_request)
        block_id = create_response["data"]["block"]["id"]
        
        # Get the block
        get_request = {"block_id": block_id}
        response = self.block_service.get_block(get_request)
        
        assert response["success"] is True
        assert "block" in response["data"]
        assert response["data"]["block"]["name"] == "TestBlock"
        assert response["data"]["block"]["description"] == "Test description"

    def test_get_block_not_found(self):
        """Test getting non-existent block."""
        request = {"block_id": "nonexistent"}
        response = self.block_service.get_block(request)
        
        assert response["success"] is False
        assert "not found" in response["error_message"]

    def test_update_block_success(self):
        """Test updating block."""
        # Create test block
        create_request = {
            "block_data": {
                "name": "TestBlock",
                "base_point": [10, 20],
                "description": "Original description"
            }
        }
        create_response = self.block_service.create_block(create_request)
        block_id = create_response["data"]["block"]["id"]
        
        # Update the block
        update_request = {
            "block_id": block_id,
            "updates": {
                "name": "UpdatedBlock",
                "description": "Updated description"
            }
        }
        response = self.block_service.update_block(update_request)
        
        assert response["success"] is True
        
        # Verify update
        block = self.block_service.blocks[block_id]
        assert block.name == "UpdatedBlock"
        assert block.description == "Updated description"

    def test_update_block_name_conflict(self):
        """Test updating block with conflicting name."""
        # Create two blocks
        self.block_service.create_block({
            "block_data": {"name": "Block1", "base_point": [0, 0]}
        })
        create_response = self.block_service.create_block({
            "block_data": {"name": "Block2", "base_point": [0, 0]}
        })
        block2_id = create_response["data"]["block"]["id"]
        
        # Try to rename Block2 to Block1
        update_request = {
            "block_id": block2_id,
            "updates": {"name": "Block1"}
        }
        response = self.block_service.update_block(update_request)
        
        assert response["success"] is False
        assert "already exists" in response["error_message"]

    def test_delete_block_success(self):
        """Test deleting block."""
        # Create test block
        create_request = {
            "block_data": {
                "name": "TestBlock",
                "base_point": [10, 20]
            }
        }
        create_response = self.block_service.create_block(create_request)
        block_id = create_response["data"]["block"]["id"]
        
        # Delete the block
        delete_request = {"block_id": block_id}
        response = self.block_service.delete_block(delete_request)
        
        assert response["success"] is True
        assert block_id not in self.block_service.blocks

    def test_delete_block_in_use(self):
        """Test deleting block that's in use."""
        # Create test block
        create_request = {
            "block_data": {
                "name": "TestBlock",
                "base_point": [10, 20]
            }
        }
        create_response = self.block_service.create_block(create_request)
        block_id = create_response["data"]["block"]["id"]
        
        # Add a block reference to simulate usage
        from backend.models.block import BlockReference
        ref = BlockReference(block_id, Point2D(0, 0))
        self.block_service.document_block_refs["test_doc"] = [ref]
        
        # Try to delete without force
        delete_request = {"block_id": block_id}
        response = self.block_service.delete_block(delete_request)
        
        assert response["success"] is False
        assert "in use" in response["error_message"]
        
        # Delete with force
        delete_request["force"] = True
        response = self.block_service.delete_block(delete_request)
        
        assert response["success"] is True
        assert block_id not in self.block_service.blocks

    def test_insert_block_reference_success(self):
        """Test inserting block reference."""
        # Create test block
        create_request = {
            "block_data": {
                "name": "TestBlock",
                "base_point": [10, 20]
            }
        }
        create_response = self.block_service.create_block(create_request)
        block_id = create_response["data"]["block"]["id"]
        
        # Insert block reference
        insert_request = {
            "document_id": "test_doc",
            "block_reference": {
                "block_id": block_id,
                "insertion_point": [100, 200],
                "layer_id": "layer1",
                "scale": [1.5, 1.5],
                "rotation": 45.0
            }
        }
        
        response = self.block_service.insert_block_reference(insert_request)
        
        assert response["success"] is True
        assert "block_reference" in response["data"]
        assert "test_doc" in self.block_service.document_block_refs
        assert len(self.block_service.document_block_refs["test_doc"]) == 1

    def test_insert_block_reference_invalid_block(self):
        """Test inserting reference to non-existent block."""
        insert_request = {
            "document_id": "test_doc",
            "block_reference": {
                "block_id": "nonexistent",
                "insertion_point": [100, 200],
                "layer_id": "layer1"
            }
        }
        
        response = self.block_service.insert_block_reference(insert_request)
        
        assert response["success"] is False
        assert "not found" in response["error_message"]

    def test_get_block_references(self):
        """Test getting block references for document."""
        # Create test block and insert reference
        create_request = {
            "block_data": {
                "name": "TestBlock",
                "base_point": [10, 20]
            }
        }
        create_response = self.block_service.create_block(create_request)
        block_id = create_response["data"]["block"]["id"]
        
        insert_request = {
            "document_id": "test_doc",
            "block_reference": {
                "block_id": block_id,
                "insertion_point": [100, 200],
                "layer_id": "layer1"
            }
        }
        self.block_service.insert_block_reference(insert_request)
        
        # Get block references
        get_request = {"document_id": "test_doc"}
        response = self.block_service.get_block_references(get_request)
        
        assert response["success"] is True
        assert "block_references" in response["data"]
        assert response["data"]["total_count"] == 1
        refs = response["data"]["block_references"]
        assert refs[0]["block_id"] == block_id
        assert refs[0]["block_name"] == "TestBlock"

    def _create_test_blocks(self):
        """Create test blocks for testing."""
        blocks_data = [
            {
                "name": "Door",
                "base_point": [0, 0],
                "category": "Symbols",
                "tags": ["door", "architectural"]
            },
            {
                "name": "Window",
                "base_point": [0, 0],
                "category": "Symbols",
                "tags": ["window", "architectural"]
            },
            {
                "name": "Motor",
                "base_point": [0, 0],
                "category": "Electrical",
                "tags": ["motor", "electrical"]
            }
        ]
        
        for block_data in blocks_data:
            request = {"block_data": block_data}
            self.block_service.create_block(request)