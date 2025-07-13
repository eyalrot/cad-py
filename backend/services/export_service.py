"""Export service for CAD documents to various formats."""

import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Optional dependencies for export formats
try:
    import svgwrite
    SVG_AVAILABLE = True
except ImportError:
    SVG_AVAILABLE = False

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, LETTER, A3, A2, A1, A0
    from reportlab.lib.units import mm, inch
    from reportlab.graphics import renderPDF
    from reportlab.graphics.shapes import Drawing, Line, Circle, Polygon
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

from backend.core.geometry.bbox import BoundingBox
from backend.core.geometry.point import Point2D
from backend.models.document import CADDocument
from backend.models.entity import BaseEntity, LineEntity, CircleEntity, ArcEntity
from backend.models.layer import Layer

logger = logging.getLogger(__name__)


class ExportOptions:
    """Options for export operations."""
    
    def __init__(self):
        # General options
        self.include_layers: List[str] = []  # Empty means all visible layers
        self.exclude_layers: List[str] = []
        self.scale_factor: float = 1.0
        self.units: str = "mm"  # mm, inch, px
        
        # Page/Canvas options
        self.page_size: str = "A4"  # A4, A3, A2, A1, A0, LETTER, LEGAL, CUSTOM
        self.orientation: str = "portrait"  # portrait, landscape
        self.custom_width: Optional[float] = None
        self.custom_height: Optional[float] = None
        self.margin: float = 10.0  # margin in units
        
        # Quality options
        self.line_width_scale: float = 1.0
        self.text_scale: float = 1.0
        self.precision: int = 3  # decimal places for coordinates
        
        # Format-specific options
        self.svg_embed_fonts: bool = False
        self.pdf_compression: bool = True
        self.pdf_metadata: Dict[str, str] = {}


class ExportBounds:
    """Calculated bounds for export."""
    
    def __init__(self, min_x: float, min_y: float, max_x: float, max_y: float):
        self.min_x = min_x
        self.min_y = min_y
        self.max_x = max_x
        self.max_y = max_y
        
    @property
    def width(self) -> float:
        return self.max_x - self.min_x
        
    @property
    def height(self) -> float:
        return self.max_y - self.min_y
        
    @property
    def center_x(self) -> float:
        return (self.min_x + self.max_x) / 2
        
    @property
    def center_y(self) -> float:
        return (self.min_y + self.max_y) / 2


class BaseExporter:
    """Base class for all export formats."""
    
    def __init__(self):
        self.options = ExportOptions()
        
    def calculate_bounds(self, document: CADDocument, options: ExportOptions) -> ExportBounds:
        """Calculate the bounds of all exportable entities."""
        if not document.entities:
            return ExportBounds(0, 0, 100, 100)  # Default bounds
            
        min_x = float('inf')
        min_y = float('inf')
        max_x = float('-inf')
        max_y = float('-inf')
        
        for entity in document.entities:
            # Skip entities on excluded layers
            if entity.layer_id in options.exclude_layers:
                continue
                
            # Skip entities on non-included layers (if include list is specified)
            if options.include_layers and entity.layer_id not in options.include_layers:
                continue
                
            # Get entity bounds
            bbox = entity.get_bounding_box()
            if bbox:
                min_x = min(min_x, bbox[0])
                min_y = min(min_y, bbox[1])
                max_x = max(max_x, bbox[2])
                max_y = max(max_y, bbox[3])
                
        # Handle case where no entities are found
        if min_x == float('inf'):
            return ExportBounds(0, 0, 100, 100)
            
        return ExportBounds(min_x, min_y, max_x, max_y)
        
    def get_page_size(self, options: ExportOptions) -> Tuple[float, float]:
        """Get page size in specified units."""
        # Standard page sizes in mm
        page_sizes = {
            "A0": (841, 1189),
            "A1": (594, 841),
            "A2": (420, 594), 
            "A3": (297, 420),
            "A4": (210, 297),
            "LETTER": (216, 279),  # 8.5" x 11" in mm
            "LEGAL": (216, 356),   # 8.5" x 14" in mm
        }
        
        if options.page_size == "CUSTOM" and options.custom_width and options.custom_height:
            width, height = options.custom_width, options.custom_height
        else:
            width, height = page_sizes.get(options.page_size, page_sizes["A4"])
            
        # Apply orientation
        if options.orientation == "landscape":
            width, height = height, width
            
        # Convert to specified units
        if options.units == "inch":
            width /= 25.4
            height /= 25.4
        elif options.units == "px":
            # Assume 96 DPI
            width = width * 96 / 25.4
            height = height * 96 / 25.4
            
        return width, height
        
    def calculate_scale_and_offset(self, bounds: ExportBounds, options: ExportOptions) -> Tuple[float, float, float]:
        """Calculate scale factor and offset to fit content on page."""
        page_width, page_height = self.get_page_size(options)
        
        # Account for margins
        usable_width = page_width - 2 * options.margin
        usable_height = page_height - 2 * options.margin
        
        # Calculate scale to fit
        scale_x = usable_width / bounds.width if bounds.width > 0 else 1.0
        scale_y = usable_height / bounds.height if bounds.height > 0 else 1.0
        scale = min(scale_x, scale_y) * options.scale_factor
        
        # Calculate offset to center content
        scaled_width = bounds.width * scale
        scaled_height = bounds.height * scale
        offset_x = (page_width - scaled_width) / 2 - bounds.min_x * scale
        offset_y = (page_height - scaled_height) / 2 - bounds.min_y * scale
        
        return scale, offset_x, offset_y
        
    def filter_entities(self, document: CADDocument, options: ExportOptions) -> List[BaseEntity]:
        """Filter entities based on export options."""
        filtered_entities = []
        
        for entity in document.entities:
            # Skip entities on excluded layers
            if entity.layer_id in options.exclude_layers:
                continue
                
            # Skip entities on non-included layers (if include list is specified)
            if options.include_layers and entity.layer_id not in options.include_layers:
                continue
                
            # Skip invisible entities
            if not entity.visible:
                continue
                
            filtered_entities.append(entity)
            
        return filtered_entities


class SVGExporter(BaseExporter):
    """Export CAD documents to SVG format."""
    
    def __init__(self):
        super().__init__()
        if not SVG_AVAILABLE:
            raise ImportError("svgwrite library is required for SVG export")
            
    def export(self, document: CADDocument, file_path: str, options: ExportOptions) -> bool:
        """Export document to SVG file."""
        try:
            bounds = self.calculate_bounds(document, options)
            scale, offset_x, offset_y = self.calculate_scale_and_offset(bounds, options)
            page_width, page_height = self.get_page_size(options)
            
            # Create SVG drawing
            dwg = svgwrite.Drawing(
                file_path,
                size=(f"{page_width}{options.units}", f"{page_height}{options.units}"),
                viewBox=f"0 0 {page_width} {page_height}"
            )
            
            # Add metadata
            dwg.add(dwg.title("CAD Export"))
            dwg.add(dwg.desc(f"Exported from PyCAD on {datetime.now().isoformat()}"))
            
            # Group entities by layer
            layer_groups = {}
            entities = self.filter_entities(document, options)
            
            for entity in entities:
                layer_id = entity.layer_id
                if layer_id not in layer_groups:
                    layer = document.get_layer(layer_id)
                    layer_name = layer.name if layer else f"Layer_{layer_id}"
                    layer_color = layer.color.to_hex() if layer else "#000000"
                    
                    layer_groups[layer_id] = dwg.g(
                        id=f"layer_{layer_name}",
                        stroke=layer_color,
                        fill="none",
                        stroke_width=options.line_width_scale
                    )
                    
                self._add_entity_to_svg(entity, layer_groups[layer_id], dwg, scale, offset_x, offset_y, options)
                
            # Add layer groups to drawing
            for group in layer_groups.values():
                dwg.add(group)
                
            # Save SVG
            dwg.save()
            logger.info(f"Successfully exported to SVG: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export to SVG: {e}")
            return False
            
    def _add_entity_to_svg(self, entity: BaseEntity, group, dwg, scale: float, offset_x: float, offset_y: float, options: ExportOptions):
        """Add a single entity to SVG group."""
        if isinstance(entity, LineEntity):
            # Transform coordinates
            x1 = entity.start_point.x * scale + offset_x
            y1 = entity.start_point.y * scale + offset_y
            x2 = entity.end_point.x * scale + offset_x
            y2 = entity.end_point.y * scale + offset_y
            
            group.add(dwg.line(
                start=(round(x1, options.precision), round(y1, options.precision)),
                end=(round(x2, options.precision), round(y2, options.precision))
            ))
            
        elif isinstance(entity, CircleEntity):
            # Transform coordinates
            cx = entity.center.x * scale + offset_x
            cy = entity.center.y * scale + offset_y
            r = entity.radius * scale
            
            group.add(dwg.circle(
                center=(round(cx, options.precision), round(cy, options.precision)),
                r=round(r, options.precision)
            ))
            
        elif isinstance(entity, ArcEntity):
            # Convert arc to SVG path
            cx = entity.center.x * scale + offset_x
            cy = entity.center.y * scale + offset_y
            r = entity.radius * scale
            
            # Calculate start and end points
            start_angle_rad = math.radians(entity.start_angle)
            end_angle_rad = math.radians(entity.end_angle)
            
            start_x = cx + r * math.cos(start_angle_rad)
            start_y = cy + r * math.sin(start_angle_rad)
            end_x = cx + r * math.cos(end_angle_rad)
            end_y = cy + r * math.sin(end_angle_rad)
            
            # Determine if arc is large arc
            angle_diff = end_angle_rad - start_angle_rad
            if angle_diff < 0:
                angle_diff += 2 * math.pi
            large_arc = 1 if angle_diff > math.pi else 0
            
            # Create SVG path
            path_data = f"M {start_x:.{options.precision}f} {start_y:.{options.precision}f} A {r:.{options.precision}f} {r:.{options.precision}f} 0 {large_arc} 1 {end_x:.{options.precision}f} {end_y:.{options.precision}f}"
            group.add(dwg.path(d=path_data))


class PDFExporter(BaseExporter):
    """Export CAD documents to PDF format."""
    
    def __init__(self):
        super().__init__()
        if not PDF_AVAILABLE:
            raise ImportError("reportlab library is required for PDF export")
            
    def export(self, document: CADDocument, file_path: str, options: ExportOptions) -> bool:
        """Export document to PDF file."""
        try:
            bounds = self.calculate_bounds(document, options)
            scale, offset_x, offset_y = self.calculate_scale_and_offset(bounds, options)
            page_width, page_height = self.get_page_size(options)
            
            # Convert to points (PDF units)
            if options.units == "mm":
                page_width *= 72 / 25.4
                page_height *= 72 / 25.4
                offset_x *= 72 / 25.4
                offset_y *= 72 / 25.4
                scale *= 72 / 25.4
            elif options.units == "inch":
                page_width *= 72
                page_height *= 72
                offset_x *= 72
                offset_y *= 72
                scale *= 72
                
            # Create PDF canvas
            c = canvas.Canvas(file_path, pagesize=(page_width, page_height))
            
            # Set metadata
            if options.pdf_metadata:
                c.setTitle(options.pdf_metadata.get("title", "CAD Export"))
                c.setAuthor(options.pdf_metadata.get("author", "PyCAD"))
                c.setSubject(options.pdf_metadata.get("subject", "CAD Drawing"))
                
            # Set coordinate system (PDF uses bottom-left origin, CAD uses top-left)
            c.translate(0, page_height)
            c.scale(1, -1)
            
            # Draw entities
            entities = self.filter_entities(document, options)
            
            for entity in entities:
                self._add_entity_to_pdf(entity, c, document, scale, offset_x, offset_y, options)
                
            # Save PDF
            c.save()
            logger.info(f"Successfully exported to PDF: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export to PDF: {e}")
            return False
            
    def _add_entity_to_pdf(self, entity: BaseEntity, canvas_obj, document: CADDocument, scale: float, offset_x: float, offset_y: float, options: ExportOptions):
        """Add a single entity to PDF canvas."""
        # Get layer color
        layer = document.get_layer(entity.layer_id)
        if layer and layer.color:
            r, g, b = layer.color.red / 255, layer.color.green / 255, layer.color.blue / 255
            canvas_obj.setStrokeColorRGB(r, g, b)
        else:
            canvas_obj.setStrokeColorRGB(0, 0, 0)  # Default to black
            
        # Set line width
        canvas_obj.setLineWidth(options.line_width_scale)
        
        if isinstance(entity, LineEntity):
            # Transform coordinates
            x1 = entity.start_point.x * scale + offset_x
            y1 = entity.start_point.y * scale + offset_y
            x2 = entity.end_point.x * scale + offset_x
            y2 = entity.end_point.y * scale + offset_y
            
            canvas_obj.line(x1, y1, x2, y2)
            
        elif isinstance(entity, CircleEntity):
            # Transform coordinates
            cx = entity.center.x * scale + offset_x
            cy = entity.center.y * scale + offset_y
            r = entity.radius * scale
            
            canvas_obj.circle(cx, cy, r, stroke=1, fill=0)
            
        elif isinstance(entity, ArcEntity):
            # ReportLab doesn't have direct arc support, so draw using path
            cx = entity.center.x * scale + offset_x
            cy = entity.center.y * scale + offset_y
            r = entity.radius * scale
            
            # Convert to path by approximating with line segments
            start_angle_rad = math.radians(entity.start_angle)
            end_angle_rad = math.radians(entity.end_angle)
            
            # Calculate angle span
            angle_span = end_angle_rad - start_angle_rad
            if angle_span < 0:
                angle_span += 2 * math.pi
                
            # Number of segments based on angle span
            num_segments = max(8, int(angle_span * 180 / math.pi / 5))  # ~5 degrees per segment
            
            path = canvas_obj.beginPath()
            for i in range(num_segments + 1):
                angle = start_angle_rad + (angle_span * i / num_segments)
                x = cx + r * math.cos(angle)
                y = cy + r * math.sin(angle)
                
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
                    
            canvas_obj.drawPath(path, stroke=1, fill=0)


class ExportService:
    """Main export service that coordinates different export formats."""
    
    def __init__(self):
        self.exporters = {}
        
        # Register available exporters
        if SVG_AVAILABLE:
            self.exporters['svg'] = SVGExporter()
            
        if PDF_AVAILABLE:
            self.exporters['pdf'] = PDFExporter()
            
    def get_supported_formats(self) -> List[str]:
        """Get list of supported export formats."""
        return list(self.exporters.keys())
        
    def export_document(self, document: CADDocument, file_path: str, format_type: str, options: Optional[ExportOptions] = None) -> bool:
        """Export document to specified format."""
        if format_type.lower() not in self.exporters:
            logger.error(f"Unsupported export format: {format_type}")
            return False
            
        if options is None:
            options = ExportOptions()
            
        exporter = self.exporters[format_type.lower()]
        
        # Ensure output directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        return exporter.export(document, file_path, options)
        
    def get_export_options_template(self, format_type: str) -> Optional[ExportOptions]:
        """Get a template export options object for the specified format."""
        if format_type.lower() not in self.exporters:
            return None
            
        options = ExportOptions()
        
        # Set format-specific defaults
        if format_type.lower() == 'svg':
            options.units = "mm"
            options.svg_embed_fonts = True
        elif format_type.lower() == 'pdf':
            options.units = "mm"
            options.pdf_compression = True
            options.pdf_metadata = {
                "title": "CAD Drawing",
                "author": "PyCAD",
                "subject": "Technical Drawing"
            }
            
        return options