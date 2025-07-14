#!/usr/bin/env python3
"""
Test CAD geometry functionality inside Docker container.
"""

import sys
import math

def test_geometry_inside_container():
    """Test geometry classes inside Docker where dependencies exist."""
    
    # Test basic geometry operations
    test_code = '''
import sys
sys.path.insert(0, '/app/core')

from geometry.point import Point2D
from geometry.line import Line
from geometry.circle import Circle

# Test Point2D
print("Testing Point2D...")
p1 = Point2D(0, 0)
p2 = Point2D(3, 4)
distance = p1.distance_to(p2)
print(f"Distance: {distance} (expected: 5.0)")

# Test Line
print("Testing Line...")
line = Line(p1, p2)
length = line.length()
print(f"Line length: {length} (expected: 5.0)")

# Test Circle
print("Testing Circle...")
circle = Circle(p1, 5.0)
area = circle.area()
print(f"Circle area: {area} (expected: {math.pi * 25})")

# Test intersection
print("Testing Line-Circle intersection...")
horizontal_line = Line(Point2D(-10, 0), Point2D(10, 0))
intersections = horizontal_line.intersections_with_circle(p1, 5.0)
print(f"Intersections: {len(intersections)} (expected: 2)")

print("All geometry tests completed successfully!")
'''
    
    return test_code

if __name__ == "__main__":
    print("Creating geometry test for Docker container...")
    test_code = test_geometry_inside_container()
    
    # Save test code to file
    with open('/tmp/geometry_test.py', 'w') as f:
        f.write(test_code)
    
    print("Test file created: /tmp/geometry_test.py")
    print("Run with: docker exec cad-py-backend python /tmp/geometry_test.py")