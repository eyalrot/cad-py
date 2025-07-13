"""Converters between domain models and protobuf messages."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.models import BaseEntity, CADDocument, Color, EntityFilter, Layer, LineType


class ProtobufConverters:
    """Converts between domain models and protobuf messages."""

    @staticmethod
    def color_to_proto(color: Color) -> Dict[str, int]:
        """Convert Color to protobuf format."""
        return {
            "red": color.red,
            "green": color.green,
            "blue": color.blue,
            "alpha": color.alpha,
        }

    @staticmethod
    def color_from_proto(proto_color: Dict[str, int]) -> Color:
        """Convert protobuf color to Color."""
        return Color(
            red=proto_color.get("red", 0),
            green=proto_color.get("green", 0),
            blue=proto_color.get("blue", 0),
            alpha=proto_color.get("alpha", 255),
        )

    @staticmethod
    def line_type_to_proto(line_type: LineType) -> str:
        """Convert LineType enum to protobuf format."""
        line_type_mapping = {
            LineType.CONTINUOUS: "CONTINUOUS",
            LineType.DASHED: "DASHED",
            LineType.DOTTED: "DOTTED",
            LineType.DASH_DOT: "DASH_DOT",
            LineType.DASH_DOT_DOT: "DASH_DOT_DOT",
            LineType.CENTER: "CENTER",
            LineType.PHANTOM: "PHANTOM",
            LineType.HIDDEN: "HIDDEN",
        }
        return line_type_mapping.get(line_type, "CONTINUOUS")

    @staticmethod
    def line_type_from_proto(proto_line_type: str) -> LineType:
        """Convert protobuf line type to LineType enum."""
        line_type_mapping = {
            "CONTINUOUS": LineType.CONTINUOUS,
            "DASHED": LineType.DASHED,
            "DOTTED": LineType.DOTTED,
            "DASH_DOT": LineType.DASH_DOT,
            "DASH_DOT_DOT": LineType.DASH_DOT_DOT,
            "CENTER": LineType.CENTER,
            "PHANTOM": LineType.PHANTOM,
            "HIDDEN": LineType.HIDDEN,
        }
        return line_type_mapping.get(proto_line_type, LineType.CONTINUOUS)

    @staticmethod
    def layer_to_proto(layer: Layer) -> Dict[str, Any]:
        """Convert Layer to protobuf format."""
        return {
            "id": layer.id,
            "name": layer.name,
            "color": ProtobufConverters.color_to_proto(layer.color),
            "line_type": ProtobufConverters.line_type_to_proto(layer.line_type),
            "line_weight": layer.line_weight,
            "visible": layer.visible,
            "locked": layer.locked,
            "printable": layer.printable,
            "frozen": layer.frozen,
            "description": layer.description,
            "properties": layer.properties,
            "created_at": layer.created_at.isoformat(),
            "modified_at": layer.modified_at.isoformat(),
        }

    @staticmethod
    def layer_from_proto(proto_layer: Dict[str, Any]) -> Layer:
        """Convert protobuf layer to Layer."""
        color = ProtobufConverters.color_from_proto(proto_layer.get("color", {}))
        line_type = ProtobufConverters.line_type_from_proto(
            proto_layer.get("line_type", "CONTINUOUS")
        )

        layer = Layer(
            name=proto_layer.get("name", ""),
            color=color,
            line_type=line_type,
            line_weight=proto_layer.get("line_weight", 0.25),
        )

        # Set additional properties if present
        if "id" in proto_layer:
            layer.id = proto_layer["id"]
        if "visible" in proto_layer:
            layer.visible = proto_layer["visible"]
        if "locked" in proto_layer:
            layer.locked = proto_layer["locked"]
        if "printable" in proto_layer:
            layer.printable = proto_layer["printable"]
        if "frozen" in proto_layer:
            layer.frozen = proto_layer["frozen"]
        if "description" in proto_layer:
            layer.description = proto_layer["description"]
        if "properties" in proto_layer:
            layer.properties = dict(proto_layer["properties"])
        if "created_at" in proto_layer:
            layer.created_at = datetime.fromisoformat(proto_layer["created_at"])
        if "modified_at" in proto_layer:
            layer.modified_at = datetime.fromisoformat(proto_layer["modified_at"])

        return layer

    @staticmethod
    def document_to_proto(document: CADDocument) -> Dict[str, Any]:
        """Convert CADDocument to protobuf format."""
        return {
            "id": document.id,
            "name": document.name,
            "version": document.version,
            "description": document.description,
            "metadata": document.metadata,
            "created_at": document.created_at.isoformat(),
            "modified_at": document.modified_at.isoformat(),
            "current_layer_id": document.current_layer_id,
            "layer_count": len(document.list_layers()),
            "entity_count": document.count_entities(),
        }

    @staticmethod
    def document_statistics_to_proto(document: CADDocument) -> Dict[str, Any]:
        """Convert document statistics to protobuf format."""
        stats = document.get_statistics()
        return {
            "name": stats["name"],
            "created_at": stats["created_at"],
            "modified_at": stats["modified_at"],
            "layer_count": stats["layer_count"],
            "entity_count": stats["entity_count"],
            "entities_by_layer": stats["entities_by_layer"],
        }

    @staticmethod
    def entity_filter_from_proto(proto_filter: Dict[str, Any]) -> EntityFilter:
        """Convert protobuf entity filter to EntityFilter."""
        return EntityFilter(
            entity_types=list(proto_filter.get("entity_types", [])),
            layer_ids=list(proto_filter.get("layer_ids", [])),
            visible_only=proto_filter.get("visible_only", True),
            locked_only=proto_filter.get("locked_only"),
            bbox=None,  # TODO: Implement bbox conversion
            properties=dict(proto_filter.get("properties", {})),
        )

    @staticmethod
    def point_to_proto(x: float, y: float) -> Dict[str, float]:
        """Convert point coordinates to protobuf format."""
        return {"x": x, "y": y}

    @staticmethod
    def point_from_proto(proto_point: Dict[str, float]) -> tuple[float, float]:
        """Convert protobuf point to coordinates."""
        return proto_point.get("x", 0.0), proto_point.get("y", 0.0)

    @staticmethod
    def create_error_response(
        success: bool = False, error_message: str = ""
    ) -> Dict[str, Any]:
        """Create a standardized error response."""
        return {"success": success, "error_message": error_message}

    @staticmethod
    def create_success_response(
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a standardized success response."""
        response = {"success": True, "error_message": ""}
        if data:
            response.update(data)
        return response
