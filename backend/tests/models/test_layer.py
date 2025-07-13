"""Tests for Layer model."""

from datetime import datetime

import pytest

from backend.models.layer import Color, Layer, LineType


class TestColor:
    """Test Color class."""

    def test_color_creation(self):
        """Test color creation with RGB values."""
        color = Color(255, 128, 64)
        assert color.red == 255
        assert color.green == 128
        assert color.blue == 64
        assert color.alpha == 255

    def test_color_with_alpha(self):
        """Test color creation with alpha."""
        color = Color(255, 128, 64, 128)
        assert color.alpha == 128

    def test_color_validation(self):
        """Test color validation."""
        with pytest.raises(ValueError):
            Color(256, 0, 0)  # Red too high

        with pytest.raises(ValueError):
            Color(-1, 0, 0)  # Red too low

    def test_from_hex(self):
        """Test color creation from hex string."""
        color = Color.from_hex("#FF8040")
        assert color.red == 255
        assert color.green == 128
        assert color.blue == 64
        assert color.alpha == 255

        # Test with alpha
        color = Color.from_hex("#FF804080")
        assert color.alpha == 128

    def test_to_hex(self):
        """Test color conversion to hex."""
        color = Color(255, 128, 64)
        assert color.to_hex() == "#ff8040"
        assert color.to_hex(include_alpha=True) == "#ff8040ff"

    def test_to_tuple(self):
        """Test color conversion to tuple."""
        color = Color(255, 128, 64, 200)
        assert color.to_tuple() == (255, 128, 64, 200)
        assert color.rgb == (255, 128, 64)


class TestLayer:
    """Test Layer class."""

    def test_layer_creation(self):
        """Test basic layer creation."""
        layer = Layer("Test Layer")
        assert layer.name == "Test Layer"
        assert layer.color == Layer.BLACK
        assert layer.line_type == LineType.CONTINUOUS
        assert layer.line_weight == 0.25
        assert layer.visible is True
        assert layer.locked is False
        assert layer.id is not None

    def test_layer_with_properties(self):
        """Test layer creation with custom properties."""
        color = Color(255, 0, 0)
        layer = Layer("Red Layer", color, LineType.DASHED, 0.5)
        assert layer.color == color
        assert layer.line_type == LineType.DASHED
        assert layer.line_weight == 0.5

    def test_layer_validation(self):
        """Test layer validation."""
        with pytest.raises(ValueError):
            Layer("")  # Empty name

        with pytest.raises(ValueError):
            Layer("Test", line_weight=-1)  # Negative weight

    def test_layer_properties(self):
        """Test layer property modifications."""
        layer = Layer("Test")

        # Test color change
        new_color = Color(255, 0, 0)
        layer.set_color(new_color)
        assert layer.color == new_color

        # Test line type change
        layer.set_line_type(LineType.DASHED)
        assert layer.line_type == LineType.DASHED

        # Test line weight change
        layer.set_line_weight(1.0)
        assert layer.line_weight == 1.0

        with pytest.raises(ValueError):
            layer.set_line_weight(-1)

    def test_layer_states(self):
        """Test layer state changes."""
        layer = Layer("Test")

        layer.set_visible(False)
        assert layer.visible is False

        layer.set_locked(True)
        assert layer.locked is True

        layer.set_printable(False)
        assert layer.printable is False

        layer.set_frozen(True)
        assert layer.frozen is True

        assert not layer.is_editable()  # Locked and frozen

    def test_layer_rename(self):
        """Test layer renaming."""
        layer = Layer("Original")
        layer.rename("New Name")
        assert layer.name == "New Name"

        with pytest.raises(ValueError):
            layer.rename("")

    def test_layer_description(self):
        """Test layer description."""
        layer = Layer("Test")
        layer.set_description("Test description")
        assert layer.description == "Test description"

    def test_layer_properties_update(self):
        """Test custom properties update."""
        layer = Layer("Test")
        layer.update_properties(custom_prop="value", number=42)
        assert layer.properties["custom_prop"] == "value"
        assert layer.properties["number"] == 42

    def test_layer_serialization(self):
        """Test layer serialization and deserialization."""
        original = Layer("Test Layer", Color(255, 0, 0), LineType.DASHED, 0.5)
        original.set_description("Test description")
        original.update_properties(custom="value")

        # Serialize
        data = original.serialize()

        # Deserialize
        restored = Layer.deserialize(data)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.color == original.color
        assert restored.line_type == original.line_type
        assert restored.line_weight == original.line_weight
        assert restored.description == original.description
        assert restored.properties == original.properties

    def test_layer_copy(self):
        """Test layer copying."""
        original = Layer("Original", Color(255, 0, 0), LineType.DASHED)
        original.set_description("Original description")

        # Copy with new name
        copy = original.copy("Copy")
        assert copy.name == "Copy"
        assert copy.id != original.id
        assert copy.color == original.color
        assert copy.line_type == original.line_type
        assert copy.description == original.description

        # Copy with default name
        copy2 = original.copy()
        assert copy2.name == "Original_copy"

    def test_layer_equality(self):
        """Test layer equality and hashing."""
        layer1 = Layer("Test")
        layer2 = Layer("Test")

        assert layer1 != layer2  # Different IDs
        assert layer1 == layer1  # Same instance

        # Test in set
        layer_set = {layer1, layer2}
        assert len(layer_set) == 2

    def test_layer_repr(self):
        """Test layer string representation."""
        layer = Layer("Test Layer", Color(255, 0, 0))
        repr_str = repr(layer)
        assert "Test Layer" in repr_str
        assert "#ff0000" in repr_str
        assert "visible=True" in repr_str
