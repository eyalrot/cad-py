"""Drawing service implementation for convenience drawing operations."""

import logging
from typing import Any, Dict

from .converters import ProtobufConverters
from .document_service import DocumentService
from .entity_service import EntityService

logger = logging.getLogger(__name__)


class DrawingService:
    """Service for convenience drawing operations."""

    def __init__(
        self, document_service: DocumentService, entity_service: EntityService
    ):
        self.document_service = document_service
        self.entity_service = entity_service

    def draw_line(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Draw a line entity."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )

            start_point = request.get("start")
            end_point = request.get("end")

            if not start_point or not end_point:
                return ProtobufConverters.create_error_response(
                    error_message="Start and end points are required"
                )

            # Extract point coordinates
            start_x, start_y = ProtobufConverters.point_from_proto(start_point)
            end_x, end_y = ProtobufConverters.point_from_proto(end_point)

            # Create line geometry
            line_geometry = {
                "line": {
                    "start": {"x": start_x, "y": start_y},
                    "end": {"x": end_x, "y": end_y},
                }
            }

            # Prepare entity creation request
            entity_request = {
                "document_id": document_id,
                "entity_type": "line",
                "layer_id": request.get("layer_id"),
                "geometry": line_geometry,
                "properties": dict(request.get("properties", {})),
            }

            # Create the entity
            result = self.entity_service.create_entity(entity_request)

            logger.info(
                f"Drew line from ({start_x}, {start_y}) to ({end_x}, {end_y}) in document {document_id}"
            )

            return result

        except Exception as e:
            logger.error(f"Error drawing line: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to draw line: {str(e)}"
            )

    def draw_circle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Draw a circle entity."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )

            center_point = request.get("center")
            radius = request.get("radius")

            if not center_point or radius is None:
                return ProtobufConverters.create_error_response(
                    error_message="Center point and radius are required"
                )

            if radius <= 0:
                return ProtobufConverters.create_error_response(
                    error_message="Radius must be positive"
                )

            # Extract center coordinates
            center_x, center_y = ProtobufConverters.point_from_proto(center_point)

            # Create circle geometry
            circle_geometry = {
                "circle": {"center": {"x": center_x, "y": center_y}, "radius": radius}
            }

            # Prepare entity creation request
            entity_request = {
                "document_id": document_id,
                "entity_type": "circle",
                "layer_id": request.get("layer_id"),
                "geometry": circle_geometry,
                "properties": dict(request.get("properties", {})),
            }

            # Create the entity
            result = self.entity_service.create_entity(entity_request)

            logger.info(
                f"Drew circle at ({center_x}, {center_y}) with radius {radius} in document {document_id}"
            )

            return result

        except Exception as e:
            logger.error(f"Error drawing circle: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to draw circle: {str(e)}"
            )

    def draw_arc(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Draw an arc entity."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )

            center_point = request.get("center")
            radius = request.get("radius")
            start_angle = request.get("start_angle")
            end_angle = request.get("end_angle")

            if (
                not center_point
                or radius is None
                or start_angle is None
                or end_angle is None
            ):
                return ProtobufConverters.create_error_response(
                    error_message="Center point, radius, start angle, and end angle are required"
                )

            if radius <= 0:
                return ProtobufConverters.create_error_response(
                    error_message="Radius must be positive"
                )

            # Extract center coordinates
            center_x, center_y = ProtobufConverters.point_from_proto(center_point)

            # Create arc geometry
            arc_geometry = {
                "arc": {
                    "center": {"x": center_x, "y": center_y},
                    "radius": radius,
                    "start_angle": start_angle,
                    "end_angle": end_angle,
                }
            }

            # Prepare entity creation request
            entity_request = {
                "document_id": document_id,
                "entity_type": "arc",
                "layer_id": request.get("layer_id"),
                "geometry": arc_geometry,
                "properties": dict(request.get("properties", {})),
            }

            # Create the entity
            result = self.entity_service.create_entity(entity_request)

            logger.info(
                f"Drew arc at ({center_x}, {center_y}) with radius {radius} from {start_angle}° to {end_angle}° in document {document_id}"
            )

            return result

        except Exception as e:
            logger.error(f"Error drawing arc: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to draw arc: {str(e)}"
            )

    def draw_rectangle(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Draw a rectangle entity."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )

            corner1 = request.get("corner1")
            corner2 = request.get("corner2")

            if not corner1 or not corner2:
                return ProtobufConverters.create_error_response(
                    error_message="Both corner points are required"
                )

            # Extract corner coordinates
            x1, y1 = ProtobufConverters.point_from_proto(corner1)
            x2, y2 = ProtobufConverters.point_from_proto(corner2)

            # Create rectangle geometry
            rectangle_geometry = {
                "rectangle": {
                    "corner1": {"x": x1, "y": y1},
                    "corner2": {"x": x2, "y": y2},
                }
            }

            # Prepare entity creation request
            entity_request = {
                "document_id": document_id,
                "entity_type": "rectangle",
                "layer_id": request.get("layer_id"),
                "geometry": rectangle_geometry,
                "properties": dict(request.get("properties", {})),
            }

            # Create the entity
            result = self.entity_service.create_entity(entity_request)

            logger.info(
                f"Drew rectangle from ({x1}, {y1}) to ({x2}, {y2}) in document {document_id}"
            )

            return result

        except Exception as e:
            logger.error(f"Error drawing rectangle: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to draw rectangle: {str(e)}"
            )

    def draw_polygon(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Draw a polygon entity."""
        try:
            document_id = request.get("document_id", "")
            if not document_id:
                return ProtobufConverters.create_error_response(
                    error_message="Document ID is required"
                )

            vertices = request.get("vertices", [])
            if len(vertices) < 3:
                return ProtobufConverters.create_error_response(
                    error_message="At least 3 vertices are required for a polygon"
                )

            closed = request.get("closed", True)

            # Extract vertex coordinates
            vertex_points = []
            for vertex in vertices:
                x, y = ProtobufConverters.point_from_proto(vertex)
                vertex_points.append({"x": x, "y": y})

            # Create polygon geometry
            polygon_geometry = {
                "polygon": {"vertices": vertex_points, "closed": closed}
            }

            # Prepare entity creation request
            entity_request = {
                "document_id": document_id,
                "entity_type": "polygon",
                "layer_id": request.get("layer_id"),
                "geometry": polygon_geometry,
                "properties": dict(request.get("properties", {})),
            }

            # Create the entity
            result = self.entity_service.create_entity(entity_request)

            logger.info(
                f"Drew polygon with {len(vertices)} vertices (closed: {closed}) in document {document_id}"
            )

            return result

        except Exception as e:
            logger.error(f"Error drawing polygon: {e}")
            return ProtobufConverters.create_error_response(
                error_message=f"Failed to draw polygon: {str(e)}"
            )
