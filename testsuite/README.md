# CONQUEST test suite.

This directory currently contains eight end-to-end tests

  - `test_001_bulk_Si_1proc_Diag` (tests ground state with diagonalisation)
  - `test_002_bulk_Si_1proc_OrderN` (tests ground state with linear scaling)
  - `test_003_bulk_BTO_polarisation` (tests polarisation (Resta))
  - `test_004_isol_C2H4_4proc_PBE0CRI` (tests EXX)
  - `test_005_isol_C2H4_4proc_PBE0GTO` (tests EXX)
  - `test_006_isol_C2H4_4proc_PBE0ERI` (tests EXX)
  - `test_007_isol_CH_spinpol_1proc_PBE0CRI` (tests EXX)
  - `test_008_surface_dipole` (tests surface dipole implementation)

for Conquest, and a simple python pytest script for checking the correctness of the outputs.

## Usage

To run the tests

  1. Compile Conquest with `make` in `../src`
  2. Run the `Conquest` executable in the subdirectories named `test_00*`
  3. Check the correctness of the outputs with `pytest`

These steps can be run automatically using the script `run_conquest_tests.sh` in this directory.

### Complete numbered suite

`run_all_tests.py` runs every numbered test directory, including the extended
general-cell workflows.  It builds with at most three jobs and dynamically
limits every MPI launch to

```text
max(1, min(3, floor(number_of_atoms / 3)))
```

The MPI limit is applied inside nested workflows as well as to the original
tests 001-009.  Run the complete suite and generate its JSON and PDF reports
with:

```bash
/opt/anaconda3/bin/python run_all_tests.py
```

Individual tests or ranges can be selected while developing:

```bash
/opt/anaconda3/bin/python run_all_tests.py --tests 5,12,28-32
```

After correcting a failure, a targeted rerun can replace those records in an
earlier complete summary and regenerate a consolidated report:

```bash
/opt/anaconda3/bin/python run_all_tests.py --no-build --tests 12,28 \
  --base-summary test_runs/20260809-230103/summary.json
```

Timestamped logs and machine-readable summaries are stored under
`test_runs/`.  The latest PDF is written to
`../output/pdf/conquest_all_tests_report.pdf`.

## Contributing

To add new tests

1. Add input files and a sample output file (run with `IO.Iprint 0` and named `Conquest_out.ref`) in a new subdirectory under [testsuite](./). The naming convention is test directory names start with `test_` followed by a running index with three digits, e.g. `004`.
2. Add a new test to `TestClass` in [`test_check_output.py`](./test_check_output.py). You can use one of the current tests, named `test_XXX` as templates.
   - Update the directory name passed to `path`
   - Update the list of parameters in the `@pytest.mark.parametrize` decorator. The `key` parameters correspond to fields in the `Conquest_out` file to be checked against the reference.
   - If necessary, update the `read_conquest_out()` function to parse a new field from the output.
   - If necessary, update the `precision()` function to return a custom precision for a given value of the `key` parameter.
4. Add it as a new `Run test XXX` step to the [CI workflow](../.github/workflows/makefile.yml)
