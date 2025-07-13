"""
Tests for export service functionality.
"""

import os
import tempfile
import pytest
from unittest.mock import MagicMock, patch

from backend.services.export_service import (
    ExportService, 
    ExportOptions, 
    ExportBounds,
    SVGExporter,
    PDFExporter
)
from backend.models.document import CADDocument
from backend.models.entity import LineEntity, CircleEntity, ArcEntity
from backend.models.layer import Layer, Color
from backend.core.geometry.point import Point2D


class TestExportOptions:
    """Test export options configuration."""

    def test_default_options(self):
        """Test default export options."""
        options = ExportOptions()
        
        assert options.scale_factor == 1.0
        assert options.units == "mm"
        assert options.page_size == "A4"
        assert options.orientation == "portrait"
        assert options.margin == 10.0
        assert options.line_width_scale == 1.0
        assert options.precision == 3

    def test_custom_options(self):
        """Test custom export options."""
        options = ExportOptions()
        options.scale_factor = 2.0
        options.units = "inch"
        options.page_size = "A3"
        options.orientation = "landscape"
        options.include_layers = ["layer1", "layer2"]
        options.exclude_layers = ["hidden_layer"]
        
        assert options.scale_factor == 2.0
        assert options.units == "inch"
        assert options.page_size == "A3"
        assert options.orientation == "landscape"
        assert "layer1" in options.include_layers
        assert "hidden_layer" in options.exclude_layers


class TestExportBounds:
    """Test export bounds calculations."""

    def test_bounds_properties(self):
        """Test bounds property calculations."""
        bounds = ExportBounds(10, 20, 50, 80)
        
        assert bounds.width == 40
        assert bounds.height == 60
        assert bounds.center_x == 30
        assert bounds.center_y == 50

    def test_zero_bounds(self):
        """Test zero-size bounds."""
        bounds = ExportBounds(10, 10, 10, 10)
        
        assert bounds.width == 0
        assert bounds.height == 0
        assert bounds.center_x == 10
        assert bounds.center_y == 10


class TestBaseExporter:
    """Test base exporter functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        # Create test document
        self.document = CADDocument("test_doc")
        
        # Create test layers
        layer1 = Layer("layer1", "Layer 1", Color(255, 0, 0))
        layer2 = Layer("layer2", "Layer 2", Color(0, 255, 0))
        self.document.add_layer(layer1)
        self.document.add_layer(layer2)
        
        # Create test entities
        line1 = LineEntity(Point2D(0, 0), Point2D(100, 0), "layer1")
        line2 = LineEntity(Point2D(0, 0), Point2D(0, 100), "layer2")
        circle = CircleEntity(Point2D(50, 50), 25, "layer1")
        
        self.document.add_entity(line1)
        self.document.add_entity(line2)
        self.document.add_entity(circle)

    def test_calculate_bounds(self):
        """Test bounds calculation."""
        from backend.services.export_service import BaseExporter
        exporter = BaseExporter()
        options = ExportOptions()
        
        bounds = exporter.calculate_bounds(self.document, options)
        
        # Should encompass all entities
        assert bounds.min_x <= 0
        assert bounds.min_y <= 0
        assert bounds.max_x >= 100
        assert bounds.max_y >= 100

    def test_calculate_bounds_with_excluded_layers(self):
        """Test bounds calculation with layer exclusion."""
        from backend.services.export_service import BaseExporter
        exporter = BaseExporter()
        options = ExportOptions()
        options.exclude_layers = ["layer2"]
        
        bounds = exporter.calculate_bounds(self.document, options)
        
        # Should only include layer1 entities
        # Since layer2 has the vertical line (0,0)-(0,100), excluding it should affect bounds
        assert bounds.min_x >= 0  # No negative X from layer2

    def test_get_page_size_a4_portrait(self):
        """Test A4 portrait page size."""
        from backend.services.export_service import BaseExporter
        exporter = BaseExporter()
        options = ExportOptions()
        options.page_size = "A4"
        options.orientation = "portrait"
        options.units = "mm"
        
        width, height = exporter.get_page_size(options)
        
        assert width == 210
        assert height == 297

    def test_get_page_size_a4_landscape(self):
        """Test A4 landscape page size."""
        from backend.services.export_service import BaseExporter
        exporter = BaseExporter()
        options = ExportOptions()
        options.page_size = "A4"
        options.orientation = "landscape"
        options.units = "mm"
        
        width, height = exporter.get_page_size(options)
        
        assert width == 297
        assert height == 210

    def test_get_page_size_custom(self):
        """Test custom page size."""
        from backend.services.export_service import BaseExporter
        exporter = BaseExporter()
        options = ExportOptions()
        options.page_size = "CUSTOM"
        options.custom_width = 150
        options.custom_height = 200
        options.units = "mm"
        
        width, height = exporter.get_page_size(options)
        
        assert width == 150
        assert height == 200

    def test_get_page_size_inches(self):
        """Test page size in inches."""
        from backend.services.export_service import BaseExporter
        exporter = BaseExporter()
        options = ExportOptions()
        options.page_size = "LETTER"
        options.units = "inch"
        
        width, height = exporter.get_page_size(options)
        
        # LETTER is 8.5" x 11" (216mm x 279mm)
        assert abs(width - 8.5) < 0.1
        assert abs(height - 11.0) < 0.1

    def test_filter_entities(self):
        """Test entity filtering."""
        from backend.services.export_service import BaseExporter
        exporter = BaseExporter()
        options = ExportOptions()
        
        # Test no filtering
        entities = exporter.filter_entities(self.document, options)
        assert len(entities) == 3  # All entities
        
        # Test layer exclusion
        options.exclude_layers = ["layer2"]
        entities = exporter.filter_entities(self.document, options)
        assert len(entities) == 2  # Only layer1 entities
        
        # Test layer inclusion
        options = ExportOptions()
        options.include_layers = ["layer1"]
        entities = exporter.filter_entities(self.document, options)
        assert len(entities) == 2  # Only layer1 entities


@pytest.mark.skipif(not hasattr(pytest, 'importorskip'), reason="pytest.importorskip not available")
class TestSVGExporter:
    """Test SVG export functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        pytest.importorskip("svgwrite")
        
        # Create test document
        self.document = CADDocument("test_doc")
        
        # Create test layer
        layer = Layer("layer1", "Test Layer", Color(255, 0, 0))
        self.document.add_layer(layer)
        
        # Create test entities
        line = LineEntity(Point2D(0, 0), Point2D(100, 100), "layer1")
        circle = CircleEntity(Point2D(50, 25), 20, "layer1")
        
        self.document.add_entity(line)
        self.document.add_entity(circle)

    def test_svg_export_success(self):
        """Test successful SVG export."""
        exporter = SVGExporter()
        options = ExportOptions()
        
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            
        try:
            success = exporter.export(self.document, tmp_path, options)
            assert success
            assert os.path.exists(tmp_path)
            
            # Check file has content
            with open(tmp_path, 'r') as f:
                content = f.read()
                assert '<svg' in content
                assert '</svg>' in content
                assert 'line' in content or 'circle' in content
                
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_svg_export_with_options(self):
        """Test SVG export with custom options."""
        exporter = SVGExporter()
        options = ExportOptions()
        options.scale_factor = 2.0
        options.page_size = "A3"
        options.orientation = "landscape"
        
        with tempfile.NamedTemporaryFile(suffix=".svg", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            
        try:
            success = exporter.export(self.document, tmp_path, options)
            assert success
            assert os.path.exists(tmp_path)
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


@pytest.mark.skipif(not hasattr(pytest, 'importorskip'), reason="pytest.importorskip not available")
class TestPDFExporter:
    """Test PDF export functionality."""

    def setup_method(self):
        """Setup test fixtures."""
        pytest.importorskip("reportlab")
        
        # Create test document
        self.document = CADDocument("test_doc")
        
        # Create test layer
        layer = Layer("layer1", "Test Layer", Color(0, 0, 255))
        self.document.add_layer(layer)
        
        # Create test entities
        line = LineEntity(Point2D(10, 10), Point2D(90, 90), "layer1")
        circle = CircleEntity(Point2D(50, 25), 15, "layer1")
        
        self.document.add_entity(line)
        self.document.add_entity(circle)

    def test_pdf_export_success(self):
        """Test successful PDF export."""
        exporter = PDFExporter()
        options = ExportOptions()
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            
        try:
            success = exporter.export(self.document, tmp_path, options)
            assert success
            assert os.path.exists(tmp_path)
            
            # Check file has content (PDF header)
            with open(tmp_path, 'rb') as f:
                content = f.read(10)
                assert content.startswith(b'%PDF-')
                
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_pdf_export_with_metadata(self):
        """Test PDF export with metadata."""
        exporter = PDFExporter()
        options = ExportOptions()
        options.pdf_metadata = {
            "title": "Test Drawing",
            "author": "Test Author",
            "subject": "Test Subject"
        }
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            
        try:
            success = exporter.export(self.document, tmp_path, options)
            assert success
            assert os.path.exists(tmp_path)
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestExportService:
    """Test main export service."""

    def test_service_initialization(self):
        """Test export service initialization."""
        service = ExportService()
        
        # Should have registered exporters
        formats = service.get_supported_formats()
        assert isinstance(formats, list)
        
        # SVG and PDF should be available if libraries are installed
        try:
            import svgwrite
            assert "svg" in formats
        except ImportError:
            assert "svg" not in formats
            
        try:
            import reportlab
            assert "pdf" in formats
        except ImportError:
            assert "pdf" not in formats

    def test_get_export_options_template(self):
        """Test getting export options template."""
        service = ExportService()
        
        # Test for each supported format
        for format_type in service.get_supported_formats():
            options = service.get_export_options_template(format_type)
            assert options is not None
            assert isinstance(options, ExportOptions)

    def test_export_document_invalid_format(self):
        """Test export with invalid format."""
        service = ExportService()
        document = CADDocument("test")
        
        success = service.export_document(document, "test.xyz", "xyz")
        assert not success

    @patch('backend.services.export_service.SVGExporter')
    def test_export_document_svg_mock(self, mock_svg_exporter):
        """Test export document with mocked SVG exporter."""
        # Mock the SVG exporter
        mock_exporter_instance = MagicMock()
        mock_exporter_instance.export.return_value = True
        mock_svg_exporter.return_value = mock_exporter_instance
        
        service = ExportService()
        # Manually add the mocked exporter
        service.exporters['svg'] = mock_exporter_instance
        
        document = CADDocument("test")
        
        with tempfile.NamedTemporaryFile(suffix=".svg") as tmp_file:
            success = service.export_document(document, tmp_file.name, "svg")
            assert success
            mock_exporter_instance.export.assert_called_once()


class TestExportIntegration:
    """Integration tests for export functionality."""

    def setup_method(self):
        """Setup integration test fixtures."""
        # Create a more complex document
        self.document = CADDocument("integration_test")
        
        # Create multiple layers
        red_layer = Layer("red", "Red Layer", Color(255, 0, 0))
        blue_layer = Layer("blue", "Blue Layer", Color(0, 0, 255))
        green_layer = Layer("green", "Green Layer", Color(0, 255, 0))
        
        self.document.add_layer(red_layer)
        self.document.add_layer(blue_layer)
        self.document.add_layer(green_layer)
        
        # Create various entities
        entities = [
            LineEntity(Point2D(0, 0), Point2D(100, 0), "red"),
            LineEntity(Point2D(100, 0), Point2D(100, 100), "red"),
            LineEntity(Point2D(100, 100), Point2D(0, 100), "red"),
            LineEntity(Point2D(0, 100), Point2D(0, 0), "red"),
            CircleEntity(Point2D(50, 50), 30, "blue"),
            CircleEntity(Point2D(25, 25), 10, "blue"),
            ArcEntity(Point2D(75, 75), 15, 0, 90, "green"),
        ]
        
        for entity in entities:
            self.document.add_entity(entity)

    def test_export_all_formats(self):
        """Test exporting to all available formats."""
        service = ExportService()
        formats = service.get_supported_formats()
        
        for format_type in formats:
            options = ExportOptions()
            options.scale_factor = 0.5  # Scale down for testing
            
            with tempfile.NamedTemporaryFile(suffix=f".{format_type}", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                
            try:
                success = service.export_document(self.document, tmp_path, format_type, options)
                assert success, f"Failed to export to {format_type}"
                assert os.path.exists(tmp_path), f"File not created for {format_type}"
                assert os.path.getsize(tmp_path) > 0, f"Empty file for {format_type}"
                
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

    def test_export_with_layer_filtering(self):
        """Test export with layer filtering."""
        service = ExportService()
        formats = service.get_supported_formats()
        
        if not formats:
            pytest.skip("No export formats available")
            
        format_type = formats[0]  # Use first available format
        
        # Test excluding layers
        options = ExportOptions()
        options.exclude_layers = ["blue", "green"]
        
        with tempfile.NamedTemporaryFile(suffix=f".{format_type}", delete=False) as tmp_file:
            tmp_path = tmp_file.name
            
        try:
            success = service.export_document(self.document, tmp_path, format_type, options)
            assert success
            assert os.path.exists(tmp_path)
            
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_export_different_page_sizes(self):
        """Test export with different page sizes."""
        service = ExportService()
        formats = service.get_supported_formats()
        
        if not formats:
            pytest.skip("No export formats available")
            
        format_type = formats[0]
        page_sizes = ["A4", "A3", "LETTER"]
        
        for page_size in page_sizes:
            options = ExportOptions()
            options.page_size = page_size
            
            with tempfile.NamedTemporaryFile(suffix=f".{format_type}", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                
            try:
                success = service.export_document(self.document, tmp_path, format_type, options)
                assert success, f"Failed to export with page size {page_size}"
                
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)