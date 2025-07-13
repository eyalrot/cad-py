"""Tests for DrawingService."""

import pytest

from backend.api.document_service import DocumentService
from backend.api.drawing_service import DrawingService
from backend.api.entity_service import EntityService


class TestDrawingService:
    """Test DrawingService class."""

    def setup_method(self):
        """Setup test method."""
        self.document_service = DocumentService()
        self.entity_service = EntityService(self.document_service)
        self.drawing_service = DrawingService(
            self.document_service, self.entity_service
        )

        # Create a test document
        doc_request = {"name": "Drawing Test"}
        doc_response = self.document_service.create_document(doc_request)
        self.document_id = doc_response["document"]["id"]

    def test_draw_line(self):
        """Test drawing a line."""
        request = {
            "document_id": self.document_id,
            "start": {"x": 0.0, "y": 0.0},
            "end": {"x": 10.0, "y": 10.0},
            "properties": {"color": "red", "width": "2"},
        }

        response = self.drawing_service.draw_line(request)

        assert response["success"] is True
        entity = response["entity"]
        assert entity["entity_type"] == "line"
        assert entity["geometry"]["line"]["start"]["x"] == 0.0
        assert entity["geometry"]["line"]["end"]["x"] == 10.0
        assert entity["properties"]["color"] == "red"

    def test_draw_line_missing_points(self):
        """Test drawing line with missing points."""
        request = {
            "document_id": self.document_id,
            "start": {"x": 0.0, "y": 0.0}
            # Missing end point
        }

        response = self.drawing_service.draw_line(request)

        assert response["success"] is False
        assert "points are required" in response["error_message"]

    def test_draw_circle(self):
        """Test drawing a circle."""
        request = {
            "document_id": self.document_id,
            "center": {"x": 5.0, "y": 5.0},
            "radius": 3.0,
            "properties": {"fill": "blue", "stroke": "black"},
        }

        response = self.drawing_service.draw_circle(request)

        assert response["success"] is True
        entity = response["entity"]
        assert entity["entity_type"] == "circle"
        assert entity["geometry"]["circle"]["center"]["x"] == 5.0
        assert entity["geometry"]["circle"]["radius"] == 3.0
        assert entity["properties"]["fill"] == "blue"

    def test_draw_circle_invalid_radius(self):
        """Test drawing circle with invalid radius."""
        request = {
            "document_id": self.document_id,
            "center": {"x": 5.0, "y": 5.0},
            "radius": -1.0,  # Invalid negative radius
        }

        response = self.drawing_service.draw_circle(request)

        assert response["success"] is False
        assert "must be positive" in response["error_message"]

    def test_draw_circle_missing_parameters(self):
        """Test drawing circle with missing parameters."""
        request = {
            "document_id": self.document_id,
            "center": {"x": 5.0, "y": 5.0}
            # Missing radius
        }

        response = self.drawing_service.draw_circle(request)

        assert response["success"] is False
        assert "radius are required" in response["error_message"]

    def test_draw_arc(self):
        """Test drawing an arc."""
        request = {
            "document_id": self.document_id,
            "center": {"x": 0.0, "y": 0.0},
            "radius": 5.0,
            "start_angle": 0.0,
            "end_angle": 90.0,
            "properties": {"style": "dashed"},
        }

        response = self.drawing_service.draw_arc(request)

        assert response["success"] is True
        entity = response["entity"]
        assert entity["entity_type"] == "arc"
        assert entity["geometry"]["arc"]["radius"] == 5.0
        assert entity["geometry"]["arc"]["start_angle"] == 0.0
        assert entity["geometry"]["arc"]["end_angle"] == 90.0
        assert entity["properties"]["style"] == "dashed"

    def test_draw_arc_invalid_radius(self):
        """Test drawing arc with invalid radius."""
        request = {
            "document_id": self.document_id,
            "center": {"x": 0.0, "y": 0.0},
            "radius": 0.0,  # Invalid zero radius
            "start_angle": 0.0,
            "end_angle": 90.0,
        }

        response = self.drawing_service.draw_arc(request)

        assert response["success"] is False
        assert "must be positive" in response["error_message"]

    def test_draw_rectangle(self):
        """Test drawing a rectangle."""
        request = {
            "document_id": self.document_id,
            "corner1": {"x": 0.0, "y": 0.0},
            "corner2": {"x": 5.0, "y": 3.0},
            "properties": {"border": "solid", "opacity": "0.8"},
        }

        response = self.drawing_service.draw_rectangle(request)

        assert response["success"] is True
        entity = response["entity"]
        assert entity["entity_type"] == "rectangle"
        assert entity["geometry"]["rectangle"]["corner1"]["x"] == 0.0
        assert entity["geometry"]["rectangle"]["corner2"]["x"] == 5.0
        assert entity["properties"]["border"] == "solid"

    def test_draw_rectangle_missing_corners(self):
        """Test drawing rectangle with missing corners."""
        request = {
            "document_id": self.document_id,
            "corner1": {"x": 0.0, "y": 0.0}
            # Missing corner2
        }

        response = self.drawing_service.draw_rectangle(request)

        assert response["success"] is False
        assert "corner points are required" in response["error_message"]

    def test_draw_polygon(self):
        """Test drawing a polygon."""
        request = {
            "document_id": self.document_id,
            "vertices": [
                {"x": 0.0, "y": 0.0},
                {"x": 2.0, "y": 0.0},
                {"x": 1.0, "y": 2.0},
            ],
            "closed": True,
            "properties": {"pattern": "crosshatch"},
        }

        response = self.drawing_service.draw_polygon(request)

        assert response["success"] is True
        entity = response["entity"]
        assert entity["entity_type"] == "polygon"
        assert len(entity["geometry"]["polygon"]["vertices"]) == 3
        assert entity["geometry"]["polygon"]["closed"] is True
        assert entity["properties"]["pattern"] == "crosshatch"

    def test_draw_polygon_insufficient_vertices(self):
        """Test drawing polygon with insufficient vertices."""
        request = {
            "document_id": self.document_id,
            "vertices": [
                {"x": 0.0, "y": 0.0},
                {"x": 1.0, "y": 1.0},
            ],  # Only 2 vertices, need at least 3
            "closed": True,
        }

        response = self.drawing_service.draw_polygon(request)

        assert response["success"] is False
        assert "At least 3 vertices" in response["error_message"]

    def test_draw_polygon_open(self):
        """Test drawing an open polygon (polyline)."""
        request = {
            "document_id": self.document_id,
            "vertices": [
                {"x": 0.0, "y": 0.0},
                {"x": 1.0, "y": 1.0},
                {"x": 2.0, "y": 0.0},
                {"x": 3.0, "y": 1.0},
            ],
            "closed": False,
        }

        response = self.drawing_service.draw_polygon(request)

        assert response["success"] is True
        entity = response["entity"]
        assert entity["geometry"]["polygon"]["closed"] is False

    def test_draw_with_invalid_document(self):
        """Test drawing operations with invalid document ID."""
        invalid_requests = [
            {
                "document_id": "invalid",
                "start": {"x": 0, "y": 0},
                "end": {"x": 1, "y": 1},
            },
            {"document_id": "invalid", "center": {"x": 0, "y": 0}, "radius": 1.0},
            {
                "document_id": "invalid",
                "center": {"x": 0, "y": 0},
                "radius": 1.0,
                "start_angle": 0.0,
                "end_angle": 90.0,
            },
            {
                "document_id": "invalid",
                "corner1": {"x": 0, "y": 0},
                "corner2": {"x": 1, "y": 1},
            },
            {
                "document_id": "invalid",
                "vertices": [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 0, "y": 1}],
                "closed": True,
            },
        ]

        drawing_methods = [
            self.drawing_service.draw_line,
            self.drawing_service.draw_circle,
            self.drawing_service.draw_arc,
            self.drawing_service.draw_rectangle,
            self.drawing_service.draw_polygon,
        ]

        for method, request in zip(drawing_methods, invalid_requests):
            response = method(request)
            assert response["success"] is False
            assert "Document ID is required" in response["error_message"]

    def test_draw_with_custom_layer(self):
        """Test drawing with custom layer specification."""
        # Create a custom layer first
        from backend.api.layer_service import LayerService

        layer_service = LayerService(self.document_service)

        layer_request = {"document_id": self.document_id, "name": "Custom Layer"}
        layer_response = layer_service.create_layer(layer_request)
        custom_layer_id = layer_response["layer"]["id"]

        # Draw line on custom layer
        line_request = {
            "document_id": self.document_id,
            "start": {"x": 0.0, "y": 0.0},
            "end": {"x": 5.0, "y": 5.0},
            "layer_id": custom_layer_id,
        }

        response = self.drawing_service.draw_line(line_request)

        assert response["success"] is True
        assert response["entity"]["layer_id"] == custom_layer_id
