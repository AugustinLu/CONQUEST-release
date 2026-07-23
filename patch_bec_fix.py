import sys

with open("src/bec_module.f90", "r") as f:
    text = f.read()

text = text.replace("call update_pos_and_matrices(0)", "call update_r_atom_cell()\n          call update_pos_and_matrices(0)")
text = text.replace("use move_atoms,       only: update_pos_and_matrices, update_H", "use move_atoms,       only: update_pos_and_matrices, update_H, update_r_atom_cell")

with open("src/bec_module.f90", "w") as f:
    f.write(text)
