"""Base entity model for CAD system."""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar

T = TypeVar("T", bound="BaseEntity")


@dataclass
class EntityFilter:
    """Filter for querying entities."""

    entity_types: Optional[List[str]] = None
    layer_ids: Optional[List[str]] = None
    visible_only: bool = True
    locked_only: Optional[bool] = None
    bbox: Optional["BoundingBox"] = None
    properties: Optional[Dict[str, Any]] = None


class BaseEntity(ABC):
    """Abstract base class for all CAD entities."""

    def __init__(
        self, layer_id: str, properties: Optional[Dict[str, Any]] = None
    ) -> None:
        self.id: str = str(uuid.uuid4())
        self.layer_id: str = layer_id
        self.properties: Dict[str, Any] = properties or {}
        self.created_at: datetime = datetime.utcnow()
        self.modified_at: datetime = datetime.utcnow()
        self.visible: bool = True
        self.locked: bool = False

    @property
    @abstractmethod
    def entity_type(self) -> str:
        """Return the entity type identifier."""
        pass

    @abstractmethod
    def get_bounding_box(self) -> Optional["BoundingBox"]:
        """Return the bounding box of the entity."""
        pass

    @abstractmethod
    def transform(self, matrix: "TransformMatrix") -> None:
        """Apply transformation to the entity."""
        pass

    @abstractmethod
    def copy(self) -> "BaseEntity":
        """Create a copy of the entity."""
        pass

    def serialize(self) -> Dict[str, Any]:
        """Serialize entity to dictionary format."""
        return {
            "id": self.id,
            "entity_type": self.entity_type,
            "layer_id": self.layer_id,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "visible": self.visible,
            "locked": self.locked,
            "geometry": self._serialize_geometry(),
        }

    @classmethod
    def deserialize(cls: Type[T], data: Dict[str, Any]) -> T:
        """Deserialize entity from dictionary format."""
        entity = cls._create_from_geometry(data.get("geometry", {}))
        entity.id = data["id"]
        entity.layer_id = data["layer_id"]
        entity.properties = data.get("properties", {})
        entity.created_at = datetime.fromisoformat(data["created_at"])
        entity.modified_at = datetime.fromisoformat(data["modified_at"])
        entity.visible = data.get("visible", True)
        entity.locked = data.get("locked", False)
        return entity

    @abstractmethod
    def _serialize_geometry(self) -> Dict[str, Any]:
        """Serialize entity-specific geometry data."""
        pass

    @classmethod
    @abstractmethod
    def _create_from_geometry(cls: Type[T], geometry_data: Dict[str, Any]) -> T:
        """Create entity from geometry data."""
        pass

    def update_properties(self, **kwargs: Any) -> None:
        """Update entity properties."""
        self.properties.update(kwargs)
        self.modified_at = datetime.utcnow()

    def set_layer(self, layer_id: str) -> None:
        """Move entity to different layer."""
        self.layer_id = layer_id
        self.modified_at = datetime.utcnow()

    def set_visibility(self, visible: bool) -> None:
        """Set entity visibility."""
        self.visible = visible
        self.modified_at = datetime.utcnow()

    def set_locked(self, locked: bool) -> None:
        """Set entity lock state."""
        self.locked = locked
        self.modified_at = datetime.utcnow()

    def matches_filter(self, filter_obj: EntityFilter) -> bool:
        """Check if entity matches the given filter."""
        if filter_obj.entity_types and self.entity_type not in filter_obj.entity_types:
            return False

        if filter_obj.layer_ids and self.layer_id not in filter_obj.layer_ids:
            return False

        if filter_obj.visible_only and not self.visible:
            return False

        if filter_obj.locked_only is not None and self.locked != filter_obj.locked_only:
            return False

        if filter_obj.bbox:
            entity_bbox = self.get_bounding_box()
            if not entity_bbox or not filter_obj.bbox.intersects(entity_bbox):
                return False

        if filter_obj.properties:
            for key, value in filter_obj.properties.items():
                if key not in self.properties or self.properties[key] != value:
                    return False

        return True

    def __eq__(self, other: object) -> bool:
        """Check equality based on entity ID."""
        if not isinstance(other, BaseEntity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on entity ID."""
        return hash(self.id)

    def __repr__(self) -> str:
        """String representation of entity."""
        return f"{self.__class__.__name__}(id={self.id[:8]}..., layer={self.layer_id})"
