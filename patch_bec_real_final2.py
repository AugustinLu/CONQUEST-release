import sys

with open("src/bec_module.f90", "r") as f:
    text = f.read()

# pzhegvx crashing means that updateIndices3 isn't allocating the matrices correctly for ELPA/ScaLAPACK because `update_pos_and_matrices` isn't fully completing or is getting bypassed.
# Wait, `update_pos_and_matrices(1)` is `update_method=1` which corresponds to `updateLorK` ... wait, `update_method=0` corresponds to `update_H`. Let's look at `update_method` mapping.

# Let's revert bec_module.f90 back to the pristine state and just implement `flag_LmatrixReuse = .false.` correctly
text = text.replace("call wrap_xyz_atom_cell()\n          call update_r_atom_cell()\n          call check_move_atoms()\n          call updateIndices(.true., fixed_potential)\n          call update_H(fixed_potential)\n          flag_DM_converged = .false.", "call update_atom_coord()\n          call updateIndices3(fixed_potential, tot_force)\n          call update_H(fixed_potential)")

text = text.replace("flag_DM_converged_orig = flag_DM_converged\n    flag_DM_converged = .false.", "")
text = text.replace("flag_DM_converged = .false.", "")
text = text.replace("flag_DM_converged = flag_DM_converged_orig", "")

with open("src/bec_module.f90", "w") as f:
    f.write(text)
