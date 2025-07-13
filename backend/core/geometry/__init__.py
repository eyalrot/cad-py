"""
Geometry Package

Contains fundamental geometry classes and operations for 2D CAD functionality.
"""

from .arc import Arc
from .bbox import BoundingBox
from .circle import Circle
from .line import Line
from .point import Point2D
from .vector import Vector2D

__all__ = [
    "Point2D",
    "Vector2D",
    "Line",
    "Circle",
    "Arc",
    "BoundingBox",
]
