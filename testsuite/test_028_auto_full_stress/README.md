# Test 028: automatic full stress for general cells

This integration test omits `AtomMove.FullStress` deliberately.  It compares
an axis-aligned cubic cell with a nonorthogonal primitive cell and checks that
only the latter automatically enables and prints the complete Cartesian
stress tensor.  This guards the default used by static stress calculations,
cell relaxation, and flexible-cell molecular dynamics.

Run with:

```bash
./run_workflow.sh
```
