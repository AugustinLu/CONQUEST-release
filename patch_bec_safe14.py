import sys

with open("src/bec_module.f90", "r") as f:
    text = f.read()

# Let's ensure we call update_pos_and_matrices(0), THEN update_H!
# wait, in patch_bec_safe_final.py I replaced `call update_pos_and_matrices(0)` with:
# `call wrap_xyz_atom_cell() \n call update_r_atom_cell() \n call check_move_atoms() \n call updateIndices(.true., fixed_potential) \n call update_H(fixed_potential)`
# Let's see what is currently in bec_module.f90:
