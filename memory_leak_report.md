# Memory Leak Investigation Report

## Multi-Site Support Functions (MSSF) Leak

### 1. File: `src/multisiteSF_module.f90`
- **Line(s):** 1411-1414, 1435-1436
- **Routine:** `LFD_make_Subspace_halo`
- **Reason:** The array `b_rem` is dynamically allocated multiple times inside a heavily-used loop (over `kpart=1, ahalo%np_in_halo`). At the end of the `kpart` loop, there is a conditional block that attempts to deallocate `b_rem`:
  ```fortran
  1411: call start_timer(tmr_std_allocation)
  1412: if(allocated(b_rem)) deallocate(b_rem)
  1413: call stop_timer(tmr_std_allocation)
  ```
  However, later down at the end of the subroutine (lines 1435-1436), the explicit `deallocate` for `b_rem` is explicitly commented out:
  ```fortran
  1435: !deallocate(b_rem,STAT=stat)
  1436: !if(stat/=0) call cq_abort('LFD_make_Subspace_halo: error deallocating b_rem')
  ```
  Depending on control flow, if `b_rem` remains allocated upon exit from `LFD_make_Subspace_halo`, Fortran might not garbage collect it depending on compiler behavior (since `b_rem` doesn't have `intent(out)` or a structured lifecycle). Additionally, repeated `allocate()` calls inside the loop without guarantee of cleanup can continuously consume heap memory over the duration of a simulation.
- **Risk Level:** **High**. `LFD_make_Subspace_halo` is called repeatedly whenever the MSSF representations and matrices are updated in the MD/optimization loop. If memory fails to be reclaimed properly per atom/partition, this will cause memory footprint to grow continuously with the number of MD steps.

---

## Other Package-Wide Findings

### 2. File: `src/cdft_module.f90`
- **Line(s):** 84, 88-90, 92, 96, 105, 108-110
- **Routine:** `init_cdft`
- **Reason:** Standard Fortran `allocate` is used to allocate several arrays and `allocate_temp_matrix` is used for `matWc` and `matHzero` during initialization (`init_cdft`). However, there is no corresponding `end_cdft` subroutine, nor any `deallocate` or `free_temp_matrix` calls anywhere in `cdft_module.f90` for `matWc`, `cDFT_Vc`, `cDFT_W`, `flag_cdft_atom`, `bwgrid`, or `matHzero`.
- **Risk Level:** **Low/Moderate**. This is an initialization routine, so the leak is fixed in size (a one-time hit per run). It won't grow infinitely like the MSSF issue during an MD loop, but it reflects orphaned memory.

### Note on `allocate_temp_matrix` / `free_temp_matrix` usage:
Across the entire package, matrix wrappers that use `allocate_temp_matrix` (like those in `force_module.f90`, `S_matrix_module.f90`, `McWeeny.f90`, `pao_minimisation.module.f90`, etc.) were systematically checked. Every temporary matrix allocated during a cyclic loop like force/energy calculations or LFD routines appears strictly paired with a `free_temp_matrix` call within the same subroutine, limiting standard memory leaks from these objects.