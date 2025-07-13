"""Tests for CADDocument model."""

import pytest
import tempfile
import json
from pathlib import Path
from typing import Dict, Any, Optional

from backend.models.document import CADDocument
from backend.models.layer import Layer, Color, LineType
from backend.models.entity import BaseEntity, EntityFilter


class MockEntity(BaseEntity):
    """Mock entity for document testing."""
    
    def __init__(self, layer_id: str, name: str = "test"):
        super().__init__(layer_id)
        self.name = name
    
    @property
    def entity_type(self) -> str:
        return "mock"
    
    def get_bounding_box(self) -> Optional['BoundingBox']:
        return None
    
    def transform(self, matrix: 'TransformMatrix') -> None:
        pass
    
    def copy(self) -> 'BaseEntity':
        copy = MockEntity(self.layer_id, self.name)
        copy.properties = self.properties.copy()
        return copy
    
    def _serialize_geometry(self) -> Dict[str, Any]:
        return {'name': self.name}
    
    @classmethod
    def _create_from_geometry(cls, geometry_data: Dict[str, Any]) -> 'MockEntity':
        return cls("", geometry_data.get('name', 'test'))


class TestCADDocument:
    """Test CADDocument class."""
    
    def test_document_creation(self):
        """Test document creation."""
        doc = CADDocument("Test Document")
        assert doc.name == "Test Document"
        assert doc.id is not None
        assert len(doc.id) == 36  # UUID length
        assert doc.version == "1.0"
        assert len(doc.list_layers()) == 1  # Default layer
        assert doc.list_layers()[0].name == "0"
        assert doc.count_entities() == 0
    
    def test_document_validation(self):
        """Test document validation."""
        with pytest.raises(ValueError):
            CADDocument("")  # Empty name
        
        with pytest.raises(ValueError):
            CADDocument(None)  # None name
    
    def test_document_properties(self):
        """Test document property management."""
        doc = CADDocument("Test")
        
        # Set description
        doc.set_description("Test description")
        assert doc.description == "Test description"
        
        # Update metadata
        doc.update_metadata(author="Test Author", version=2)
        assert doc.metadata["author"] == "Test Author"
        assert doc.metadata["version"] == 2
        
        # Rename document
        doc.set_name("New Name")
        assert doc.name == "New Name"
        
        with pytest.raises(ValueError):
            doc.set_name("")
    
    def test_layer_management(self):
        """Test layer management operations."""
        doc = CADDocument("Test")
        
        # Add layer
        layer = Layer("Test Layer", Color(255, 0, 0), LineType.DASHED)
        layer_id = doc.add_layer(layer)
        assert layer_id == layer.id
        assert len(doc.list_layers()) == 2
        
        # Get layer
        retrieved = doc.get_layer(layer_id)
        assert retrieved == layer
        
        # Get layer by name
        retrieved_by_name = doc.get_layer_by_name("Test Layer")
        assert retrieved_by_name == layer
        
        # Test duplicate name
        duplicate_layer = Layer("Test Layer")
        with pytest.raises(ValueError):
            doc.add_layer(duplicate_layer)
        
        # Rename layer
        success = doc.rename_layer(layer_id, "Renamed Layer")
        assert success is True
        assert layer.name == "Renamed Layer"
        
        # Test rename to existing name
        with pytest.raises(ValueError):
            doc.rename_layer(layer_id, "0")  # Default layer name
        
        # Set current layer
        doc.set_current_layer(layer_id)
        assert doc.current_layer_id == layer_id
        assert doc.current_layer == layer
        
        with pytest.raises(ValueError):
            doc.set_current_layer("nonexistent")
    
    def test_layer_removal(self):
        """Test layer removal."""
        doc = CADDocument("Test")
        
        # Add layer
        layer = Layer("Removable")
        layer_id = doc.add_layer(layer)
        
        # Remove empty layer
        success = doc.remove_layer(layer_id)
        assert success is True
        assert len(doc.list_layers()) == 1
        
        # Try to remove non-existent layer
        success = doc.remove_layer("nonexistent")
        assert success is False
        
        # Try to remove last layer
        default_layer_id = doc.list_layers()[0].id
        with pytest.raises(ValueError):
            doc.remove_layer(default_layer_id)
        
        # Test removing layer with entities
        layer2 = Layer("With Entities")
        layer2_id = doc.add_layer(layer2)
        entity = MockEntity(layer2_id)
        doc.add_entity(entity)
        
        with pytest.raises(ValueError):
            doc.remove_layer(layer2_id)
    
    def test_entity_management(self):
        """Test entity management operations."""
        doc = CADDocument("Test")
        default_layer_id = doc.list_layers()[0].id
        
        # Add entity
        entity = MockEntity(default_layer_id, "test_entity")
        entity_id = doc.add_entity(entity)
        assert entity_id == entity.id
        assert doc.count_entities() == 1
        
        # Get entity
        retrieved = doc.get_entity(entity_id)
        assert retrieved == entity
        
        # Test adding entity with invalid layer
        invalid_entity = MockEntity("nonexistent_layer")
        with pytest.raises(ValueError):
            doc.add_entity(invalid_entity)
        
        # Remove entity
        success = doc.remove_entity(entity_id)
        assert success is True
        assert doc.count_entities() == 0
        
        # Try to remove non-existent entity
        success = doc.remove_entity("nonexistent")
        assert success is False
    
    def test_entity_queries(self):
        """Test entity query operations."""
        doc = CADDocument("Test")
        default_layer_id = doc.list_layers()[0].id
        
        # Add test layer
        test_layer = Layer("Test Layer")
        test_layer_id = doc.add_layer(test_layer)
        
        # Add entities
        entity1 = MockEntity(default_layer_id, "entity1")
        entity1.update_properties(type="circle")
        doc.add_entity(entity1)
        
        entity2 = MockEntity(test_layer_id, "entity2")
        entity2.update_properties(type="line")
        doc.add_entity(entity2)
        
        entity3 = MockEntity(default_layer_id, "entity3")
        entity3.update_properties(type="circle")
        entity3.set_visibility(False)
        doc.add_entity(entity3)
        
        # Query all entities
        all_entities = doc.query_entities()
        assert len(all_entities) == 3
        
        # Query by layer
        filter_obj = EntityFilter(layer_ids=[default_layer_id])
        layer_entities = doc.query_entities(filter_obj)
        assert len(layer_entities) == 2
        
        # Query by entity type
        filter_obj = EntityFilter(entity_types=["mock"])
        type_entities = doc.query_entities(filter_obj)
        assert len(type_entities) == 3
        
        # Query visible only
        filter_obj = EntityFilter(visible_only=True)
        visible_entities = doc.query_entities(filter_obj)
        assert len(visible_entities) == 2
        
        # Query by properties
        filter_obj = EntityFilter(properties={"type": "circle"})
        circle_entities = doc.query_entities(filter_obj)
        assert len(circle_entities) == 2  # Includes hidden one
        
        # Combined filter
        filter_obj = EntityFilter(
            layer_ids=[default_layer_id],
            visible_only=True,
            properties={"type": "circle"}
        )
        filtered_entities = doc.query_entities(filter_obj)
        assert len(filtered_entities) == 1
        assert filtered_entities[0] == entity1
    
    def test_entity_layer_operations(self):
        """Test moving entities between layers."""
        doc = CADDocument("Test")
        default_layer_id = doc.list_layers()[0].id
        
        # Add test layer
        test_layer = Layer("Test Layer")
        test_layer_id = doc.add_layer(test_layer)
        
        # Add entities
        entity1 = MockEntity(default_layer_id)
        entity2 = MockEntity(default_layer_id)
        doc.add_entity(entity1)
        doc.add_entity(entity2)
        
        # Move entities to new layer
        moved_count = doc.move_entities_to_layer([entity1.id, entity2.id], test_layer_id)
        assert moved_count == 2
        assert entity1.layer_id == test_layer_id
        assert entity2.layer_id == test_layer_id
        
        # Test moving to non-existent layer
        with pytest.raises(ValueError):
            doc.move_entities_to_layer([entity1.id], "nonexistent")
        
        # Test moving non-existent entities
        moved_count = doc.move_entities_to_layer(["nonexistent"], test_layer_id)
        assert moved_count == 0
    
    def test_entity_counts(self):
        """Test entity counting functions."""
        doc = CADDocument("Test")
        default_layer_id = doc.list_layers()[0].id
        
        # Add test layer
        test_layer = Layer("Test Layer")
        test_layer_id = doc.add_layer(test_layer)
        
        # Add entities
        entity1 = MockEntity(default_layer_id)
        entity2 = MockEntity(default_layer_id)
        entity3 = MockEntity(test_layer_id)
        doc.add_entity(entity1)
        doc.add_entity(entity2)
        doc.add_entity(entity3)
        
        # Test counts
        assert doc.count_entities() == 3
        assert doc.count_entities_by_layer(default_layer_id) == 2
        assert doc.count_entities_by_layer(test_layer_id) == 1
    
    def test_document_serialization(self):
        """Test document serialization."""
        doc = CADDocument("Test Document")
        doc.set_description("Test description")
        doc.update_metadata(author="Test Author")
        
        # Add layer and entity
        layer = Layer("Test Layer", Color(255, 0, 0))
        layer_id = doc.add_layer(layer)
        
        entity = MockEntity(layer_id, "test_entity")
        entity.update_properties(test_prop="value")
        doc.add_entity(entity)
        
        # Serialize
        data = doc.serialize()
        
        assert data["name"] == "Test Document"
        assert data["description"] == "Test description"
        assert data["metadata"]["author"] == "Test Author"
        assert len(data["layers"]) == 2  # Default + test layer
        assert len(data["entities"]) == 1
        assert data["current_layer_id"] == doc.current_layer_id
    
    def test_document_file_operations(self):
        """Test document file save/load operations."""
        doc = CADDocument("File Test")
        doc.set_description("File test document")
        
        # Add test data
        layer = Layer("File Layer")
        layer_id = doc.add_layer(layer)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_doc.json"
            
            # Save to file
            doc.save_to_file(file_path)
            assert file_path.exists()
            
            # Load from file
            loaded_doc = CADDocument.load_from_file(file_path)
            assert loaded_doc.name == doc.name
            assert loaded_doc.description == doc.description
            assert len(loaded_doc.list_layers()) == len(doc.list_layers())
    
    def test_document_statistics(self):
        """Test document statistics."""
        doc = CADDocument("Stats Test")
        default_layer_id = doc.list_layers()[0].id
        
        # Add layer and entities
        test_layer = Layer("Test Layer")
        test_layer_id = doc.add_layer(test_layer)
        
        entity1 = MockEntity(default_layer_id)
        entity2 = MockEntity(test_layer_id)
        doc.add_entity(entity1)
        doc.add_entity(entity2)
        
        stats = doc.get_statistics()
        assert stats["name"] == "Stats Test"
        assert stats["layer_count"] == 2
        assert stats["entity_count"] == 2
        assert stats["entities_by_layer"]["0"] == 1
        assert stats["entities_by_layer"]["Test Layer"] == 1
    
    def test_document_repr(self):
        """Test document string representation."""
        doc = CADDocument("Test Document")
        layer = Layer("Test Layer")
        doc.add_layer(layer)
        
        entity = MockEntity(doc.current_layer_id)
        doc.add_entity(entity)
        
        repr_str = repr(doc)
        assert "Test Document" in repr_str
        assert "layers=2" in repr_str
        assert "entities=1" in repr_str