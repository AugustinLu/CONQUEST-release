# Memory Leak Investigation Report (Updated)

Upon deeper static analysis after identifying that `b_rem` is properly deallocated at the end of the `kpart` loop (and thus the commented out `deallocate(b_rem)` is correct behavior), the root cause of the continuous, scaling memory leak during MD operations has been located.

## Critical Memory Leak: Unfreed File Read Matrices (`InfoMat`)

### 1. File: `src/move_atoms.module.f90`
- **Line(s):** 5125-5153 (Inside `update_pos_and_matrices`)
- **Reason:** The `update_pos_and_matrices` subroutine is called on every MD step to update the `L`, `K`, `S`, and `SFcoeff` matrices across MPI ranks. For each matrix type requested, the subroutine calls `grab_matrix2` (e.g., `call grab_matrix2('L', inode, nfile, InfoMat, InfoGlob, index=0, n_matrix=nspin)`).

  Inside `src/store_matrix_module.f90` at line 1242, `grab_matrix2` executes `allocate(InfoMat(nfile), STAT=stat_alloc)`. It then loops through files and allocates several sub-arrays within each `InfoMat` struct (e.g., `alpha_i`, `idglob_i`, `jmax_i`, `beta_j_i`, `rvec_Pij`, `data_Lold`, etc.).

  However, `update_pos_and_matrices` never calls `deallocate_InfoMatrixFile(nfile, InfoMat)` after `Matrix_CommRebuild`. Therefore, **multiple sets of matrices representing the entire system size are allocated on every single MD step and never freed.** Since MSSF requires updating an additional set of matrices (`SFcoeff`), the leak is noticeably worse per step when MSSF is enabled compared to standard MD (which only updates `L`, `K`, `S`), perfectly matching the provided memory plot.
- **Risk Level:** **Critical**. This scales with system size and MD steps. It is the primary cause of the continuous memory ramp.

### 2. File: `src/XLBOMD_module.f90`
- **Line(s):** 539-550 (Inside `initial_XLBOMD`), 621 (Inside `Do_XLBOMD`)
- **Reason:** Similar to the above issue, `grab_matrix2` is called repeatedly to load `X`, `Xvel`, and `S` matrices into `InfoMat`, but `deallocate_InfoMatrixFile` is never invoked, orphaning all read data per call.
- **Risk Level:** **High**. If XLBOMD is running, this causes another per-step/per-initialization leak.

### 3. File: `src/S_matrix_module.f90`
- **Line(s):** 878 (Inside `get_S_matrix`)
- **Reason:** When `flag_readT` or `restart_T` is true, `grab_matrix2` is used to load `T` into `Info`, but `Info` is never deallocated via `deallocate_InfoMatrixFile`.
- **Risk Level:** **High**. Dependent on how often `get_S_matrix` triggers a read.

### 4. File: `src/initialisation_module.f90`
- **Line(s):** 1226, 1253, 1273, 1279 (Inside `initial_phis`)
- **Reason:** During matrix startup, `grab_matrix2` is called to load `SFcoeff`, `T`, `L`, and `K` without being followed by `deallocate_InfoMatrixFile`.
- **Risk Level:** **Low/Moderate**. This only occurs once at program start, so it represents a flat initialization cost rather than a continuous per-step leak.

## Other Findings

### 5. File: `src/cdft_module.f90`
- **Line(s):** 84-115 (Inside `init_cdft`)
- **Reason:** Standard Fortran `allocate` is used to allocate several arrays and `allocate_temp_matrix` is used for `matWc` and `matHzero` during initialization (`init_cdft`). However, there is no corresponding `end_cdft` subroutine to release `matWc`, `cDFT_Vc`, `cDFT_W`, `flag_cdft_atom`, `bwgrid`, or `matHzero`.
- **Risk Level:** **Low**. Flat memory cost at startup if CDFT is active.