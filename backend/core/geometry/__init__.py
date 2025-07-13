"""
Geometry Package

Contains fundamental geometry classes and operations for 2D CAD functionality.
"""

from .point import Point2D
from .vector import Vector2D
from .line import Line
from .circle import Circle
from .arc import Arc
from .bbox import BoundingBox

__all__ = [
    "Point2D",
    "Vector2D", 
    "Line",
    "Circle",
    "Arc",
    "BoundingBox",
]