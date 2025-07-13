"""Block and symbol model for CAD system."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from backend.core.geometry.point import Point2D
from backend.core.geometry.vector import Vector2D
from backend.models.entity import BaseEntity


class BlockType(Enum):
    """Types of blocks."""
    
    STATIC = "static"           # Normal block with fixed geometry
    DYNAMIC = "dynamic"         # Block with adjustable parameters
    ANNOTATIVE = "annotative"   # Block that scales with annotation scale


class AttributeType(Enum):
    """Types of block attributes."""
    
    TEXT = "text"
    NUMBER = "number"
    BOOLEAN = "boolean"
    CHOICE = "choice"
    POINT = "point"
    DISTANCE = "distance"
    ANGLE = "angle"


@dataclass(frozen=True)
class AttributeDefinition:
    """Definition of a block attribute."""
    
    name: str
    type: AttributeType
    default_value: Any
    prompt: str = ""
    description: str = ""
    required: bool = True
    choices: Optional[List[str]] = None  # For choice type
    min_value: Optional[float] = None    # For number/distance/angle
    max_value: Optional[float] = None
    visible: bool = True
    
    def validate_value(self, value: Any) -> bool:
        """Validate if a value is acceptable for this attribute."""
        if not self.required and value is None:
            return True
            
        if self.type == AttributeType.TEXT:
            return isinstance(value, str)
        elif self.type == AttributeType.NUMBER:
            if not isinstance(value, (int, float)):
                return False
            if self.min_value is not None and value < self.min_value:
                return False
            if self.max_value is not None and value > self.max_value:
                return False
            return True
        elif self.type == AttributeType.BOOLEAN:
            return isinstance(value, bool)
        elif self.type == AttributeType.CHOICE:
            return self.choices is not None and value in self.choices
        elif self.type == AttributeType.POINT:
            return isinstance(value, Point2D)
        elif self.type == AttributeType.DISTANCE:
            return isinstance(value, (int, float)) and value >= 0
        elif self.type == AttributeType.ANGLE:
            return isinstance(value, (int, float))
            
        return False


class Block:
    """Block definition containing entities and attributes."""
    
    def __init__(self, name: str, base_point: Point2D, block_type: BlockType = BlockType.STATIC):
        """Initialize block.
        
        Args:
            name: Unique name for the block
            base_point: Base insertion point for the block
            block_type: Type of block (static, dynamic, annotative)
        """
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.base_point: Point2D = base_point
        self.block_type: BlockType = block_type
        
        # Block content
        self.entities: List[BaseEntity] = []
        self.attributes: Dict[str, AttributeDefinition] = {}
        
        # Block properties
        self.description: str = ""
        self.category: str = "General"
        self.tags: List[str] = []
        self.preview_image_path: Optional[str] = None
        
        # Metadata
        self.created_at: datetime = datetime.utcnow()
        self.modified_at: datetime = datetime.utcnow()
        self.author: str = ""
        self.version: str = "1.0"
        
        # Display properties
        self.units: str = "mm"
        self.scale: float = 1.0
        
        # Advanced properties
        self.explodable: bool = True
        self.allow_explode: bool = True
        self.path_type: str = "relative"  # relative, absolute
        
    def add_entity(self, entity: BaseEntity):
        """Add an entity to the block definition."""
        # Adjust entity coordinates relative to base point
        if hasattr(entity, 'move'):
            # Move entity relative to base point
            entity.move(-self.base_point.x, -self.base_point.y)
        
        self.entities.append(entity)
        self.modified_at = datetime.utcnow()
        
    def remove_entity(self, entity: BaseEntity):
        """Remove an entity from the block definition."""
        if entity in self.entities:
            self.entities.remove(entity)
            self.modified_at = datetime.utcnow()
            
    def add_attribute(self, attribute: AttributeDefinition):
        """Add an attribute definition to the block."""
        self.attributes[attribute.name] = attribute
        self.modified_at = datetime.utcnow()
        
    def remove_attribute(self, name: str):
        """Remove an attribute definition from the block."""
        if name in self.attributes:
            del self.attributes[name]
            self.modified_at = datetime.utcnow()
            
    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """Get bounding box of all entities in the block."""
        if not self.entities:
            return (0.0, 0.0, 0.0, 0.0)
            
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for entity in self.entities:
            bbox = entity.get_bounding_box()
            if bbox:
                min_x = min(min_x, bbox[0])
                min_y = min(min_y, bbox[1])
                max_x = max(max_x, bbox[2])
                max_y = max(max_y, bbox[3])
                
        return (min_x, min_y, max_x, max_y)
        
    def copy(self) -> "Block":
        """Create a copy of this block definition."""
        new_block = Block(f"{self.name}_copy", self.base_point, self.block_type)
        
        # Copy properties
        new_block.description = self.description
        new_block.category = self.category
        new_block.tags = self.tags.copy()
        new_block.units = self.units
        new_block.scale = self.scale
        new_block.explodable = self.explodable
        new_block.allow_explode = self.allow_explode
        new_block.author = self.author
        
        # Copy entities
        for entity in self.entities:
            new_block.entities.append(entity.copy())
            
        # Copy attributes
        new_block.attributes = self.attributes.copy()
        
        return new_block
        
    def serialize(self) -> Dict[str, Any]:
        """Serialize block to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "base_point": [self.base_point.x, self.base_point.y],
            "block_type": self.block_type.value,
            "entities": [entity.serialize() for entity in self.entities],
            "attributes": {
                name: {
                    "name": attr.name,
                    "type": attr.type.value,
                    "default_value": attr.default_value,
                    "prompt": attr.prompt,
                    "description": attr.description,
                    "required": attr.required,
                    "choices": attr.choices,
                    "min_value": attr.min_value,
                    "max_value": attr.max_value,
                    "visible": attr.visible
                }
                for name, attr in self.attributes.items()
            },
            "description": self.description,
            "category": self.category,
            "tags": self.tags,
            "preview_image_path": self.preview_image_path,
            "units": self.units,
            "scale": self.scale,
            "explodable": self.explodable,
            "allow_explode": self.allow_explode,
            "author": self.author,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat()
        }


class BlockReference:
    """Reference to a block instance in a document."""
    
    def __init__(self, block_id: str, insertion_point: Point2D, layer_id: str = "0"):
        """Initialize block reference.
        
        Args:
            block_id: ID of the block definition
            insertion_point: Point where block is inserted
            layer_id: Layer this block reference belongs to
        """
        self.id: str = str(uuid.uuid4())
        self.block_id: str = block_id
        self.insertion_point: Point2D = insertion_point
        self.layer_id: str = layer_id
        
        # Transformation properties
        self.scale: Vector2D = Vector2D(1.0, 1.0)
        self.rotation: float = 0.0  # Rotation in degrees
        self.uniform_scale: bool = True
        
        # Attribute values for this instance
        self.attribute_values: Dict[str, Any] = {}
        
        # Display properties
        self.visible: bool = True
        self.locked: bool = False
        self.selected: bool = False
        
        # Metadata
        self.created_at: datetime = datetime.utcnow()
        self.modified_at: datetime = datetime.utcnow()
        self.custom_properties: Dict[str, Any] = {}
        
    def set_attribute_value(self, name: str, value: Any):
        """Set value for a block attribute."""
        self.attribute_values[name] = value
        self.modified_at = datetime.utcnow()
        
    def get_attribute_value(self, name: str, default: Any = None) -> Any:
        """Get value for a block attribute."""
        return self.attribute_values.get(name, default)
        
    def set_scale(self, scale_x: float, scale_y: Optional[float] = None):
        """Set scale factors."""
        if scale_y is None or self.uniform_scale:
            self.scale = Vector2D(scale_x, scale_x)
        else:
            self.scale = Vector2D(scale_x, scale_y)
        self.modified_at = datetime.utcnow()
        
    def set_rotation(self, rotation_degrees: float):
        """Set rotation in degrees."""
        self.rotation = rotation_degrees % 360.0
        self.modified_at = datetime.utcnow()
        
    def move(self, delta_x: float, delta_y: float):
        """Move the block reference."""
        self.insertion_point = Point2D(
            self.insertion_point.x + delta_x,
            self.insertion_point.y + delta_y
        )
        self.modified_at = datetime.utcnow()
        
    def get_transformed_point(self, point: Point2D) -> Point2D:
        """Transform a point from block space to world space."""
        import math
        
        # Apply scale
        scaled_x = point.x * self.scale.x
        scaled_y = point.y * self.scale.y
        
        # Apply rotation
        if self.rotation != 0:
            angle_rad = math.radians(self.rotation)
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            
            rotated_x = scaled_x * cos_a - scaled_y * sin_a
            rotated_y = scaled_x * sin_a + scaled_y * cos_a
        else:
            rotated_x = scaled_x
            rotated_y = scaled_y
            
        # Apply translation
        return Point2D(
            rotated_x + self.insertion_point.x,
            rotated_y + self.insertion_point.y
        )
        
    def get_bounding_box(self, block_definition: Block) -> Tuple[float, float, float, float]:
        """Get bounding box of the block reference in world coordinates."""
        if not block_definition.entities:
            return (self.insertion_point.x, self.insertion_point.y, 
                   self.insertion_point.x, self.insertion_point.y)
            
        # Get block's bounding box
        block_bbox = block_definition.get_bounding_box()
        
        # Transform corner points
        corners = [
            Point2D(block_bbox[0], block_bbox[1]),  # min_x, min_y
            Point2D(block_bbox[2], block_bbox[1]),  # max_x, min_y
            Point2D(block_bbox[2], block_bbox[3]),  # max_x, max_y
            Point2D(block_bbox[0], block_bbox[3])   # min_x, max_y
        ]
        
        transformed_corners = [self.get_transformed_point(corner) for corner in corners]
        
        min_x = min(corner.x for corner in transformed_corners)
        min_y = min(corner.y for corner in transformed_corners)
        max_x = max(corner.x for corner in transformed_corners)
        max_y = max(corner.y for corner in transformed_corners)
        
        return (min_x, min_y, max_x, max_y)
        
    def copy(self) -> "BlockReference":
        """Create a copy of this block reference."""
        new_ref = BlockReference(self.block_id, self.insertion_point, self.layer_id)
        
        new_ref.scale = self.scale
        new_ref.rotation = self.rotation
        new_ref.uniform_scale = self.uniform_scale
        new_ref.attribute_values = self.attribute_values.copy()
        new_ref.visible = self.visible
        new_ref.locked = self.locked
        new_ref.custom_properties = self.custom_properties.copy()
        
        return new_ref
        
    def serialize(self) -> Dict[str, Any]:
        """Serialize block reference to dictionary."""
        return {
            "id": self.id,
            "block_id": self.block_id,
            "insertion_point": [self.insertion_point.x, self.insertion_point.y],
            "layer_id": self.layer_id,
            "scale": [self.scale.x, self.scale.y],
            "rotation": self.rotation,
            "uniform_scale": self.uniform_scale,
            "attribute_values": self.attribute_values,
            "visible": self.visible,
            "locked": self.locked,
            "selected": self.selected,
            "custom_properties": self.custom_properties,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat()
        }


class BlockLibrary:
    """Collection of blocks organized by category."""
    
    def __init__(self, name: str, description: str = ""):
        """Initialize block library.
        
        Args:
            name: Name of the library
            description: Description of the library
        """
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.description: str = description
        
        # Library content
        self.blocks: Dict[str, Block] = {}
        self.categories: Dict[str, List[str]] = {}  # category -> block_ids
        
        # Library properties
        self.version: str = "1.0"
        self.author: str = ""
        self.tags: List[str] = []
        self.library_path: Optional[str] = None
        
        # Metadata
        self.created_at: datetime = datetime.utcnow()
        self.modified_at: datetime = datetime.utcnow()
        
    def add_block(self, block: Block):
        """Add a block to the library."""
        self.blocks[block.id] = block
        
        # Add to category
        category = block.category
        if category not in self.categories:
            self.categories[category] = []
        if block.id not in self.categories[category]:
            self.categories[category].append(block.id)
            
        self.modified_at = datetime.utcnow()
        
    def remove_block(self, block_id: str):
        """Remove a block from the library."""
        if block_id in self.blocks:
            block = self.blocks[block_id]
            del self.blocks[block_id]
            
            # Remove from category
            if block.category in self.categories:
                if block_id in self.categories[block.category]:
                    self.categories[block.category].remove(block_id)
                    
            self.modified_at = datetime.utcnow()
            
    def get_block(self, block_id: str) -> Optional[Block]:
        """Get a block by ID."""
        return self.blocks.get(block_id)
        
    def get_blocks_by_category(self, category: str) -> List[Block]:
        """Get all blocks in a category."""
        block_ids = self.categories.get(category, [])
        return [self.blocks[block_id] for block_id in block_ids if block_id in self.blocks]
        
    def get_categories(self) -> List[str]:
        """Get list of all categories."""
        return list(self.categories.keys())
        
    def search_blocks(self, query: str) -> List[Block]:
        """Search blocks by name, description, or tags."""
        query_lower = query.lower()
        results = []
        
        for block in self.blocks.values():
            # Search in name
            if query_lower in block.name.lower():
                results.append(block)
                continue
                
            # Search in description
            if query_lower in block.description.lower():
                results.append(block)
                continue
                
            # Search in tags
            if any(query_lower in tag.lower() for tag in block.tags):
                results.append(block)
                continue
                
        return results
        
    def serialize(self) -> Dict[str, Any]:
        """Serialize library to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "library_path": self.library_path,
            "blocks": {block_id: block.serialize() for block_id, block in self.blocks.items()},
            "categories": self.categories,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat()
        }