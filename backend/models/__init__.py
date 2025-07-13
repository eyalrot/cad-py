"""CAD Backend Models.

This module contains the core data models for the CAD system including
document structure, entities, and layers.
"""

from .dimension import (
    ArrowType,
    Dimension,
    DimensionPoint,
    DimensionStyle,
    DimensionType,
    UnitFormat,
)
from .document import CADDocument
from .entity import BaseEntity, EntityFilter
from .layer import Color, Layer, LineType
from .serialization import CompactSerializer, DocumentSerializer

__all__ = [
    "BaseEntity",
    "EntityFilter",
    "Layer",
    "Color",
    "LineType",
    "Dimension",
    "DimensionStyle",
    "DimensionType",
    "DimensionPoint",
    "UnitFormat",
    "ArrowType",
    "CADDocument",
    "DocumentSerializer",
    "CompactSerializer",
]
