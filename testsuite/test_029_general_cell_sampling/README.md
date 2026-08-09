# Test 029: sampling bounds for a general cell

This test uses an extreme unimodular re-expression of primitive silicon.  It
checks two distinct sampling rules:

- each FFT index-box face lies beyond the sphere implied by
  `Grid.GridCutoff`; this bound depends on the direct-vector lengths;
- each automatically generated Monkhorst-Pack step is no larger than
  `Diag.dk`; this bound depends on the reciprocal-vector lengths.

The distinction is important for strongly skewed cells, where a direct-vector
length and its associated direct-plane spacing can differ by a large factor.
