"""Tests for BaseEntity model."""

import pytest
from datetime import datetime
from typing import Dict, Any, Optional

from backend.models.entity import BaseEntity, EntityFilter


class MockEntity(BaseEntity):
    """Mock entity for testing BaseEntity functionality."""
    
    def __init__(self, layer_id: str, x: float = 0, y: float = 0):
        super().__init__(layer_id)
        self.x = x
        self.y = y
    
    @property
    def entity_type(self) -> str:
        return "mock"
    
    def get_bounding_box(self) -> Optional['BoundingBox']:
        # Mock implementation
        return None
    
    def transform(self, matrix: 'TransformMatrix') -> None:
        # Mock implementation
        pass
    
    def copy(self) -> 'BaseEntity':
        copy = MockEntity(self.layer_id, self.x, self.y)
        copy.properties = self.properties.copy()
        return copy
    
    def _serialize_geometry(self) -> Dict[str, Any]:
        return {'x': self.x, 'y': self.y}
    
    @classmethod
    def _create_from_geometry(cls, geometry_data: Dict[str, Any]) -> 'MockEntity':
        return cls("", geometry_data.get('x', 0), geometry_data.get('y', 0))


class TestBaseEntity:
    """Test BaseEntity base class."""
    
    def test_entity_creation(self):
        """Test basic entity creation."""
        entity = MockEntity("layer1")
        assert entity.layer_id == "layer1"
        assert entity.id is not None
        assert len(entity.id) == 36  # UUID length
        assert entity.visible is True
        assert entity.locked is False
        assert isinstance(entity.created_at, datetime)
        assert isinstance(entity.modified_at, datetime)
    
    def test_entity_properties(self):
        """Test entity property management."""
        entity = MockEntity("layer1")
        
        # Update properties
        entity.update_properties(color="red", width=5)
        assert entity.properties["color"] == "red"
        assert entity.properties["width"] == 5
        
        # Modified time should be updated
        old_modified = entity.modified_at
        entity.update_properties(new_prop="value")
        assert entity.modified_at > old_modified
    
    def test_entity_layer_change(self):
        """Test entity layer modification."""
        entity = MockEntity("layer1")
        
        old_modified = entity.modified_at
        entity.set_layer("layer2")
        assert entity.layer_id == "layer2"
        assert entity.modified_at > old_modified
    
    def test_entity_visibility(self):
        """Test entity visibility control."""
        entity = MockEntity("layer1")
        
        old_modified = entity.modified_at
        entity.set_visibility(False)
        assert entity.visible is False
        assert entity.modified_at > old_modified
    
    def test_entity_locking(self):
        """Test entity locking control."""
        entity = MockEntity("layer1")
        
        old_modified = entity.modified_at
        entity.set_locked(True)
        assert entity.locked is True
        assert entity.modified_at > old_modified
    
    def test_entity_serialization(self):
        """Test entity serialization."""
        entity = MockEntity("layer1", 10, 20)
        entity.update_properties(test_prop="value")
        
        data = entity.serialize()
        
        assert data["id"] == entity.id
        assert data["entity_type"] == "mock"
        assert data["layer_id"] == "layer1"
        assert data["properties"]["test_prop"] == "value"
        assert data["geometry"]["x"] == 10
        assert data["geometry"]["y"] == 20
        assert "created_at" in data
        assert "modified_at" in data
    
    def test_entity_deserialization(self):
        """Test entity deserialization."""
        original = MockEntity("layer1", 10, 20)
        original.update_properties(test_prop="value")
        
        # Serialize then deserialize
        data = original.serialize()
        restored = MockEntity.deserialize(data)
        
        assert restored.id == original.id
        assert restored.layer_id == original.layer_id
        assert restored.x == original.x
        assert restored.y == original.y
        assert restored.properties == original.properties
        assert restored.created_at == original.created_at
        assert restored.modified_at == original.modified_at
    
    def test_entity_copy(self):
        """Test entity copying."""
        entity = MockEntity("layer1", 10, 20)
        entity.update_properties(test="value")
        
        copy = entity.copy()
        assert copy.layer_id == entity.layer_id
        assert copy.x == entity.x
        assert copy.y == entity.y
        assert copy.properties == entity.properties
        assert copy.id != entity.id  # Should have new ID
    
    def test_entity_equality(self):
        """Test entity equality and hashing."""
        entity1 = MockEntity("layer1")
        entity2 = MockEntity("layer1")
        
        assert entity1 != entity2  # Different IDs
        assert entity1 == entity1  # Same instance
        
        # Test in set
        entity_set = {entity1, entity2}
        assert len(entity_set) == 2
    
    def test_entity_repr(self):
        """Test entity string representation."""
        entity = MockEntity("layer1")
        repr_str = repr(entity)
        assert "MockEntity" in repr_str
        assert entity.id[:8] in repr_str
        assert "layer1" in repr_str


class TestEntityFilter:
    """Test EntityFilter functionality."""
    
    def test_filter_creation(self):
        """Test filter creation."""
        filter_obj = EntityFilter(
            entity_types=["line", "circle"],
            layer_ids=["layer1", "layer2"],
            visible_only=True
        )
        assert filter_obj.entity_types == ["line", "circle"]
        assert filter_obj.layer_ids == ["layer1", "layer2"]
        assert filter_obj.visible_only is True
    
    def test_entity_filter_matching(self):
        """Test entity filter matching."""
        entity = MockEntity("layer1")
        entity.update_properties(type="test", value=42)
        
        # Test entity type filter
        filter_obj = EntityFilter(entity_types=["mock"])
        assert entity.matches_filter(filter_obj)
        
        filter_obj = EntityFilter(entity_types=["line"])
        assert not entity.matches_filter(filter_obj)
        
        # Test layer filter
        filter_obj = EntityFilter(layer_ids=["layer1"])
        assert entity.matches_filter(filter_obj)
        
        filter_obj = EntityFilter(layer_ids=["layer2"])
        assert not entity.matches_filter(filter_obj)
        
        # Test visibility filter
        filter_obj = EntityFilter(visible_only=True)
        assert entity.matches_filter(filter_obj)
        
        entity.set_visibility(False)
        assert not entity.matches_filter(filter_obj)
        
        # Test locked filter
        filter_obj = EntityFilter(locked_only=False)
        assert entity.matches_filter(filter_obj)
        
        entity.set_locked(True)
        filter_obj = EntityFilter(locked_only=True)
        assert entity.matches_filter(filter_obj)
        
        # Test properties filter
        filter_obj = EntityFilter(properties={"type": "test"})
        assert entity.matches_filter(filter_obj)
        
        filter_obj = EntityFilter(properties={"type": "wrong"})
        assert not entity.matches_filter(filter_obj)
        
        filter_obj = EntityFilter(properties={"missing": "value"})
        assert not entity.matches_filter(filter_obj)
    
    def test_combined_filters(self):
        """Test multiple filter criteria combined."""
        entity = MockEntity("layer1")
        entity.update_properties(category="geometry")
        
        filter_obj = EntityFilter(
            entity_types=["mock"],
            layer_ids=["layer1"],
            visible_only=True,
            properties={"category": "geometry"}
        )
        
        assert entity.matches_filter(filter_obj)
        
        # Change one property and test failure
        entity.set_layer("layer2")
        assert not entity.matches_filter(filter_obj)