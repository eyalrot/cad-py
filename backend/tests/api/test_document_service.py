"""Tests for DocumentService."""

import pytest
import tempfile
from pathlib import Path

from backend.api.document_service import DocumentService


class TestDocumentService:
    """Test DocumentService class."""
    
    def setup_method(self):
        """Setup test method."""
        self.service = DocumentService()
    
    def test_create_document(self):
        """Test document creation."""
        request = {
            "name": "Test Document",
            "description": "Test description",
            "metadata": {"author": "Test Author"}
        }
        
        response = self.service.create_document(request)
        
        assert response["success"] is True
        assert response["error_message"] == ""
        assert "document" in response
        
        doc = response["document"]
        assert doc["name"] == "Test Document"
        assert doc["description"] == "Test description"
        assert doc["metadata"]["author"] == "Test Author"
        assert doc["layer_count"] == 1  # Default layer
        assert doc["entity_count"] == 0
    
    def test_create_document_without_name(self):
        """Test document creation without name."""
        request = {}
        
        response = self.service.create_document(request)
        
        assert response["success"] is False
        assert "name is required" in response["error_message"]
    
    def test_open_document(self):
        """Test opening a document."""
        # First create a document
        create_request = {"name": "Test Document"}
        create_response = self.service.create_document(create_request)
        document_id = create_response["document"]["id"]
        
        # Then open it
        open_request = {"document_id": document_id}
        response = self.service.open_document(open_request)
        
        assert response["found"] is True
        assert response["error_message"] == ""
        assert response["document"]["id"] == document_id
    
    def test_open_nonexistent_document(self):
        """Test opening a non-existent document."""
        request = {"document_id": "nonexistent"}
        
        response = self.service.open_document(request)
        
        assert response["found"] is False
        assert "not found" in response["error_message"]
    
    def test_save_document(self):
        """Test saving a document."""
        # Create a document
        create_request = {"name": "Save Test"}
        create_response = self.service.create_document(create_request)
        document_id = create_response["document"]["id"]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_document.json"
            
            save_request = {
                "document_id": document_id,
                "file_path": str(file_path),
                "format": "json"
            }
            
            response = self.service.save_document(save_request)
            
            assert response["success"] is True
            assert response["file_path"] == str(file_path)
            assert file_path.exists()
    
    def test_save_nonexistent_document(self):
        """Test saving a non-existent document."""
        request = {
            "document_id": "nonexistent",
            "file_path": "test.json"
        }
        
        response = self.service.save_document(request)
        
        assert response["success"] is False
        assert "not found" in response["error_message"]
    
    def test_load_document(self):
        """Test loading a document."""
        # Create and save a document first
        create_request = {"name": "Load Test", "description": "Load test doc"}
        create_response = self.service.create_document(create_request)
        document_id = create_response["document"]["id"]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "load_test.json"
            
            # Save document
            save_request = {
                "document_id": document_id,
                "file_path": str(file_path)
            }
            self.service.save_document(save_request)
            
            # Clear documents and load
            self.service._documents.clear()
            
            load_request = {"file_path": str(file_path)}
            response = self.service.load_document(load_request)
            
            assert response["success"] is True
            assert response["document"]["name"] == "Load Test"
            assert response["document"]["description"] == "Load test doc"
    
    def test_load_nonexistent_file(self):
        """Test loading from non-existent file."""
        request = {"file_path": "nonexistent.json"}
        
        response = self.service.load_document(request)
        
        assert response["success"] is False
        assert "not found" in response["error_message"]
    
    def test_update_document(self):
        """Test updating document properties."""
        # Create a document
        create_request = {"name": "Original Name"}
        create_response = self.service.create_document(create_request)
        document_id = create_response["document"]["id"]
        
        # Update document
        update_request = {
            "document_id": document_id,
            "name": "Updated Name",
            "description": "Updated description",
            "metadata": {"version": "2.0"}
        }
        
        response = self.service.update_document(update_request)
        
        assert response["success"] is True
        doc = response["document"]
        assert doc["name"] == "Updated Name"
        assert doc["description"] == "Updated description"
        assert doc["metadata"]["version"] == "2.0"
    
    def test_update_nonexistent_document(self):
        """Test updating a non-existent document."""
        request = {
            "document_id": "nonexistent",
            "name": "New Name"
        }
        
        response = self.service.update_document(request)
        
        assert response["success"] is False
        assert "not found" in response["error_message"]
    
    def test_delete_document(self):
        """Test deleting a document."""
        # Create a document
        create_request = {"name": "Delete Test"}
        create_response = self.service.create_document(create_request)
        document_id = create_response["document"]["id"]
        
        # Delete document
        delete_request = {"document_id": document_id}
        response = self.service.delete_document(delete_request)
        
        assert response["success"] is True
        
        # Verify document is gone
        assert document_id not in self.service._documents
    
    def test_delete_nonexistent_document(self):
        """Test deleting a non-existent document."""
        request = {"document_id": "nonexistent"}
        
        response = self.service.delete_document(request)
        
        assert response["success"] is False
        assert "not found" in response["error_message"]
    
    def test_get_document_statistics(self):
        """Test getting document statistics."""
        # Create a document
        create_request = {"name": "Stats Test"}
        create_response = self.service.create_document(create_request)
        document_id = create_response["document"]["id"]
        
        # Get statistics
        stats_request = {"document_id": document_id}
        response = self.service.get_document_statistics(stats_request)
        
        assert response["success"] is True
        stats = response["statistics"]
        assert stats["name"] == "Stats Test"
        assert stats["layer_count"] == 1
        assert stats["entity_count"] == 0
    
    def test_list_documents(self):
        """Test listing documents."""
        # Create multiple documents
        for i in range(3):
            request = {"name": f"Document {i}"}
            self.service.create_document(request)
        
        # List all documents
        response = self.service.list_documents({})
        
        assert response["success"] is True
        assert len(response["documents"]) == 3
        assert response["total_count"] == 3
    
    def test_list_documents_with_pagination(self):
        """Test listing documents with pagination."""
        # Create multiple documents
        for i in range(5):
            request = {"name": f"Document {i}"}
            self.service.create_document(request)
        
        # List with pagination
        request = {"limit": 2, "offset": 1}
        response = self.service.list_documents(request)
        
        assert response["success"] is True
        assert len(response["documents"]) == 2
        assert response["total_count"] == 5