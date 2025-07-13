"""Tests for block model functionality."""

import pytest
from datetime import datetime

from backend.models.block import (
    Block, 
    BlockReference, 
    BlockLibrary, 
    BlockType, 
    AttributeType, 
    AttributeDefinition
)
from backend.core.geometry.point import Point2D
from backend.core.geometry.vector import Vector2D
from backend.models.entity import LineEntity


class TestAttributeDefinition:
    """Test attribute definition functionality."""

    def test_text_attribute_validation(self):
        """Test text attribute validation."""
        attr = AttributeDefinition(
            name="title",
            type=AttributeType.TEXT,
            default_value="Default Title"
        )
        
        assert attr.validate_value("Valid Text")
        assert attr.validate_value("")
        assert not attr.validate_value(123)
        assert not attr.validate_value(None)  # Required by default

    def test_number_attribute_validation(self):
        """Test number attribute validation."""
        attr = AttributeDefinition(
            name="width",
            type=AttributeType.NUMBER,
            default_value=10.0,
            min_value=0.0,
            max_value=100.0
        )
        
        assert attr.validate_value(50.0)
        assert attr.validate_value(0.0)
        assert attr.validate_value(100.0)
        assert not attr.validate_value(-1.0)  # Below min
        assert not attr.validate_value(101.0)  # Above max
        assert not attr.validate_value("text")

    def test_choice_attribute_validation(self):
        """Test choice attribute validation."""
        attr = AttributeDefinition(
            name="size",
            type=AttributeType.CHOICE,
            default_value="Medium",
            choices=["Small", "Medium", "Large"]
        )
        
        assert attr.validate_value("Small")
        assert attr.validate_value("Medium")
        assert attr.validate_value("Large")
        assert not attr.validate_value("Extra Large")
        assert not attr.validate_value(123)

    def test_optional_attribute(self):
        """Test optional attribute validation."""
        attr = AttributeDefinition(
            name="description",
            type=AttributeType.TEXT,
            default_value="",
            required=False
        )
        
        assert attr.validate_value(None)
        assert attr.validate_value("")
        assert attr.validate_value("Some text")


class TestBlock:
    """Test block definition functionality."""

    def test_block_creation(self):
        """Test basic block creation."""
        base_point = Point2D(10, 20)
        block = Block("TestBlock", base_point, BlockType.STATIC)
        
        assert block.name == "TestBlock"
        assert block.base_point == base_point
        assert block.block_type == BlockType.STATIC
        assert block.entities == []
        assert block.attributes == {}
        assert isinstance(block.created_at, datetime)
        assert isinstance(block.modified_at, datetime)

    def test_add_entity(self):
        """Test adding entity to block."""
        block = Block("TestBlock", Point2D(0, 0))
        entity = LineEntity(Point2D(0, 0), Point2D(10, 0), "layer1")
        
        original_start = entity.start_point
        block.add_entity(entity)
        
        assert len(block.entities) == 1
        assert block.entities[0] == entity
        # Entity should be moved relative to base point
        # Note: This depends on the entity implementation

    def test_add_attribute(self):
        """Test adding attribute definition to block."""
        block = Block("TestBlock", Point2D(0, 0))
        
        attr = AttributeDefinition(
            name="width",
            type=AttributeType.NUMBER,
            default_value=10.0
        )
        
        block.add_attribute(attr)
        
        assert "width" in block.attributes
        assert block.attributes["width"] == attr

    def test_remove_attribute(self):
        """Test removing attribute definition."""
        block = Block("TestBlock", Point2D(0, 0))
        
        attr = AttributeDefinition(
            name="width",
            type=AttributeType.NUMBER,
            default_value=10.0
        )
        
        block.add_attribute(attr)
        assert "width" in block.attributes
        
        block.remove_attribute("width")
        assert "width" not in block.attributes

    def test_bounding_box_empty(self):
        """Test bounding box for empty block."""
        block = Block("TestBlock", Point2D(0, 0))
        bbox = block.get_bounding_box()
        
        assert bbox == (0.0, 0.0, 0.0, 0.0)

    def test_block_copy(self):
        """Test block copying."""
        original = Block("TestBlock", Point2D(5, 5))
        original.description = "Test Description"
        original.category = "Test Category"
        original.tags = ["tag1", "tag2"]
        
        # Add an entity
        entity = LineEntity(Point2D(0, 0), Point2D(10, 0), "layer1")
        original.add_entity(entity)
        
        # Add an attribute
        attr = AttributeDefinition("width", AttributeType.NUMBER, 10.0)
        original.add_attribute(attr)
        
        copy = original.copy()
        
        assert copy.name == "TestBlock_copy"
        assert copy.description == original.description
        assert copy.category == original.category
        assert copy.tags == original.tags
        assert len(copy.entities) == len(original.entities)
        assert len(copy.attributes) == len(original.attributes)
        assert copy.id != original.id  # Should have different ID

    def test_block_serialization(self):
        """Test block serialization."""
        block = Block("TestBlock", Point2D(10, 20), BlockType.DYNAMIC)
        block.description = "Test block for serialization"
        block.category = "Test"
        block.tags = ["test", "serialization"]
        
        # Add attribute
        attr = AttributeDefinition("width", AttributeType.NUMBER, 10.0)
        block.add_attribute(attr)
        
        serialized = block.serialize()
        
        assert serialized["name"] == "TestBlock"
        assert serialized["base_point"] == [10, 20]
        assert serialized["block_type"] == "dynamic"
        assert serialized["description"] == "Test block for serialization"
        assert serialized["category"] == "Test"
        assert serialized["tags"] == ["test", "serialization"]
        assert "width" in serialized["attributes"]


class TestBlockReference:
    """Test block reference functionality."""

    def test_block_reference_creation(self):
        """Test basic block reference creation."""
        insertion_point = Point2D(100, 200)
        ref = BlockReference("block123", insertion_point, "layer1")
        
        assert ref.block_id == "block123"
        assert ref.insertion_point == insertion_point
        assert ref.layer_id == "layer1"
        assert ref.scale == Vector2D(1.0, 1.0)
        assert ref.rotation == 0.0
        assert ref.visible
        assert not ref.locked

    def test_set_scale(self):
        """Test setting scale factors."""
        ref = BlockReference("block123", Point2D(0, 0))
        
        # Uniform scale
        ref.set_scale(2.0)
        assert ref.scale == Vector2D(2.0, 2.0)
        
        # Non-uniform scale
        ref.uniform_scale = False
        ref.set_scale(2.0, 3.0)
        assert ref.scale == Vector2D(2.0, 3.0)

    def test_set_rotation(self):
        """Test setting rotation."""
        ref = BlockReference("block123", Point2D(0, 0))
        
        ref.set_rotation(45.0)
        assert ref.rotation == 45.0
        
        # Test angle normalization
        ref.set_rotation(450.0)
        assert ref.rotation == 90.0

    def test_move(self):
        """Test moving block reference."""
        ref = BlockReference("block123", Point2D(10, 20))
        
        ref.move(5, -10)
        assert ref.insertion_point == Point2D(15, 10)

    def test_transform_point(self):
        """Test point transformation."""
        ref = BlockReference("block123", Point2D(10, 10))
        ref.set_scale(2.0)
        ref.set_rotation(90.0)
        
        # Transform point (1, 0) - should become (-2, 2) + (10, 10) = (8, 12)
        transformed = ref.get_transformed_point(Point2D(1, 0))
        
        # Allow for floating point precision
        assert abs(transformed.x - 8.0) < 0.001
        assert abs(transformed.y - 12.0) < 0.001

    def test_attribute_values(self):
        """Test setting and getting attribute values."""
        ref = BlockReference("block123", Point2D(0, 0))
        
        ref.set_attribute_value("width", 50.0)
        ref.set_attribute_value("title", "Test Title")
        
        assert ref.get_attribute_value("width") == 50.0
        assert ref.get_attribute_value("title") == "Test Title"
        assert ref.get_attribute_value("missing") is None
        assert ref.get_attribute_value("missing", "default") == "default"

    def test_block_reference_copy(self):
        """Test block reference copying."""
        original = BlockReference("block123", Point2D(5, 5), "layer1")
        original.set_scale(2.0)
        original.set_rotation(45.0)
        original.set_attribute_value("width", 100.0)
        original.visible = False
        original.locked = True
        
        copy = original.copy()
        
        assert copy.block_id == original.block_id
        assert copy.insertion_point == original.insertion_point
        assert copy.layer_id == original.layer_id
        assert copy.scale == original.scale
        assert copy.rotation == original.rotation
        assert copy.attribute_values == original.attribute_values
        assert copy.visible == original.visible
        assert copy.locked == original.locked
        assert copy.id != original.id  # Should have different ID

    def test_block_reference_serialization(self):
        """Test block reference serialization."""
        ref = BlockReference("block123", Point2D(100, 200), "layer1")
        ref.set_scale(1.5, 2.0)
        ref.set_rotation(30.0)
        ref.set_attribute_value("width", 75.0)
        ref.visible = False
        
        serialized = ref.serialize()
        
        assert serialized["block_id"] == "block123"
        assert serialized["insertion_point"] == [100, 200]
        assert serialized["layer_id"] == "layer1"
        assert serialized["scale"] == [1.5, 2.0]
        assert serialized["rotation"] == 30.0
        assert serialized["attribute_values"]["width"] == 75.0
        assert serialized["visible"] is False


class TestBlockLibrary:
    """Test block library functionality."""

    def test_library_creation(self):
        """Test basic library creation."""
        library = BlockLibrary("TestLibrary", "Test library description")
        
        assert library.name == "TestLibrary"
        assert library.description == "Test library description"
        assert library.blocks == {}
        assert library.categories == {}
        assert isinstance(library.created_at, datetime)

    def test_add_block(self):
        """Test adding block to library."""
        library = BlockLibrary("TestLibrary")
        block = Block("TestBlock", Point2D(0, 0))
        block.category = "Symbols"
        
        library.add_block(block)
        
        assert block.id in library.blocks
        assert library.blocks[block.id] == block
        assert "Symbols" in library.categories
        assert block.id in library.categories["Symbols"]

    def test_remove_block(self):
        """Test removing block from library."""
        library = BlockLibrary("TestLibrary")
        block = Block("TestBlock", Point2D(0, 0))
        block.category = "Symbols"
        
        library.add_block(block)
        assert block.id in library.blocks
        
        library.remove_block(block.id)
        assert block.id not in library.blocks
        assert block.id not in library.categories.get("Symbols", [])

    def test_get_block(self):
        """Test getting block by ID."""
        library = BlockLibrary("TestLibrary")
        block = Block("TestBlock", Point2D(0, 0))
        
        library.add_block(block)
        
        retrieved = library.get_block(block.id)
        assert retrieved == block
        
        missing = library.get_block("nonexistent")
        assert missing is None

    def test_get_blocks_by_category(self):
        """Test getting blocks by category."""
        library = BlockLibrary("TestLibrary")
        
        # Add blocks in different categories
        block1 = Block("Block1", Point2D(0, 0))
        block1.category = "Symbols"
        
        block2 = Block("Block2", Point2D(0, 0))
        block2.category = "Symbols"
        
        block3 = Block("Block3", Point2D(0, 0))
        block3.category = "Mechanical"
        
        library.add_block(block1)
        library.add_block(block2)
        library.add_block(block3)
        
        symbols = library.get_blocks_by_category("Symbols")
        mechanical = library.get_blocks_by_category("Mechanical")
        missing = library.get_blocks_by_category("Missing")
        
        assert len(symbols) == 2
        assert block1 in symbols
        assert block2 in symbols
        assert len(mechanical) == 1
        assert block3 in mechanical
        assert len(missing) == 0

    def test_search_blocks(self):
        """Test searching blocks."""
        library = BlockLibrary("TestLibrary")
        
        # Add blocks with different properties
        block1 = Block("Door", Point2D(0, 0))
        block1.description = "Standard door block"
        block1.tags = ["door", "architectural"]
        
        block2 = Block("Window", Point2D(0, 0))
        block2.description = "Standard window block"
        block2.tags = ["window", "architectural"]
        
        block3 = Block("Motor", Point2D(0, 0))
        block3.description = "Electric motor symbol"
        block3.tags = ["motor", "electrical"]
        
        library.add_block(block1)
        library.add_block(block2)
        library.add_block(block3)
        
        # Search by name
        door_results = library.search_blocks("door")
        assert len(door_results) == 1
        assert block1 in door_results
        
        # Search by description
        standard_results = library.search_blocks("standard")
        assert len(standard_results) == 2
        assert block1 in standard_results
        assert block2 in standard_results
        
        # Search by tag
        architectural_results = library.search_blocks("architectural")
        assert len(architectural_results) == 2
        assert block1 in architectural_results
        assert block2 in architectural_results
        
        # Case insensitive search
        window_results = library.search_blocks("WINDOW")
        assert len(window_results) == 1
        assert block2 in window_results

    def test_library_serialization(self):
        """Test library serialization."""
        library = BlockLibrary("TestLibrary", "Test description")
        library.version = "1.1"
        library.author = "Test Author"
        library.tags = ["test", "library"]
        
        # Add a block
        block = Block("TestBlock", Point2D(0, 0))
        library.add_block(block)
        
        serialized = library.serialize()
        
        assert serialized["name"] == "TestLibrary"
        assert serialized["description"] == "Test description"
        assert serialized["version"] == "1.1"
        assert serialized["author"] == "Test Author"
        assert serialized["tags"] == ["test", "library"]
        assert block.id in serialized["blocks"]
        assert "General" in serialized["categories"]  # Default category