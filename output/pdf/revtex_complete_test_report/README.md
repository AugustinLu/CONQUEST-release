# REVTeX complete validation report

This folder is self-contained for the report artifact:

- `conquest_general_cell_validation_revtex.pdf` is the rendered report;
- `conquest_general_cell_validation_revtex.tex` is the generated REVTeX source;
- `generate_revtex_report.py` rebuilds the source and refreshes the copied assets;
- `references.bib` contains the report bibliography;
- `figures/` contains every band/PDOS and numerical-validation image used;
- `data/all_tests_summary.json` is the consolidated 32-test execution record.

From this directory, regenerate and compile with:

```sh
python3 generate_revtex_report.py
tectonic -X compile conquest_general_cell_validation_revtex.tex
```

The settings table distinguishes Monkhorst-Pack SCF/PDOS meshes from line-mode
band paths. Grid cutoffs are reported in hartree. Tests 020 and 024 use
nonstandard workflow input filenames, so their known two-atom counts are
recorded explicitly by the report generator.
