"""DXF import/export service with support for AutoCAD R12-2018 formats."""

import logging
import math
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass

try:
    import ezdxf
    from ezdxf.document import Drawing
    from ezdxf.entities import DXFEntity
    from ezdxf.layouts import Modelspace
except ImportError:
    ezdxf = None
    Drawing = None
    DXFEntity = None
    Modelspace = None

from backend.models.document import CADDocument
from backend.models.layer import Layer, Color, LineType
from backend.models.entity import BaseEntity
from backend.core.geometry.point import Point2D
from backend.core.geometry.line import Line
from backend.core.geometry.circle import Circle
from backend.core.geometry.arc import Arc
from backend.core.geometry.rectangle import Rectangle


logger = logging.getLogger(__name__)


@dataclass
class DXFImportOptions:
    """Options for DXF import operations."""
    merge_duplicate_layers: bool = True
    import_blocks: bool = True
    import_dimensions: bool = True
    import_text: bool = True
    scale_factor: float = 1.0
    layer_filter: Optional[List[str]] = None
    entity_filter: Optional[List[str]] = None


@dataclass
class DXFExportOptions:
    """Options for DXF export operations."""
    version: str = "R2010"
    precision: int = 6
    export_invisible_layers: bool = False
    export_locked_layers: bool = True
    unit_scale: float = 1.0
    header_variables: Optional[Dict[str, Any]] = None


@dataclass
class DXFImportResult:
    """Result of DXF import operation."""
    document: Optional[CADDocument]
    success: bool
    errors: List[str]
    warnings: List[str]
    stats: Dict[str, int]


@dataclass
class DXFExportResult:
    """Result of DXF export operation."""
    success: bool
    file_path: Optional[str]
    errors: List[str]
    warnings: List[str]
    stats: Dict[str, int]


class DXFEntityMapper:
    """Maps between DXF entities and CAD entities."""
    
    def __init__(self):
        self.supported_entities = {
            "LINE", "CIRCLE", "ARC", "LWPOLYLINE", "POLYLINE",
            "POINT", "TEXT", "MTEXT", "INSERT", "DIMENSION"
        }
        
        # Color mapping (AutoCAD Color Index to RGB)
        self.aci_colors = {
            1: (255, 0, 0),      # Red
            2: (255, 255, 0),    # Yellow
            3: (0, 255, 0),      # Green
            4: (0, 255, 255),    # Cyan
            5: (0, 0, 255),      # Blue
            6: (255, 0, 255),    # Magenta
            7: (255, 255, 255),  # White
            8: (128, 128, 128),  # Gray
            9: (192, 192, 192),  # Light Gray
        }
    
    def dxf_to_cad_entity(self, dxf_entity: 'DXFEntity') -> Optional[BaseEntity]:
        """Convert DXF entity to CAD entity."""
        try:
            entity_type = dxf_entity.dxftype()
            layer_id = getattr(dxf_entity.dxf, 'layer', '0')
            
            if entity_type == "LINE":
                return self._convert_line(dxf_entity, layer_id)
            elif entity_type == "CIRCLE":
                return self._convert_circle(dxf_entity, layer_id)
            elif entity_type == "ARC":
                return self._convert_arc(dxf_entity, layer_id)
            elif entity_type in ["LWPOLYLINE", "POLYLINE"]:
                return self._convert_polyline(dxf_entity, layer_id)
            elif entity_type == "POINT":
                return self._convert_point(dxf_entity, layer_id)
            else:
                logger.debug(f"Unsupported entity type: {entity_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error converting DXF entity {entity_type}: {e}")
            return None
    
    def cad_to_dxf_entity(self, cad_entity: BaseEntity, msp: 'Modelspace') -> Optional['DXFEntity']:
        """Convert CAD entity to DXF entity."""
        try:
            if isinstance(cad_entity, Line):
                return self._create_dxf_line(cad_entity, msp)
            elif isinstance(cad_entity, Circle):
                return self._create_dxf_circle(cad_entity, msp)
            elif isinstance(cad_entity, Arc):
                return self._create_dxf_arc(cad_entity, msp)
            elif isinstance(cad_entity, Rectangle):
                return self._create_dxf_rectangle(cad_entity, msp)
            else:
                logger.debug(f"Unsupported CAD entity type: {type(cad_entity)}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating DXF entity: {e}")
            return None
    
    def _convert_line(self, dxf_entity: 'DXFEntity', layer_id: str) -> Line:
        """Convert DXF LINE to CAD Line."""
        start_point = Point2D(dxf_entity.dxf.start.x, dxf_entity.dxf.start.y)
        end_point = Point2D(dxf_entity.dxf.end.x, dxf_entity.dxf.end.y)
        
        return Line(
            start=start_point,
            end=end_point,
            layer_id=layer_id
        )
    
    def _convert_circle(self, dxf_entity: 'DXFEntity', layer_id: str) -> Circle:
        """Convert DXF CIRCLE to CAD Circle."""
        center = Point2D(dxf_entity.dxf.center.x, dxf_entity.dxf.center.y)
        radius = dxf_entity.dxf.radius
        
        return Circle(
            center=center,
            radius=radius,
            layer_id=layer_id
        )
    
    def _convert_arc(self, dxf_entity: 'DXFEntity', layer_id: str) -> Arc:
        """Convert DXF ARC to CAD Arc."""
        center = Point2D(dxf_entity.dxf.center.x, dxf_entity.dxf.center.y)
        radius = dxf_entity.dxf.radius
        start_angle = math.radians(dxf_entity.dxf.start_angle)
        end_angle = math.radians(dxf_entity.dxf.end_angle)
        
        return Arc(
            center=center,
            radius=radius,
            start_angle=start_angle,
            end_angle=end_angle,
            layer_id=layer_id
        )
    
    def _convert_polyline(self, dxf_entity: 'DXFEntity', layer_id: str) -> Optional[BaseEntity]:
        """Convert DXF POLYLINE/LWPOLYLINE to CAD entities."""
        # For now, convert polylines to multiple line segments
        # This could be enhanced to support a Polyline entity type
        points = []
        
        if dxf_entity.dxftype() == "LWPOLYLINE":
            for point in dxf_entity.get_points():
                points.append(Point2D(point[0], point[1]))
        else:  # POLYLINE
            for vertex in dxf_entity.vertices:
                points.append(Point2D(vertex.dxf.location.x, vertex.dxf.location.y))
        
        if len(points) < 2:
            return None
        
        # Return first line segment (in a real implementation, 
        # you might want to return a list or create a compound entity)
        return Line(
            start=points[0],
            end=points[1],
            layer_id=layer_id
        )
    
    def _convert_point(self, dxf_entity: 'DXFEntity', layer_id: str) -> Optional[BaseEntity]:
        """Convert DXF POINT to CAD Point (if Point entity exists)."""
        # For now, skip points as we don't have a Point entity
        logger.debug("Skipping POINT entity (not implemented)")
        return None
    
    def _create_dxf_line(self, line: Line, msp: 'Modelspace') -> 'DXFEntity':
        """Create DXF LINE from CAD Line."""
        return msp.add_line(
            start=(line.start.x, line.start.y),
            end=(line.end.x, line.end.y),
            dxfattribs={"layer": line.layer_id}
        )
    
    def _create_dxf_circle(self, circle: Circle, msp: 'Modelspace') -> 'DXFEntity':
        """Create DXF CIRCLE from CAD Circle."""
        return msp.add_circle(
            center=(circle.center.x, circle.center.y),
            radius=circle.radius,
            dxfattribs={"layer": circle.layer_id}
        )
    
    def _create_dxf_arc(self, arc: Arc, msp: 'Modelspace') -> 'DXFEntity':
        """Create DXF ARC from CAD Arc."""
        start_angle_deg = math.degrees(arc.start_angle)
        end_angle_deg = math.degrees(arc.end_angle)
        
        return msp.add_arc(
            center=(arc.center.x, arc.center.y),
            radius=arc.radius,
            start_angle=start_angle_deg,
            end_angle=end_angle_deg,
            dxfattribs={"layer": arc.layer_id}
        )
    
    def _create_dxf_rectangle(self, rect: Rectangle, msp: 'Modelspace') -> 'DXFEntity':
        """Create DXF LWPOLYLINE from CAD Rectangle."""
        # Create rectangle as closed polyline
        points = [
            (rect.min_point.x, rect.min_point.y),
            (rect.max_point.x, rect.min_point.y),
            (rect.max_point.x, rect.max_point.y),
            (rect.min_point.x, rect.max_point.y)
        ]
        
        return msp.add_lwpolyline(
            points=points,
            close=True,
            dxfattribs={"layer": rect.layer_id}
        )
    
    def color_from_aci(self, aci_color: int) -> Color:
        """Convert AutoCAD Color Index to Color."""
        if aci_color in self.aci_colors:
            rgb = self.aci_colors[aci_color]
            return Color(rgb[0], rgb[1], rgb[2])
        else:
            # Default to white for unknown colors
            return Color(255, 255, 255)
    
    def color_to_aci(self, color: Color) -> int:
        """Convert Color to AutoCAD Color Index (best match)."""
        rgb = (color.red, color.green, color.blue)
        
        # Find closest ACI color
        min_distance = float('inf')
        best_aci = 7  # Default to white
        
        for aci, aci_rgb in self.aci_colors.items():
            distance = sum((a - b) ** 2 for a, b in zip(rgb, aci_rgb))
            if distance < min_distance:
                min_distance = distance
                best_aci = aci
        
        return best_aci


class DXFService:
    """Service for importing and exporting DXF files."""
    
    # DXF version mapping
    VERSION_MAP = {
        "R12": "AC1009",
        "R14": "AC1014", 
        "R2000": "AC1015",
        "R2004": "AC1018",
        "R2007": "AC1021",
        "R2010": "AC1024",
        "R2013": "AC1027",
        "R2018": "AC1032"
    }
    
    def __init__(self):
        if ezdxf is None:
            raise ImportError("ezdxf library is required for DXF support. Install with: pip install ezdxf")
        
        self.entity_mapper = DXFEntityMapper()
        
        logger.info("DXF service initialized")
    
    def import_dxf(self, file_path: Union[str, Path], options: Optional[DXFImportOptions] = None) -> DXFImportResult:
        """Import a DXF file and convert to CAD document."""
        if options is None:
            options = DXFImportOptions()
        
        file_path = Path(file_path)
        result = DXFImportResult(
            document=None,
            success=False,
            errors=[],
            warnings=[],
            stats={}
        )
        
        try:
            # Read DXF file
            logger.info(f"Importing DXF file: {file_path}")
            dxf_doc = ezdxf.readfile(str(file_path))
            
            # Create CAD document
            cad_doc = CADDocument(name=file_path.stem)
            
            # Import layers
            layer_count = self._import_layers(dxf_doc, cad_doc, options, result)
            
            # Import entities
            entity_count = self._import_entities(dxf_doc, cad_doc, options, result)
            
            # Set statistics
            result.stats = {
                "layers_imported": layer_count,
                "entities_imported": entity_count,
                "total_dxf_entities": len(list(dxf_doc.modelspace())),
                "file_size_bytes": file_path.stat().st_size
            }
            
            result.document = cad_doc
            result.success = True
            
            logger.info(f"DXF import completed: {entity_count} entities, {layer_count} layers")
            
        except ezdxf.DXFStructureError as e:
            error_msg = f"Invalid DXF file structure: {e}"
            result.errors.append(error_msg)
            logger.error(error_msg)
            
        except ezdxf.DXFVersionError as e:
            error_msg = f"Unsupported DXF version: {e}"
            result.errors.append(error_msg)
            logger.error(error_msg)
            
        except FileNotFoundError:
            error_msg = f"DXF file not found: {file_path}"
            result.errors.append(error_msg)
            logger.error(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error during DXF import: {e}"
            result.errors.append(error_msg)
            logger.error(error_msg)
        
        return result
    
    def export_dxf(self, document: CADDocument, file_path: Union[str, Path], 
                   options: Optional[DXFExportOptions] = None) -> DXFExportResult:
        """Export CAD document to DXF file."""
        if options is None:
            options = DXFExportOptions()
        
        file_path = Path(file_path)
        result = DXFExportResult(
            success=False,
            file_path=None,
            errors=[],
            warnings=[],
            stats={}
        )
        
        try:
            # Validate DXF version
            if options.version not in self.VERSION_MAP:
                raise ValueError(f"Unsupported DXF version: {options.version}")
            
            # Create new DXF document
            logger.info(f"Exporting to DXF file: {file_path}")
            dxf_version = self.VERSION_MAP[options.version]
            dxf_doc = ezdxf.new(dxf_version)
            
            # Set header variables
            if options.header_variables:
                for var, value in options.header_variables.items():
                    dxf_doc.header[var] = value
            
            # Export layers
            layer_count = self._export_layers(document, dxf_doc, options, result)
            
            # Export entities
            entity_count = self._export_entities(document, dxf_doc, options, result)
            
            # Save DXF file
            dxf_doc.saveas(str(file_path))
            
            # Set statistics
            result.stats = {
                "layers_exported": layer_count,
                "entities_exported": entity_count,
                "total_cad_entities": len(document.entities),
                "dxf_version": options.version,
                "file_size_bytes": file_path.stat().st_size if file_path.exists() else 0
            }
            
            result.success = True
            result.file_path = str(file_path)
            
            logger.info(f"DXF export completed: {entity_count} entities, {layer_count} layers")
            
        except ValueError as e:
            error_msg = str(e)
            result.errors.append(error_msg)
            logger.error(error_msg)
            
        except PermissionError:
            error_msg = f"Permission denied writing to: {file_path}"
            result.errors.append(error_msg)
            logger.error(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error during DXF export: {e}"
            result.errors.append(error_msg)
            logger.error(error_msg)
        
        return result
    
    def _import_layers(self, dxf_doc: 'Drawing', cad_doc: CADDocument, 
                      options: DXFImportOptions, result: DXFImportResult) -> int:
        """Import layers from DXF document."""
        layer_count = 0
        
        try:
            for dxf_layer in dxf_doc.layers:
                layer_name = dxf_layer.dxf.name
                
                # Apply layer filter
                if options.layer_filter and layer_name not in options.layer_filter:
                    continue
                
                # Check for duplicate layers
                if options.merge_duplicate_layers and cad_doc.get_layer(layer_name):
                    result.warnings.append(f"Duplicate layer '{layer_name}' - merging")
                    continue
                
                # Convert layer properties
                color = self.entity_mapper.color_from_aci(dxf_layer.dxf.color)
                line_type = self._map_line_type(getattr(dxf_layer.dxf, 'linetype', 'CONTINUOUS'))
                line_weight = getattr(dxf_layer.dxf, 'lineweight', 25) / 100.0  # Convert from 1/100mm to mm
                
                # Create CAD layer
                layer = Layer(
                    name=layer_name,
                    color=color,
                    line_type=line_type,
                    line_weight=line_weight,
                    visible=not getattr(dxf_layer, 'is_off', False),
                    locked=getattr(dxf_layer, 'is_locked', False),
                    printable=True  # Default to printable
                )
                
                cad_doc.add_layer(layer)
                layer_count += 1
                
        except Exception as e:
            result.warnings.append(f"Error importing layers: {e}")
            logger.warning(f"Error importing layers: {e}")
        
        return layer_count
    
    def _import_entities(self, dxf_doc: 'Drawing', cad_doc: CADDocument,
                        options: DXFImportOptions, result: DXFImportResult) -> int:
        """Import entities from DXF document."""
        entity_count = 0
        
        try:
            modelspace = dxf_doc.modelspace()
            
            for dxf_entity in modelspace:
                entity_type = dxf_entity.dxftype()
                
                # Apply entity filter
                if options.entity_filter and entity_type not in options.entity_filter:
                    continue
                
                # Skip unsupported entities with warning
                if entity_type not in self.entity_mapper.supported_entities:
                    result.warnings.append(f"Unsupported entity type: {entity_type}")
                    continue
                
                # Convert entity
                cad_entity = self.entity_mapper.dxf_to_cad_entity(dxf_entity)
                
                if cad_entity:
                    # Apply scale factor
                    if options.scale_factor != 1.0:
                        cad_entity = self._scale_entity(cad_entity, options.scale_factor)
                    
                    cad_doc.add_entity(cad_entity)
                    entity_count += 1
                else:
                    result.warnings.append(f"Failed to convert {entity_type} entity")
                    
        except Exception as e:
            result.warnings.append(f"Error importing entities: {e}")
            logger.warning(f"Error importing entities: {e}")
        
        return entity_count
    
    def _export_layers(self, cad_doc: CADDocument, dxf_doc: 'Drawing',
                      options: DXFExportOptions, result: DXFExportResult) -> int:
        """Export layers to DXF document."""
        layer_count = 0
        
        try:
            for layer in cad_doc.layers.values():
                # Skip invisible layers if option is set
                if not options.export_invisible_layers and not layer.visible:
                    continue
                
                # Skip locked layers if option is set
                if not options.export_locked_layers and layer.locked:
                    continue
                
                # Create DXF layer
                dxf_layer = dxf_doc.layers.new(
                    name=layer.name,
                    dxfattribs={
                        "color": self.entity_mapper.color_to_aci(layer.color),
                        "linetype": self._map_line_type_to_dxf(layer.line_type),
                        "lineweight": int(layer.line_weight * 100)  # Convert mm to 1/100mm
                    }
                )
                
                # Set layer state
                if not layer.visible:
                    dxf_layer.off()
                if layer.locked:
                    dxf_layer.lock()
                
                layer_count += 1
                
        except Exception as e:
            result.warnings.append(f"Error exporting layers: {e}")
            logger.warning(f"Error exporting layers: {e}")
        
        return layer_count
    
    def _export_entities(self, cad_doc: CADDocument, dxf_doc: 'Drawing',
                        options: DXFExportOptions, result: DXFExportResult) -> int:
        """Export entities to DXF document."""
        entity_count = 0
        
        try:
            modelspace = dxf_doc.modelspace()
            
            for cad_entity in cad_doc.entities:
                # Apply unit scale
                if options.unit_scale != 1.0:
                    cad_entity = self._scale_entity(cad_entity, options.unit_scale)
                
                # Convert entity
                dxf_entity = self.entity_mapper.cad_to_dxf_entity(cad_entity, modelspace)
                
                if dxf_entity:
                    entity_count += 1
                else:
                    result.warnings.append(f"Failed to convert {type(cad_entity).__name__} entity")
                    
        except Exception as e:
            result.warnings.append(f"Error exporting entities: {e}")
            logger.warning(f"Error exporting entities: {e}")
        
        return entity_count
    
    def _map_line_type(self, dxf_linetype: str) -> LineType:
        """Map DXF linetype to CAD LineType."""
        linetype_map = {
            "CONTINUOUS": LineType.CONTINUOUS,
            "DASHED": LineType.DASHED,
            "DOTTED": LineType.DOTTED,
            "DASHDOT": LineType.DASH_DOT,
            "CENTER": LineType.CENTER,
            "HIDDEN": LineType.HIDDEN
        }
        
        return linetype_map.get(dxf_linetype.upper(), LineType.CONTINUOUS)
    
    def _map_line_type_to_dxf(self, line_type: LineType) -> str:
        """Map CAD LineType to DXF linetype."""
        linetype_map = {
            LineType.CONTINUOUS: "CONTINUOUS",
            LineType.DASHED: "DASHED",
            LineType.DOTTED: "DOTTED", 
            LineType.DASH_DOT: "DASHDOT",
            LineType.CENTER: "CENTER",
            LineType.HIDDEN: "HIDDEN"
        }
        
        return linetype_map.get(line_type, "CONTINUOUS")
    
    def _scale_entity(self, entity: BaseEntity, scale_factor: float) -> BaseEntity:
        """Scale an entity by the given factor."""
        # This is a simplified implementation
        # In practice, you'd want to create a new entity with scaled coordinates
        if hasattr(entity, 'scale'):
            entity.scale(scale_factor)
        return entity
    
    def get_supported_versions(self) -> List[str]:
        """Get list of supported DXF versions."""
        return list(self.VERSION_MAP.keys())
    
    def get_file_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Get information about a DXF file without full import."""
        try:
            dxf_doc = ezdxf.readfile(str(file_path))
            
            return {
                "version": dxf_doc.dxfversion,
                "entity_count": len(list(dxf_doc.modelspace())),
                "layer_count": len(dxf_doc.layers),
                "block_count": len(dxf_doc.blocks),
                "file_size": Path(file_path).stat().st_size,
                "creation_date": dxf_doc.header.get("$TDCREATE", "Unknown"),
                "last_update": dxf_doc.header.get("$TDUPDATE", "Unknown")
            }
            
        except Exception as e:
            logger.error(f"Error reading DXF file info: {e}")
            return {"error": str(e)}