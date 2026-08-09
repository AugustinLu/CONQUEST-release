# Test 030: exact triclinic block distance

This source-level geometry test exercises the exact distance from a point to
a skewed integration-grid block.  Its adversarial case places a point inside
the block's Cartesian axis-aligned bounding box but outside the actual
parallelepiped, exposing the false neighbour that the former approximation
accepted.  Axis-aligned, interior, and face-projection controls are included.
