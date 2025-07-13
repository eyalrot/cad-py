"""Dimension service implementation."""

import logging
from typing import Any, Dict, List, Optional

from backend.models import (
    Color,
    Dimension,
    DimensionPoint,
    DimensionStyle,
    DimensionType,
)

from .converters import ProtobufConverters
from .document_service import DocumentService

logger = logging.getLogger(__name__)


class DimensionService:
    """Service for dimension operations."""

    def __init__(self, document_service: DocumentService):
        self.document_service = document_service
        self._dimension_styles: Dict[str, DimensionStyle] = {}
        self._create_default_styles()

    def _create_default_styles(self):
        """Create default dimension styles."""
        # Standard style
        standard = DimensionStyle("Standard")
        self._dimension_styles[standard.id] = standard

        # Architectural style
        architectural = DimensionStyle("Architectural")
        architectural.text_height = 3.0
        architectural.arrow_size = 3.0
        architectural.unit_format = "architectural"
        self._dimension_styles[architectural.id] = architectural

        # Engineering style
        engineering = DimensionStyle("Engineering")
        engineering.text_height = 2.0
        engineering.arrow_size = 2.0
        engineering.precision = 3
        self._dimension_styles[engineering.id] = engineering

    def create_dimension(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new dimension in a document."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )

            document = self.document_service.get_document(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )

            # Parse dimension data
            dimension_type_str = request.get("dimension_type", "")
            if not dimension_type_str:
                return ProtobufConverters.create_error_response(
                    error_message="Dimension type is required"
                )

            try:
                dimension_type = DimensionType(dimension_type_str)
            except ValueError:
                return ProtobufConverters.create_error_response(
                    error_message=f"Invalid dimension type: {dimension_type_str}"
                )

            # Parse points
            points_data = request.get("points", [])
            if len(points_data) < 2:
                return ProtobufConverters.create_error_response(
                    error_message="At least 2 points are required for dimension"
                )

            points = []
            for point_data in points_data:
                if isinstance(point_data, (list, tuple)) and len(point_data) >= 2:
                    x, y = point_data[0], point_data[1]
                    z = point_data[2] if len(point_data) > 2 else 0.0
                    points.append(DimensionPoint(x, y, z))
                else:
                    return ProtobufConverters.create_error_response(
                        error_message="Invalid point data format"
                    )

            # Get layer ID
            layer_id = request.get("layer_id", "")
            if not layer_id:
                # Use current layer
                layer_id = document.current_layer_id or "0"

            # Get or create dimension style
            style_id = request.get("style_id")
            style = None
            if style_id and style_id in self._dimension_styles:
                style = self._dimension_styles[style_id]
            else:
                style = DimensionStyle()  # Use default style

            # Create dimension
            dimension = Dimension(dimension_type, points, layer_id, style)

            # Apply any custom properties
            if "text_override" in request:
                dimension.set_text_override(request["text_override"])

            # Add dimension to document (extending document model would be needed)
            # For now, we'll simulate this
            dimension_id = dimension.id

            logger.info(f"Created dimension {dimension_id} in document {document_id}")

            return ProtobufConverters.create_success_response(
                {"dimension": self._dimension_to_proto(dimension)}
            )

        except ValueError as e:
            logger.warning(f"Validation error creating dimension: {e}")
            return ProtobufConverters.create_error_response(error_message=str(e))
        except Exception as e:
            logger.error(f"Error creating dimension: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to create dimension: {str(e)}"
            )

    def update_dimension(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Update dimension properties."""
        try:
            document_id = request.get("document_id", "")
            dimension_id = request.get("dimension_id", "")

            if not document_id or not dimension_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID and Dimension ID are required"
                )

            document = self.document_service.get_document(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )

            # For now, create a mock dimension to demonstrate the update process
            # In a real implementation, we'd retrieve the dimension from document
            points = [DimensionPoint(0, 0), DimensionPoint(100, 0)]
            dimension = Dimension(DimensionType.HORIZONTAL, points, "0")
            dimension.id = dimension_id

            # Update properties if provided
            if "points" in request:
                points_data = request["points"]
                new_points = []
                for point_data in points_data:
                    if isinstance(point_data, (list, tuple)) and len(point_data) >= 2:
                        x, y = point_data[0], point_data[1]
                        z = point_data[2] if len(point_data) > 2 else 0.0
                        new_points.append(DimensionPoint(x, y, z))
                dimension.update_points(new_points)

            if "text_override" in request:
                dimension.set_text_override(request["text_override"])

            if "style_id" in request:
                style_id = request["style_id"]
                if style_id in self._dimension_styles:
                    dimension.set_style(self._dimension_styles[style_id])

            logger.info(f"Updated dimension {dimension_id} in document {document_id}")

            return ProtobufConverters.create_success_response(
                {"dimension": self._dimension_to_proto(dimension)}
            )

        except ValueError as e:
            logger.warning(f"Validation error updating dimension: {e}")
            return ProtobufConverters.create_error_response(error_message=str(e))
        except Exception as e:
            logger.error(f"Error updating dimension: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to update dimension: {str(e)}"
            )

    def delete_dimension(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a dimension from a document."""
        try:
            document_id = request.get("document_id", "")
            dimension_id = request.get("dimension_id", "")

            if not document_id or not dimension_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID and Dimension ID are required"
                )

            document = self.document_service.get_document(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )

            # In a real implementation, we'd remove the dimension from document
            # For now, we'll just simulate success
            logger.info(f"Deleted dimension {dimension_id} from document {document_id}")

            return ProtobufConverters.create_success_response()

        except Exception as e:
            logger.error(f"Error deleting dimension: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to delete dimension: {str(e)}"
            )

    def list_dimensions(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """List all dimensions in a document."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )

            document = self.document_service.get_document(document_id)
            if not document:
                return ProtobufConverters.create_error_response(
                    error_message=f"Document {document_id} not found"
                )

            # In a real implementation, we'd get dimensions from document
            # For now, return empty list
            dimensions = []

            return ProtobufConverters.create_success_response(
                {"dimensions": [self._dimension_to_proto(dim) for dim in dimensions]}
            )

        except Exception as e:
            logger.error(f"Error listing dimensions: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to list dimensions: {str(e)}"
            )

    def create_dimension_style(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new dimension style."""
        try:
            name = request.get("name", "")
            if not name:
                return ProtobufConverters.create_error_response(
                    error_message="Style name is required"
                )

            # Check if style name already exists
            for style in self._dimension_styles.values():
                if style.name == name:
                    return ProtobufConverters.create_error_response(
                        error_message=f"Style '{name}' already exists"
                    )

            # Create new style
            style = DimensionStyle(name)

            # Apply any provided properties
            if "text_height" in request:
                style.text_height = float(request["text_height"])
            if "arrow_size" in request:
                style.arrow_size = float(request["arrow_size"])
            if "precision" in request:
                style.precision = int(request["precision"])
            if "unit_format" in request:
                style.unit_format = request["unit_format"]

            self._dimension_styles[style.id] = style

            logger.info(f"Created dimension style '{name}' with ID {style.id}")

            return ProtobufConverters.create_success_response(
                {"style": self._dimension_style_to_proto(style)}
            )

        except ValueError as e:
            logger.warning(f"Validation error creating dimension style: {e}")
            return ProtobufConverters.create_error_response(error_message=str(e))
        except Exception as e:
            logger.error(f"Error creating dimension style: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to create dimension style: {str(e)}"
            )

    def list_dimension_styles(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """List all available dimension styles."""
        try:
            styles = list(self._dimension_styles.values())

            return ProtobufConverters.create_success_response(
                {"styles": [self._dimension_style_to_proto(style) for style in styles]}
            )

        except Exception as e:
            logger.error(f"Error listing dimension styles: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to list dimension styles: {str(e)}"
            )

    def _dimension_to_proto(self, dimension: Dimension) -> Dict[str, Any]:
        """Convert dimension to protobuf format."""
        return {
            "id": dimension.id,
            "dimension_type": dimension.dimension_type.value,
            "points": [point.to_tuple() for point in dimension.points],
            "layer_id": dimension.layer_id,
            "measurement_value": dimension.measurement_value,
            "formatted_text": dimension.get_formatted_text(),
            "text_override": dimension.text_override,
            "text_position": dimension.text_position.to_tuple()
            if dimension.text_position
            else None,
            "style": self._dimension_style_to_proto(dimension.style),
            "visible": dimension.visible,
            "locked": dimension.locked,
            "selected": dimension.selected,
            "created_at": dimension.created_at.isoformat(),
            "modified_at": dimension.modified_at.isoformat(),
        }

    def _dimension_style_to_proto(self, style: DimensionStyle) -> Dict[str, Any]:
        """Convert dimension style to protobuf format."""
        return {
            "id": style.id,
            "name": style.name,
            "text_height": style.text_height,
            "text_color": {
                "red": style.text_color.red,
                "green": style.text_color.green,
                "blue": style.text_color.blue,
                "alpha": style.text_color.alpha,
            },
            "text_font": style.text_font,
            "text_offset": style.text_offset,
            "arrow_type": style.arrow_type.value,
            "arrow_size": style.arrow_size,
            "line_color": {
                "red": style.line_color.red,
                "green": style.line_color.green,
                "blue": style.line_color.blue,
                "alpha": style.line_color.alpha,
            },
            "line_weight": style.line_weight,
            "extension_line_offset": style.extension_line_offset,
            "extension_line_extension": style.extension_line_extension,
            "dimension_line_gap": style.dimension_line_gap,
            "precision": style.precision,
            "unit_format": style.unit_format.value,
            "unit_suffix": style.unit_suffix,
            "scale_factor": style.scale_factor,
            "suppress_zeros": style.suppress_zeros,
            "show_tolerances": style.show_tolerances,
            "tolerance_upper": style.tolerance_upper,
            "tolerance_lower": style.tolerance_lower,
        }
