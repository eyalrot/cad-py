"""CAD Document model."""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from .entity import BaseEntity, EntityFilter
from .layer import Color, Layer, LineType


class CADDocument:
    """CAD Document containing entities and layers."""

    def __init__(self, name: str) -> None:
        """Initialize CAD document.

        Args:
            name: Document name
        """
        if not name or not isinstance(name, str):
            raise ValueError("Document name must be a non-empty string")

        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.created_at: datetime = datetime.utcnow()
        self.modified_at: datetime = datetime.utcnow()
        self.version: str = "1.0"
        self.description: str = ""
        self.metadata: Dict[str, Any] = {}

        # Entity and layer storage
        self._entities: Dict[str, BaseEntity] = {}
        self._layers: Dict[str, Layer] = {}

        # Create default layer
        self._create_default_layer()

        # Current layer for new entities
        self._current_layer_id: str = list(self._layers.keys())[0]

    def _create_default_layer(self) -> None:
        """Create default layer 0."""
        default_layer = Layer(
            name="0", color=Layer.WHITE, line_type=LineType.CONTINUOUS
        )
        self._layers[default_layer.id] = default_layer

    @property
    def current_layer_id(self) -> str:
        """Get current layer ID."""
        return self._current_layer_id

    @property
    def current_layer(self) -> Layer:
        """Get current layer."""
        return self._layers[self._current_layer_id]

    def set_current_layer(self, layer_id: str) -> None:
        """Set current layer for new entities."""
        if layer_id not in self._layers:
            raise ValueError(f"Layer {layer_id} does not exist")
        self._current_layer_id = layer_id
        self.modified_at = datetime.utcnow()

    # Layer Management
    def add_layer(self, layer: Layer) -> str:
        """Add layer to document.

        Args:
            layer: Layer to add

        Returns:
            Layer ID

        Raises:
            ValueError: If layer name already exists
        """
        # Check for duplicate names
        for existing_layer in self._layers.values():
            if existing_layer.name == layer.name:
                raise ValueError(f"Layer name '{layer.name}' already exists")

        self._layers[layer.id] = layer
        self.modified_at = datetime.utcnow()
        return layer.id

    def remove_layer(self, layer_id: str) -> bool:
        """Remove layer from document.

        Args:
            layer_id: ID of layer to remove

        Returns:
            True if layer was removed, False if not found

        Raises:
            ValueError: If trying to remove layer with entities or last layer
        """
        if layer_id not in self._layers:
            return False

        # Check if layer has entities
        entities_on_layer = [
            e for e in self._entities.values() if e.layer_id == layer_id
        ]
        if entities_on_layer:
            raise ValueError(
                f"Cannot remove layer with {len(entities_on_layer)} entities"
            )

        # Check if it's the last layer
        if len(self._layers) == 1:
            raise ValueError("Cannot remove the last layer")

        # Update current layer if removing current
        if layer_id == self._current_layer_id:
            remaining_layers = [lid for lid in self._layers.keys() if lid != layer_id]
            self._current_layer_id = remaining_layers[0]

        del self._layers[layer_id]
        self.modified_at = datetime.utcnow()
        return True

    def get_layer(self, layer_id: str) -> Optional[Layer]:
        """Get layer by ID."""
        return self._layers.get(layer_id)

    def get_layer_by_name(self, name: str) -> Optional[Layer]:
        """Get layer by name."""
        for layer in self._layers.values():
            if layer.name == name:
                return layer
        return None

    def list_layers(self) -> List[Layer]:
        """Get all layers."""
        return list(self._layers.values())

    def rename_layer(self, layer_id: str, new_name: str) -> bool:
        """Rename layer.

        Args:
            layer_id: ID of layer to rename
            new_name: New layer name

        Returns:
            True if renamed successfully

        Raises:
            ValueError: If new name already exists
        """
        if layer_id not in self._layers:
            return False

        # Check for duplicate names
        for lid, layer in self._layers.items():
            if lid != layer_id and layer.name == new_name:
                raise ValueError(f"Layer name '{new_name}' already exists")

        self._layers[layer_id].rename(new_name)
        self.modified_at = datetime.utcnow()
        return True

    # Entity Management
    def add_entity(self, entity: BaseEntity) -> str:
        """Add entity to document.

        Args:
            entity: Entity to add

        Returns:
            Entity ID

        Raises:
            ValueError: If entity layer doesn't exist
        """
        if entity.layer_id not in self._layers:
            raise ValueError(f"Layer {entity.layer_id} does not exist")

        self._entities[entity.id] = entity
        self.modified_at = datetime.utcnow()
        return entity.id

    def remove_entity(self, entity_id: str) -> bool:
        """Remove entity from document.

        Args:
            entity_id: ID of entity to remove

        Returns:
            True if entity was removed, False if not found
        """
        if entity_id in self._entities:
            del self._entities[entity_id]
            self.modified_at = datetime.utcnow()
            return True
        return False

    def get_entity(self, entity_id: str) -> Optional[BaseEntity]:
        """Get entity by ID."""
        return self._entities.get(entity_id)

    def query_entities(
        self, filter_obj: Optional[EntityFilter] = None
    ) -> List[BaseEntity]:
        """Query entities with optional filter.

        Args:
            filter_obj: Filter criteria

        Returns:
            List of matching entities
        """
        entities = list(self._entities.values())

        if filter_obj:
            entities = [e for e in entities if e.matches_filter(filter_obj)]

        return entities

    def list_entities(self) -> List[BaseEntity]:
        """Get all entities."""
        return list(self._entities.values())

    def count_entities(self) -> int:
        """Get total entity count."""
        return len(self._entities)

    def count_entities_by_layer(self, layer_id: str) -> int:
        """Get entity count for specific layer."""
        return len([e for e in self._entities.values() if e.layer_id == layer_id])

    def move_entities_to_layer(
        self, entity_ids: List[str], target_layer_id: str
    ) -> int:
        """Move entities to different layer.

        Args:
            entity_ids: List of entity IDs to move
            target_layer_id: Target layer ID

        Returns:
            Number of entities moved

        Raises:
            ValueError: If target layer doesn't exist
        """
        if target_layer_id not in self._layers:
            raise ValueError(f"Target layer {target_layer_id} does not exist")

        moved_count = 0
        for entity_id in entity_ids:
            if entity_id in self._entities:
                self._entities[entity_id].set_layer(target_layer_id)
                moved_count += 1

        if moved_count > 0:
            self.modified_at = datetime.utcnow()

        return moved_count

    # Document Properties
    def set_name(self, name: str) -> None:
        """Set document name."""
        if not name or not isinstance(name, str):
            raise ValueError("Document name must be a non-empty string")
        self.name = name
        self.modified_at = datetime.utcnow()

    def set_description(self, description: str) -> None:
        """Set document description."""
        self.description = description
        self.modified_at = datetime.utcnow()

    def update_metadata(self, **kwargs: Any) -> None:
        """Update document metadata."""
        self.metadata.update(kwargs)
        self.modified_at = datetime.utcnow()

    # Serialization
    def serialize(self) -> Dict[str, Any]:
        """Serialize document to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "current_layer_id": self._current_layer_id,
            "layers": {lid: layer.serialize() for lid, layer in self._layers.items()},
            "entities": {
                eid: entity.serialize() for eid, entity in self._entities.items()
            },
        }

    def save_to_file(self, file_path: Union[str, Path]) -> None:
        """Save document to JSON file.

        Args:
            file_path: Path to save file
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.serialize(), f, indent=2, ensure_ascii=False)

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "CADDocument":
        """Deserialize document from dictionary.

        Note: This is a placeholder implementation. Full deserialization
        would require entity type registry for proper entity creation.
        """
        doc = cls(data["name"])
        doc.id = data["id"]
        doc.version = data.get("version", "1.0")
        doc.description = data.get("description", "")
        doc.metadata = data.get("metadata", {})
        doc.created_at = datetime.fromisoformat(data["created_at"])
        doc.modified_at = datetime.fromisoformat(data["modified_at"])

        # Clear default layer and load layers
        doc._layers.clear()
        for layer_data in data["layers"].values():
            layer = Layer.deserialize(layer_data)
            doc._layers[layer.id] = layer

        doc._current_layer_id = data.get(
            "current_layer_id", list(doc._layers.keys())[0]
        )

        # Load entities (placeholder - would need entity registry)
        # doc._entities = {}
        # for entity_data in data['entities'].values():
        #     entity = EntityRegistry.create_from_data(entity_data)
        #     doc._entities[entity.id] = entity

        return doc

    @classmethod
    def load_from_file(cls, file_path: Union[str, Path]) -> "CADDocument":
        """Load document from JSON file.

        Args:
            file_path: Path to load file

        Returns:
            Loaded CAD document
        """
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls.deserialize(data)

    # Statistics
    def get_statistics(self) -> Dict[str, Any]:
        """Get document statistics."""
        return {
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
            "layer_count": len(self._layers),
            "entity_count": len(self._entities),
            "entities_by_layer": {
                layer.name: self.count_entities_by_layer(layer.id)
                for layer in self._layers.values()
            },
        }

    def __repr__(self) -> str:
        """String representation of document."""
        return (
            f"CADDocument(name='{self.name}', "
            f"layers={len(self._layers)}, entities={len(self._entities)})"
        )
