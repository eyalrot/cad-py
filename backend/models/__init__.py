"""CAD Backend Models.

This module contains the core data models for the CAD system including
document structure, entities, and layers.
"""

from .entity import BaseEntity, EntityFilter
from .layer import Layer, Color, LineType
from .document import CADDocument
from .serialization import DocumentSerializer, CompactSerializer

__all__ = [
    "BaseEntity",
    "EntityFilter", 
    "Layer",
    "Color",
    "LineType",
    "CADDocument",
    "DocumentSerializer",
    "CompactSerializer",
]