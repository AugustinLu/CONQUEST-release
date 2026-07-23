import sys

with open("src/bec_module.f90", "r") as f:
    text = f.read()

# Let's inspect what happens to `atom_coord` and why it isn't moving.
# wait! Earlier when I used `update_pos_and_matrices(0)` I removed `call update_r_atom_cell()`.
# BUT `update_pos_and_matrices(0)` internally does:
#    call wrap_xyz_atom_cell
#    call update_atom_coord
# AND `update_atom_coord` DOES NOT update `x_atom_cell` from `atom_coord`! It updates `atom_coord` from `x_atom_cell`!
# So calling `update_pos_and_matrices` OVERWRITES `atom_coord` with the old `x_atom_cell` which means my BEC displacement is erased!!
# I must call `update_r_atom_cell` BEFORE `update_pos_and_matrices`!
text = text.replace("call update_pos_and_matrices(0)", "call update_r_atom_cell()\n          call update_pos_and_matrices(0)")
# We already did this previously, but maybe I wiped it? Let's check `src/bec_module.f90`
