"""Serialization utilities for CAD models."""

import json
import pickle
from pathlib import Path
from typing import Any, Dict, Union

from .document import CADDocument


class DocumentSerializer:
    """Handles document serialization in multiple formats."""
    
    @staticmethod
    def to_json(document: CADDocument, indent: int = 2) -> str:
        """Serialize document to JSON string.
        
        Args:
            document: CAD document to serialize
            indent: JSON indentation level
            
        Returns:
            JSON string representation
        """
        return json.dumps(document.serialize(), indent=indent, ensure_ascii=False)
    
    @staticmethod
    def from_json(json_str: str) -> CADDocument:
        """Deserialize document from JSON string.
        
        Args:
            json_str: JSON string representation
            
        Returns:
            CAD document instance
        """
        data = json.loads(json_str)
        return CADDocument.deserialize(data)
    
    @staticmethod
    def to_binary(document: CADDocument) -> bytes:
        """Serialize document to binary format using pickle.
        
        Args:
            document: CAD document to serialize
            
        Returns:
            Binary representation
        """
        return pickle.dumps(document.serialize())
    
    @staticmethod
    def from_binary(binary_data: bytes) -> CADDocument:
        """Deserialize document from binary format.
        
        Args:
            binary_data: Binary representation
            
        Returns:
            CAD document instance
        """
        data = pickle.loads(binary_data)
        return CADDocument.deserialize(data)
    
    @staticmethod
    def save_json(document: CADDocument, file_path: Union[str, Path]) -> None:
        """Save document to JSON file.
        
        Args:
            document: CAD document to save
            file_path: Path to save file
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(document.serialize(), f, indent=2, ensure_ascii=False)
    
    @staticmethod
    def load_json(file_path: Union[str, Path]) -> CADDocument:
        """Load document from JSON file.
        
        Args:
            file_path: Path to load file
            
        Returns:
            CAD document instance
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return CADDocument.deserialize(data)
    
    @staticmethod
    def save_binary(document: CADDocument, file_path: Union[str, Path]) -> None:
        """Save document to binary file.
        
        Args:
            document: CAD document to save
            file_path: Path to save file
        """
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'wb') as f:
            pickle.dump(document.serialize(), f)
    
    @staticmethod
    def load_binary(file_path: Union[str, Path]) -> CADDocument:
        """Load document from binary file.
        
        Args:
            file_path: Path to load file
            
        Returns:
            CAD document instance
        """
        with open(file_path, 'rb') as f:
            data = pickle.load(f)
        
        return CADDocument.deserialize(data)


class CompactSerializer:
    """Compact serialization for performance-critical scenarios."""
    
    @staticmethod
    def serialize_entities_only(document: CADDocument) -> Dict[str, Any]:
        """Serialize only entity data for fast operations.
        
        Args:
            document: CAD document
            
        Returns:
            Compact entity data
        """
        return {
            'entities': {eid: entity.serialize() for eid, entity in document._entities.items()},
            'entity_count': len(document._entities)
        }
    
    @staticmethod
    def serialize_layers_only(document: CADDocument) -> Dict[str, Any]:
        """Serialize only layer data.
        
        Args:
            document: CAD document
            
        Returns:
            Compact layer data
        """
        return {
            'layers': {lid: layer.serialize() for lid, layer in document._layers.items()},
            'current_layer_id': document._current_layer_id,
            'layer_count': len(document._layers)
        }
    
    @staticmethod
    def serialize_metadata_only(document: CADDocument) -> Dict[str, Any]:
        """Serialize only document metadata.
        
        Args:
            document: CAD document
            
        Returns:
            Document metadata
        """
        return {
            'id': document.id,
            'name': document.name,
            'version': document.version,
            'description': document.description,
            'metadata': document.metadata,
            'created_at': document.created_at.isoformat(),
            'modified_at': document.modified_at.isoformat(),
            'statistics': document.get_statistics()
        }