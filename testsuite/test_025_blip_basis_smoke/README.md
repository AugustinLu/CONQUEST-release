# Test 025: orthorhombic Si blip-basis smoke test

This test establishes whether the legacy CONQUEST blip-basis path still
executes before attempting any nonorthogonal generalization. It reuses the
eight-atom conventional diamond-Si cell and ion file from test 001.

The calculation explicitly selects `Basis.BasisSet blips`, initializes nine
blip support functions from the nine PAOs in the maintained Si ion file, and
runs a self-consistent diagonalization calculation. Blip-coefficient
optimization is intentionally disabled: this is an execution and
initialization gate, not a converged blip-basis benchmark.

Run with:

```bash
./run_workflow.sh
```

The checker requires:

- explicit confirmation that the blip basis was selected;
- completion of blip coefficient initialization;
- SCF convergence;
- the maintained Harris-Foulkes energy and electron count within tolerance;
- normal completion without non-finite output.

The committed one-rank reference has a Harris-Foulkes energy of
`-33.282717184298 Ha` and `32.000050` electrons. These values are regression
signals for the deliberately coarse smoke-test setup, not converged Si
predictions.

This orthorhombic test does not validate nonorthogonal blip transforms,
optimized blip coefficients, forces, stress, or order-N execution. Those are
separate acceptance layers.
