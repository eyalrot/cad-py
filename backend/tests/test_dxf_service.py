"""Tests for the DXF import/export service."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from backend.services.dxf_service import (
    DXFService, DXFEntityMapper, DXFImportOptions, DXFExportOptions,
    DXFImportResult, DXFExportResult
)
from backend.models.document import CADDocument
from backend.models.layer import Layer, Color, LineType
from backend.core.geometry.point import Point2D
from backend.core.geometry.line import Line
from backend.core.geometry.circle import Circle
from backend.core.geometry.arc import Arc


class TestDXFEntityMapper:
    """Test cases for DXFEntityMapper."""
    
    def test_entity_mapper_initialization(self):
        """Test entity mapper initializes correctly."""
        mapper = DXFEntityMapper()
        
        assert "LINE" in mapper.supported_entities
        assert "CIRCLE" in mapper.supported_entities
        assert "ARC" in mapper.supported_entities
        assert len(mapper.aci_colors) > 0
    
    def test_color_from_aci(self):
        """Test ACI color conversion."""
        mapper = DXFEntityMapper()
        
        # Test known colors
        red = mapper.color_from_aci(1)
        assert red.red == 255
        assert red.green == 0
        assert red.blue == 0
        
        # Test unknown color (should default to white)
        unknown = mapper.color_from_aci(999)
        assert unknown.red == 255
        assert unknown.green == 255
        assert unknown.blue == 255
    
    def test_color_to_aci(self):
        """Test Color to ACI conversion."""
        mapper = DXFEntityMapper()
        
        # Test red color
        red_color = Color(255, 0, 0)
        aci = mapper.color_to_aci(red_color)
        assert aci == 1
        
        # Test approximate color matching
        almost_red = Color(250, 10, 10)
        aci = mapper.color_to_aci(almost_red)
        assert aci in mapper.aci_colors
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_dxf_line_conversion(self, mock_ezdxf):
        """Test DXF LINE to CAD Line conversion."""
        mapper = DXFEntityMapper()
        
        # Mock DXF line entity
        mock_line = Mock()
        mock_line.dxftype.return_value = "LINE"
        mock_line.dxf.layer = "0"
        mock_line.dxf.start = Mock(x=0, y=0)
        mock_line.dxf.end = Mock(x=100, y=100)
        
        # Convert to CAD entity
        cad_line = mapper.dxf_to_cad_entity(mock_line)
        
        assert isinstance(cad_line, Line)
        assert cad_line.start.x == 0
        assert cad_line.start.y == 0
        assert cad_line.end.x == 100
        assert cad_line.end.y == 100
        assert cad_line.layer_id == "0"
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_dxf_circle_conversion(self, mock_ezdxf):
        """Test DXF CIRCLE to CAD Circle conversion."""
        mapper = DXFEntityMapper()
        
        # Mock DXF circle entity
        mock_circle = Mock()
        mock_circle.dxftype.return_value = "CIRCLE"
        mock_circle.dxf.layer = "0"
        mock_circle.dxf.center = Mock(x=50, y=50)
        mock_circle.dxf.radius = 25
        
        # Convert to CAD entity
        cad_circle = mapper.dxf_to_cad_entity(mock_circle)
        
        assert isinstance(cad_circle, Circle)
        assert cad_circle.center.x == 50
        assert cad_circle.center.y == 50
        assert cad_circle.radius == 25
        assert cad_circle.layer_id == "0"
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_dxf_arc_conversion(self, mock_ezdxf):
        """Test DXF ARC to CAD Arc conversion."""
        mapper = DXFEntityMapper()
        
        # Mock DXF arc entity
        mock_arc = Mock()
        mock_arc.dxftype.return_value = "ARC"
        mock_arc.dxf.layer = "0"
        mock_arc.dxf.center = Mock(x=50, y=50)
        mock_arc.dxf.radius = 25
        mock_arc.dxf.start_angle = 0
        mock_arc.dxf.end_angle = 90
        
        # Convert to CAD entity
        cad_arc = mapper.dxf_to_cad_entity(mock_arc)
        
        assert isinstance(cad_arc, Arc)
        assert cad_arc.center.x == 50
        assert cad_arc.center.y == 50
        assert cad_arc.radius == 25
        assert cad_arc.layer_id == "0"
    
    def test_unsupported_entity_conversion(self):
        """Test conversion of unsupported entity types."""
        mapper = DXFEntityMapper()
        
        # Mock unsupported entity
        mock_entity = Mock()
        mock_entity.dxftype.return_value = "UNSUPPORTED"
        
        # Should return None for unsupported types
        result = mapper.dxf_to_cad_entity(mock_entity)
        assert result is None


class TestDXFService:
    """Test cases for DXFService."""
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_service_initialization(self, mock_ezdxf):
        """Test DXF service initializes correctly."""
        service = DXFService()
        
        assert service.entity_mapper is not None
        assert len(service.VERSION_MAP) > 0
        assert "R2010" in service.VERSION_MAP
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_service_initialization_no_ezdxf(self, mock_ezdxf):
        """Test service initialization without ezdxf."""
        # Simulate ezdxf not available
        with patch('backend.services.dxf_service.ezdxf', None):
            with pytest.raises(ImportError, match="ezdxf library is required"):
                DXFService()
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_import_dxf_success(self, mock_ezdxf):
        """Test successful DXF import."""
        # Mock ezdxf document
        mock_doc = Mock()
        mock_doc.modelspace.return_value = []
        mock_doc.layers = []
        mock_ezdxf.readfile.return_value = mock_doc
        
        service = DXFService()
        
        # Create temporary file for testing
        with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        
        try:
            result = service.import_dxf(tmp_path)
            
            assert result.success
            assert result.document is not None
            assert isinstance(result.document, CADDocument)
            assert len(result.errors) == 0
            
        finally:
            tmp_path.unlink()  # Clean up
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_import_dxf_file_not_found(self, mock_ezdxf):
        """Test DXF import with missing file."""
        mock_ezdxf.readfile.side_effect = FileNotFoundError()
        
        service = DXFService()
        result = service.import_dxf("nonexistent.dxf")
        
        assert not result.success
        assert result.document is None
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_import_dxf_structure_error(self, mock_ezdxf):
        """Test DXF import with structure error."""
        mock_ezdxf.readfile.side_effect = mock_ezdxf.DXFStructureError("Invalid structure")
        mock_ezdxf.DXFStructureError = Exception  # Mock the exception class
        
        service = DXFService()
        result = service.import_dxf("invalid.dxf")
        
        assert not result.success
        assert result.document is None
        assert len(result.errors) > 0
        assert "structure" in result.errors[0].lower()
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_import_dxf_with_entities(self, mock_ezdxf):
        """Test DXF import with entities."""
        # Mock DXF entities
        mock_line = Mock()
        mock_line.dxftype.return_value = "LINE"
        mock_line.dxf.layer = "0"
        mock_line.dxf.start = Mock(x=0, y=0)
        mock_line.dxf.end = Mock(x=100, y=100)
        
        mock_circle = Mock()
        mock_circle.dxftype.return_value = "CIRCLE"
        mock_circle.dxf.layer = "0"
        mock_circle.dxf.center = Mock(x=50, y=50)
        mock_circle.dxf.radius = 25
        
        # Mock document
        mock_doc = Mock()
        mock_doc.modelspace.return_value = [mock_line, mock_circle]
        mock_doc.layers = []
        mock_ezdxf.readfile.return_value = mock_doc
        
        service = DXFService()
        
        with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        
        try:
            result = service.import_dxf(tmp_path)
            
            assert result.success
            assert result.stats["entities_imported"] == 2
            assert len(result.document.entities) == 2
            
        finally:
            tmp_path.unlink()
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_import_dxf_with_layers(self, mock_ezdxf):
        """Test DXF import with layers."""
        # Mock DXF layer
        mock_layer = Mock()
        mock_layer.dxf.name = "TestLayer"
        mock_layer.dxf.color = 1  # Red
        mock_layer.dxf.linetype = "CONTINUOUS"
        mock_layer.dxf.lineweight = 25
        mock_layer.is_off = False
        mock_layer.is_locked = False
        
        # Mock document
        mock_doc = Mock()
        mock_doc.modelspace.return_value = []
        mock_doc.layers = [mock_layer]
        mock_ezdxf.readfile.return_value = mock_doc
        
        service = DXFService()
        
        with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        
        try:
            result = service.import_dxf(tmp_path)
            
            assert result.success
            assert result.stats["layers_imported"] == 1
            assert "TestLayer" in result.document.layers
            
        finally:
            tmp_path.unlink()
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_export_dxf_success(self, mock_ezdxf):
        """Test successful DXF export."""
        # Mock ezdxf document creation
        mock_doc = Mock()
        mock_doc.layers = Mock()
        mock_doc.header = {}
        mock_doc.modelspace.return_value = Mock()
        mock_doc.saveas = Mock()
        mock_ezdxf.new.return_value = mock_doc
        
        service = DXFService()
        
        # Create CAD document with entities
        cad_doc = CADDocument("test")
        layer = Layer("0", Color(255, 255, 255), LineType.CONTINUOUS, 0.25)
        cad_doc.add_layer(layer)
        
        line = Line(Point2D(0, 0), Point2D(100, 100), "0")
        cad_doc.add_entity(line)
        
        with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        
        try:
            result = service.export_dxf(cad_doc, tmp_path)
            
            assert result.success
            assert result.file_path == str(tmp_path)
            assert len(result.errors) == 0
            mock_doc.saveas.assert_called_once()
            
        finally:
            tmp_path.unlink()
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_export_dxf_invalid_version(self, mock_ezdxf):
        """Test DXF export with invalid version."""
        service = DXFService()
        cad_doc = CADDocument("test")
        
        options = DXFExportOptions(version="INVALID")
        result = service.export_dxf(cad_doc, "test.dxf", options)
        
        assert not result.success
        assert len(result.errors) > 0
        assert "unsupported" in result.errors[0].lower()
    
    def test_import_options(self):
        """Test DXF import options."""
        options = DXFImportOptions(
            merge_duplicate_layers=False,
            import_blocks=False,
            scale_factor=2.0,
            layer_filter=["Layer1", "Layer2"],
            entity_filter=["LINE", "CIRCLE"]
        )
        
        assert not options.merge_duplicate_layers
        assert not options.import_blocks
        assert options.scale_factor == 2.0
        assert "Layer1" in options.layer_filter
        assert "LINE" in options.entity_filter
    
    def test_export_options(self):
        """Test DXF export options."""
        options = DXFExportOptions(
            version="R2018",
            precision=8,
            export_invisible_layers=True,
            unit_scale=0.5,
            header_variables={"$INSUNITS": 4}
        )
        
        assert options.version == "R2018"
        assert options.precision == 8
        assert options.export_invisible_layers
        assert options.unit_scale == 0.5
        assert options.header_variables["$INSUNITS"] == 4
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_get_supported_versions(self, mock_ezdxf):
        """Test getting supported DXF versions."""
        service = DXFService()
        versions = service.get_supported_versions()
        
        assert isinstance(versions, list)
        assert len(versions) > 0
        assert "R2010" in versions
        assert "R2018" in versions
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_get_file_info(self, mock_ezdxf):
        """Test getting DXF file information."""
        # Mock DXF document
        mock_doc = Mock()
        mock_doc.dxfversion = "AC1024"
        mock_doc.modelspace.return_value = ["entity1", "entity2"]
        mock_doc.layers = ["layer1", "layer2"]
        mock_doc.blocks = ["block1"]
        mock_doc.header = {"$TDCREATE": "2023-01-01", "$TDUPDATE": "2023-01-02"}
        mock_ezdxf.readfile.return_value = mock_doc
        
        service = DXFService()
        
        with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        
        try:
            info = service.get_file_info(tmp_path)
            
            assert info["version"] == "AC1024"
            assert info["entity_count"] == 2
            assert info["layer_count"] == 2
            assert info["block_count"] == 1
            assert "file_size" in info
            
        finally:
            tmp_path.unlink()
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_get_file_info_error(self, mock_ezdxf):
        """Test getting file info with error."""
        mock_ezdxf.readfile.side_effect = Exception("Read error")
        
        service = DXFService()
        info = service.get_file_info("nonexistent.dxf")
        
        assert "error" in info
        assert "Read error" in info["error"]


class TestDXFResults:
    """Test cases for DXF result classes."""
    
    def test_import_result(self):
        """Test DXF import result structure."""
        result = DXFImportResult(
            document=None,
            success=False,
            errors=["Error 1"],
            warnings=["Warning 1"],
            stats={"entities": 10}
        )
        
        assert result.document is None
        assert not result.success
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert result.stats["entities"] == 10
    
    def test_export_result(self):
        """Test DXF export result structure."""
        result = DXFExportResult(
            success=True,
            file_path="/path/to/file.dxf",
            errors=[],
            warnings=["Warning 1"],
            stats={"entities": 5}
        )
        
        assert result.success
        assert result.file_path == "/path/to/file.dxf"
        assert len(result.errors) == 0
        assert len(result.warnings) == 1
        assert result.stats["entities"] == 5


class TestDXFIntegration:
    """Integration tests for DXF service."""
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_round_trip_conversion(self, mock_ezdxf):
        """Test round-trip DXF export and import."""
        # This would be a more complex integration test
        # that exports a CAD document and then imports it back
        # to verify data integrity
        pass
    
    @patch('backend.services.dxf_service.ezdxf')
    def test_large_file_performance(self, mock_ezdxf):
        """Test performance with large DXF files."""
        # Mock large document
        large_entities = [Mock() for _ in range(10000)]
        for i, entity in enumerate(large_entities):
            entity.dxftype.return_value = "LINE"
            entity.dxf.layer = "0"
            entity.dxf.start = Mock(x=i, y=0)
            entity.dxf.end = Mock(x=i+1, y=1)
        
        mock_doc = Mock()
        mock_doc.modelspace.return_value = large_entities
        mock_doc.layers = []
        mock_ezdxf.readfile.return_value = mock_doc
        
        service = DXFService()
        
        with tempfile.NamedTemporaryFile(suffix='.dxf', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        
        try:
            # Import should handle large files efficiently
            result = service.import_dxf(tmp_path)
            
            assert result.success
            # Performance assertion would go here
            # assert result.stats["import_time"] < some_threshold
            
        finally:
            tmp_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__])