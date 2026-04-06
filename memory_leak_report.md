# Memory Leak Investigation Report

This report documents the confirmed sources of memory leaks found during deep static analysis of the CONQUEST codebase. These memory leaks occur during Molecular Dynamics (MD) calculations, particularly scaling significantly with Multi-Site Support Functions (MSSF), as reflected in the `arachine400` and `mssf` growth metrics.

---

## 1. Critical Continuous Leak: Unfreed `InfoMat` Read Matrices

When CONQUEST reads saved or checkpointed matrices from the file system, it invokes `grab_matrix2` (located in `src/store_matrix_module.f90`). This subroutine dynamically allocates an array of `InfoMat` derived types, and inside each element, allocates several deep nested arrays (`alpha_i`, `idglob_i`, `jmax_i`, `beta_j_i`, `rvec_Pij`, `data_Lold`, etc.) proportional to the system size and number of spins.

While `store_matrix_module` provides a `deallocate_InfoMatrixFile` subroutine to cleanly free this memory, several core loops inside CONQUEST invoke `grab_matrix2` without ever calling the deallocation routine, causing massive chunks of memory to be orphaned per step.

### Detailed Findings:

**1. File:** `src/move_atoms.module.f90` (The Primary MD Leak)
- **Location:** Inside `update_pos_and_matrices` (approx. Lines 5120-5160)
- **Reason:** Called on **every MD step**, `update_pos_and_matrices` reads matrix components (`L`, `K`, `S`) across MPI ranks to propagate them forward.
- **Why MSSF made it worse:** When MSSF is active (`flag_SFcoeff`), an additional matrix structure (`SFcoeff`) is allocated and read. Thus, the MSSF leak scale directly correlates to this extra `InfoMat` block being leaked on top of the standard MD baseline.
- **Risk Level:** **Critical**. This continuous leak scales with system size and MD iterations. (A patch for this specific location has been provided).

**2. File:** `src/XLBOMD_module.f90`
- **Location:** Inside `initial_XLBOMD` and `Do_XLBOMD` (approx. Lines 539-550, 621)
- **Reason:** `grab_matrix2` is called repeatedly to load the `X`, `Xvel`, and `S` matrices into `InfoMat`, but `deallocate_InfoMatrixFile` and `free_InfoMatGlobal` were never invoked.
- **Risk Level:** **High** (if XL-BOMD is running). Similar to the main MD loop, this causes a continuous leak per XLBOMD propagation.

**3. File:** `src/S_matrix_module.f90`
- **Location:** Inside `get_S_matrix` (approx. Line 879)
- **Reason:** When `flag_readT` or `restart_T` is true, the code reads inverse S-matrix components `T` using `grab_matrix2`. Memory is never deallocated.
- **Risk Level:** **Moderate/High** (depending on how often `get_S_matrix` hits the read condition).

**4. File:** `src/initialisation_module.f90`
- **Location:** Inside `initial_phis` (approx. Lines 1226, 1253, 1273, 1279)
- **Reason:** During the initial matrix startup routines, `grab_matrix2` is called up to four times to load `SFcoeff`, `T`, `L`, and `K` without being followed by `deallocate_InfoMatrixFile`.
- **Risk Level:** **Low** (flat cost per run since this is startup code only).

---

## 2. General Initialization Orphaned Arrays

**5. File:** `src/cdft_module.f90`
- **Location:** Inside `init_cdft`
- **Reason:** Several Fortran arrays and memory blocks via `allocate_temp_matrix` are allocated (`matWc`, `cDFT_Vc`, `cDFT_W`, `flag_cdft_atom`, `bwgrid`, and `matHzero`) when cDFT conditions are active. The module completely lacks an accompanying deallocation routine (`end_cdft`) to gracefully tear them down at runtime closure in `src/main.f90`.
- **Risk Level:** **Low** (one-time allocation size at program start).

---

## Conclusion
The most critical memory accumulation observed in standard `arachine400` profiles and the accelerated accumulation under `mssf` is driven by the missing `deallocate_InfoMatrixFile` calls inside `update_pos_and_matrices` within `src/move_atoms.module.f90`. A targeted patch has been prepared to fix this specific issue first, to allow for focused testing, with remaining minor leaks documented for subsequent cleanups.