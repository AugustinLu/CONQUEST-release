# Test 032: triclinic surface geometry

This source-level regression validates the geometry used by the slab dipole
correction.  For all three fractional lattice directions it checks the true
face area, perpendicular cell height, and wrapped atomic coordinate along the
face normal.  The cell is fully triclinic, so direct-vector lengths and
Cartesian coordinate components are deliberately not valid substitutes.
