# Test 031: rotated triclinic PDB restart

This regression starts from a deliberately rotated triclinic Si cell, writes
a PDB checkpoint, and restarts CONQUEST from that checkpoint.  It verifies
that the standard PDB `SCALE1`--`SCALE3` records retain the full cell
orientation omitted by `CRYST1`, and that both the lattice and fractional
atomic coordinates survive the write/read/write cycle within PDB precision.

Run with:

```bash
./run_workflow.sh
```

The script uses one MPI rank.
