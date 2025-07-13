"""Tests for serialization utilities."""

import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from backend.models.document import CADDocument
from backend.models.entity import BaseEntity
from backend.models.layer import Color, Layer, LineType
from backend.models.serialization import CompactSerializer, DocumentSerializer


class MockEntity(BaseEntity):
    """Mock entity for serialization testing."""

    def __init__(self, layer_id: str, value: int = 0):
        super().__init__(layer_id)
        self.value = value

    @property
    def entity_type(self) -> str:
        return "mock"

    def get_bounding_box(self) -> Optional["BoundingBox"]:
        return None

    def transform(self, matrix: "TransformMatrix") -> None:
        pass

    def copy(self) -> "BaseEntity":
        copy = MockEntity(self.layer_id, self.value)
        copy.properties = self.properties.copy()
        return copy

    def _serialize_geometry(self) -> Dict[str, Any]:
        return {"value": self.value}

    @classmethod
    def _create_from_geometry(cls, geometry_data: Dict[str, Any]) -> "MockEntity":
        return cls("", geometry_data.get("value", 0))


class TestDocumentSerializer:
    """Test DocumentSerializer class."""

    def test_json_serialization(self):
        """Test JSON serialization and deserialization."""
        # Create test document
        doc = CADDocument("JSON Test")
        doc.set_description("Test document for JSON serialization")
        doc.update_metadata(author="Test Author", version=2)

        # Add layer
        layer = Layer("Test Layer", Color(255, 0, 0), LineType.DASHED)
        layer_id = doc.add_layer(layer)

        # Add entity
        entity = MockEntity(layer_id, 42)
        entity.update_properties(name="test_entity", active=True)
        doc.add_entity(entity)

        # Serialize to JSON string
        json_str = DocumentSerializer.to_json(doc)
        assert isinstance(json_str, str)

        # Verify it's valid JSON
        data = json.loads(json_str)
        assert data["name"] == "JSON Test"
        assert data["description"] == "Test document for JSON serialization"
        assert data["metadata"]["author"] == "Test Author"

        # Deserialize from JSON string
        restored_doc = DocumentSerializer.from_json(json_str)
        assert restored_doc.name == doc.name
        assert restored_doc.description == doc.description
        assert restored_doc.metadata == doc.metadata
        assert len(restored_doc.list_layers()) == len(doc.list_layers())

    def test_json_formatting(self):
        """Test JSON formatting options."""
        doc = CADDocument("Format Test")

        # Test with different indentation
        json_str_compact = DocumentSerializer.to_json(doc, indent=0)
        json_str_formatted = DocumentSerializer.to_json(doc, indent=4)

        # Formatted version should be longer
        assert len(json_str_formatted) > len(json_str_compact)

        # Both should be valid JSON
        data_compact = json.loads(json_str_compact)
        data_formatted = json.loads(json_str_formatted)
        assert data_compact == data_formatted

    def test_binary_serialization(self):
        """Test binary serialization and deserialization."""
        # Create test document
        doc = CADDocument("Binary Test")
        doc.update_metadata(test_data=[1, 2, 3, 4, 5])

        # Add layer
        layer = Layer("Binary Layer", Color(128, 64, 192))
        layer_id = doc.add_layer(layer)

        # Add entity
        entity = MockEntity(layer_id, 100)
        doc.add_entity(entity)

        # Serialize to binary
        binary_data = DocumentSerializer.to_binary(doc)
        assert isinstance(binary_data, bytes)

        # Deserialize from binary
        restored_doc = DocumentSerializer.from_binary(binary_data)
        assert restored_doc.name == doc.name
        assert restored_doc.metadata == doc.metadata
        assert len(restored_doc.list_layers()) == len(doc.list_layers())

    def test_json_file_operations(self):
        """Test JSON file save and load operations."""
        doc = CADDocument("File Test")
        doc.set_description("File operation test")

        # Add test data
        layer = Layer("File Layer", Color(200, 100, 50))
        layer_id = doc.add_layer(layer)
        entity = MockEntity(layer_id, 999)
        doc.add_entity(entity)

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_document.json"

            # Save to JSON file
            DocumentSerializer.save_json(doc, file_path)
            assert file_path.exists()

            # Verify file content is valid JSON
            with open(file_path, "r") as f:
                data = json.load(f)
            assert data["name"] == "File Test"

            # Load from JSON file
            loaded_doc = DocumentSerializer.load_json(file_path)
            assert loaded_doc.name == doc.name
            assert loaded_doc.description == doc.description
            assert len(loaded_doc.list_layers()) == len(doc.list_layers())

    def test_binary_file_operations(self):
        """Test binary file save and load operations."""
        doc = CADDocument("Binary File Test")
        doc.update_metadata(binary_test=True, numbers=[1, 2, 3])

        # Add test data
        layer = Layer("Binary File Layer")
        layer_id = doc.add_layer(layer)
        entity = MockEntity(layer_id, 777)
        doc.add_entity(entity)

        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "test_document.bin"

            # Save to binary file
            DocumentSerializer.save_binary(doc, file_path)
            assert file_path.exists()

            # Load from binary file
            loaded_doc = DocumentSerializer.load_binary(file_path)
            assert loaded_doc.name == doc.name
            assert loaded_doc.metadata == doc.metadata
            assert len(loaded_doc.list_layers()) == len(doc.list_layers())

    def test_file_error_handling(self):
        """Test error handling in file operations."""
        doc = CADDocument("Error Test")

        # Test loading non-existent file
        with pytest.raises(FileNotFoundError):
            DocumentSerializer.load_json("nonexistent.json")

        with pytest.raises(FileNotFoundError):
            DocumentSerializer.load_binary("nonexistent.bin")

        # Test loading invalid JSON
        with tempfile.TemporaryDirectory() as temp_dir:
            invalid_file = Path(temp_dir) / "invalid.json"
            invalid_file.write_text("invalid json content")

            with pytest.raises(json.JSONDecodeError):
                DocumentSerializer.load_json(invalid_file)


class TestCompactSerializer:
    """Test CompactSerializer class."""

    def test_entities_only_serialization(self):
        """Test serializing only entity data."""
        doc = CADDocument("Entities Test")
        default_layer_id = doc.list_layers()[0].id

        # Add entities
        entity1 = MockEntity(default_layer_id, 10)
        entity2 = MockEntity(default_layer_id, 20)
        doc.add_entity(entity1)
        doc.add_entity(entity2)

        # Serialize entities only
        entities_data = CompactSerializer.serialize_entities_only(doc)

        assert "entities" in entities_data
        assert "entity_count" in entities_data
        assert entities_data["entity_count"] == 2
        assert len(entities_data["entities"]) == 2

        # Should not contain layer or document data
        assert "layers" not in entities_data
        assert "name" not in entities_data

    def test_layers_only_serialization(self):
        """Test serializing only layer data."""
        doc = CADDocument("Layers Test")

        # Add layers
        layer1 = Layer("Layer 1", Color(255, 0, 0))
        layer2 = Layer("Layer 2", Color(0, 255, 0))
        doc.add_layer(layer1)
        doc.add_layer(layer2)

        # Serialize layers only
        layers_data = CompactSerializer.serialize_layers_only(doc)

        assert "layers" in layers_data
        assert "current_layer_id" in layers_data
        assert "layer_count" in layers_data
        assert layers_data["layer_count"] == 3  # Default + 2 added
        assert len(layers_data["layers"]) == 3

        # Should not contain entity or full document data
        assert "entities" not in layers_data
        assert "description" not in layers_data

    def test_metadata_only_serialization(self):
        """Test serializing only metadata."""
        doc = CADDocument("Metadata Test")
        doc.set_description("Test description")
        doc.update_metadata(author="Test Author", version=2, tags=["test", "metadata"])

        # Add some entities and layers for statistics
        layer = Layer("Stats Layer")
        layer_id = doc.add_layer(layer)
        entity = MockEntity(layer_id, 50)
        doc.add_entity(entity)

        # Serialize metadata only
        metadata = CompactSerializer.serialize_metadata_only(doc)

        assert "id" in metadata
        assert "name" in metadata
        assert "version" in metadata
        assert "description" in metadata
        assert "metadata" in metadata
        assert "statistics" in metadata
        assert metadata["name"] == "Metadata Test"
        assert metadata["description"] == "Test description"
        assert metadata["metadata"]["author"] == "Test Author"
        assert metadata["statistics"]["entity_count"] == 1
        assert metadata["statistics"]["layer_count"] == 2

        # Should not contain full entity or layer data
        assert "entities" not in metadata
        assert "layers" not in metadata

    def test_compact_serialization_performance(self):
        """Test that compact serialization is more efficient."""
        doc = CADDocument("Performance Test")
        default_layer_id = doc.list_layers()[0].id

        # Add many entities
        for i in range(100):
            entity = MockEntity(default_layer_id, i)
            entity.update_properties(index=i, name=f"entity_{i}")
            doc.add_entity(entity)

        # Full serialization
        full_data = doc.serialize()

        # Compact serializations
        entities_only = CompactSerializer.serialize_entities_only(doc)
        layers_only = CompactSerializer.serialize_layers_only(doc)
        metadata_only = CompactSerializer.serialize_metadata_only(doc)

        # Convert to JSON strings for size comparison
        full_json = json.dumps(full_data)
        entities_json = json.dumps(entities_only)
        layers_json = json.dumps(layers_only)
        metadata_json = json.dumps(metadata_only)

        # Compact versions should be smaller than full
        assert len(entities_json) < len(full_json)
        assert len(layers_json) < len(full_json)
        assert len(metadata_json) < len(full_json)

        # Metadata should be smallest
        assert len(metadata_json) < len(entities_json)
        assert len(metadata_json) < len(layers_json)
