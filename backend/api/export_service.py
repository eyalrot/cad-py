"""Export API service implementation."""

import logging
import os
from typing import Any, Dict, List, Optional

from backend.services.export_service import ExportService, ExportOptions
from .converters import ProtobufConverters
from .document_service import DocumentService

logger = logging.getLogger(__name__)


class ExportAPIService:
    """API service for document export operations."""

    def __init__(self, document_service: DocumentService):
        self.document_service = document_service
        self.export_service = ExportService()

    def get_supported_formats(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of supported export formats."""
        try:
            formats = self.export_service.get_supported_formats()
            
            # Add format details
            format_details = []
            for fmt in formats:
                details = {
                    "format": fmt,
                    "name": fmt.upper(),
                    "description": self._get_format_description(fmt),
                    "extensions": self._get_format_extensions(fmt),
                    "supports_layers": True,
                    "supports_scaling": True,
                    "vector_format": True
                }
                format_details.append(details)
            
            return ProtobufConverters.create_success_response({
                "supported_formats": format_details
            })
            
        except Exception as e:
            logger.error(f"Error getting supported formats: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to get supported formats: {str(e)}"
            )

    def export_document(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Export a document to specified format."""
        try:
            # Validate required parameters
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )

            file_path = request.get("file_path", "")
            if not file_path:
                return ProtobufConverters.create_error_response(
                    error_message="File path is required"
                )

            format_type = request.get("format", "").lower()
            if not format_type:
                return ProtobufConverters.create_error_response(
                    error_message="Export format is required"
                )

            # Check if format is supported
            supported_formats = self.export_service.get_supported_formats()
            if format_type not in supported_formats:
                return ProtobufConverters.create_error_response(
                    error_message=f"Unsupported format: {format_type}. Supported: {', '.join(supported_formats)}"
                )

            # Get document
            document = self.document_service.get_document(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )

            # Parse export options
            options = self._parse_export_options(request.get("options", {}))

            # Validate file path
            if not self._validate_file_path(file_path, format_type):
                return ProtobufConverters.create_error_response(
                    error_message="Invalid file path or insufficient permissions"
                )

            # Perform export
            success = self.export_service.export_document(
                document, file_path, format_type, options
            )

            if success:
                # Get file info for response
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                
                return ProtobufConverters.create_success_response({
                    "export_info": {
                        "file_path": file_path,
                        "format": format_type,
                        "file_size": file_size,
                        "entity_count": len(document.entities),
                        "layer_count": len(document.layers)
                    }
                })
            else:
                return ProtobufConverters.create_error_response(
                    error_message="Export operation failed"
                )

        except Exception as e:
            logger.error(f"Error exporting document: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to export document: {str(e)}"
            )

    def get_export_options(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Get available export options for a format."""
        try:
            format_type = request.get("format", "").lower()
            if not format_type:
                return ProtobufConverters.create_error_response(
                    error_message="Format is required"
                )

            # Check if format is supported
            supported_formats = self.export_service.get_supported_formats()
            if format_type not in supported_formats:
                return ProtobufConverters.create_error_response(
                    error_message=f"Unsupported format: {format_type}"
                )

            # Get template options
            options_template = self.export_service.get_export_options_template(format_type)
            if not options_template:
                return ProtobufConverters.create_error_response(
                    error_message=f"No options template available for format: {format_type}"
                )

            # Convert to response format
            options_dict = {
                "page_sizes": ["A0", "A1", "A2", "A3", "A4", "LETTER", "LEGAL", "CUSTOM"],
                "orientations": ["portrait", "landscape"],
                "units": ["mm", "inch", "px"],
                "default_options": {
                    "page_size": options_template.page_size,
                    "orientation": options_template.orientation,
                    "units": options_template.units,
                    "scale_factor": options_template.scale_factor,
                    "margin": options_template.margin,
                    "line_width_scale": options_template.line_width_scale,
                    "precision": options_template.precision
                }
            }

            # Add format-specific options
            if format_type == "svg":
                options_dict["svg_options"] = {
                    "embed_fonts": options_template.svg_embed_fonts
                }
            elif format_type == "pdf":
                options_dict["pdf_options"] = {
                    "compression": options_template.pdf_compression,
                    "metadata": options_template.pdf_metadata
                }

            return ProtobufConverters.create_success_response({
                "export_options": options_dict
            })

        except Exception as e:
            logger.error(f"Error getting export options: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to get export options: {str(e)}"
            )

    def preview_export(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Generate export preview information."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )

            # Get document
            document = self.document_service.get_document(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )

            # Parse export options
            options = self._parse_export_options(request.get("options", {}))

            # Calculate preview information
            from backend.services.export_service import BaseExporter
            exporter = BaseExporter()
            
            bounds = exporter.calculate_bounds(document, options)
            scale, offset_x, offset_y = exporter.calculate_scale_and_offset(bounds, options)
            page_width, page_height = exporter.get_page_size(options)
            
            # Filter entities to get count
            filtered_entities = exporter.filter_entities(document, options)

            preview_info = {
                "bounds": {
                    "min_x": bounds.min_x,
                    "min_y": bounds.min_y,
                    "max_x": bounds.max_x,
                    "max_y": bounds.max_y,
                    "width": bounds.width,
                    "height": bounds.height
                },
                "page": {
                    "width": page_width,
                    "height": page_height,
                    "units": options.units
                },
                "transform": {
                    "scale": scale,
                    "offset_x": offset_x,
                    "offset_y": offset_y
                },
                "entity_count": len(filtered_entities),
                "layer_count": len(set(e.layer_id for e in filtered_entities))
            }

            return ProtobufConverters.create_success_response({
                "preview": preview_info
            })

        except Exception as e:
            logger.error(f"Error generating export preview: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to generate preview: {str(e)}"
            )

    def _parse_export_options(self, options_dict: Dict[str, Any]) -> ExportOptions:
        """Parse export options from request."""
        options = ExportOptions()
        
        # General options
        if "include_layers" in options_dict:
            options.include_layers = options_dict["include_layers"]
        if "exclude_layers" in options_dict:
            options.exclude_layers = options_dict["exclude_layers"]
        if "scale_factor" in options_dict:
            options.scale_factor = float(options_dict["scale_factor"])
        if "units" in options_dict:
            options.units = options_dict["units"]
            
        # Page options
        if "page_size" in options_dict:
            options.page_size = options_dict["page_size"]
        if "orientation" in options_dict:
            options.orientation = options_dict["orientation"]
        if "custom_width" in options_dict:
            options.custom_width = float(options_dict["custom_width"])
        if "custom_height" in options_dict:
            options.custom_height = float(options_dict["custom_height"])
        if "margin" in options_dict:
            options.margin = float(options_dict["margin"])
            
        # Quality options
        if "line_width_scale" in options_dict:
            options.line_width_scale = float(options_dict["line_width_scale"])
        if "text_scale" in options_dict:
            options.text_scale = float(options_dict["text_scale"])
        if "precision" in options_dict:
            options.precision = int(options_dict["precision"])
            
        # Format-specific options
        if "svg_embed_fonts" in options_dict:
            options.svg_embed_fonts = bool(options_dict["svg_embed_fonts"])
        if "pdf_compression" in options_dict:
            options.pdf_compression = bool(options_dict["pdf_compression"])
        if "pdf_metadata" in options_dict:
            options.pdf_metadata = options_dict["pdf_metadata"]
            
        return options

    def _validate_file_path(self, file_path: str, format_type: str) -> bool:
        """Validate file path and permissions."""
        try:
            # Check if directory exists and is writable
            directory = os.path.dirname(file_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # Check if we can write to the directory
            if directory:
                return os.access(directory, os.W_OK)
            else:
                return os.access(".", os.W_OK)
                
        except Exception:
            return False

    def _get_format_description(self, format_type: str) -> str:
        """Get description for export format."""
        descriptions = {
            "svg": "Scalable Vector Graphics - Web-compatible vector format",
            "pdf": "Portable Document Format - Print-ready document format"
        }
        return descriptions.get(format_type, f"{format_type.upper()} format")

    def _get_format_extensions(self, format_type: str) -> List[str]:
        """Get file extensions for export format."""
        extensions = {
            "svg": [".svg"],
            "pdf": [".pdf"]
        }
        return extensions.get(format_type, [f".{format_type}"])