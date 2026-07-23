import sys

with open("src/bec_module.f90", "r") as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if "updateIndices(.true., fixed_potential)" in line:
        line = line.replace("updateIndices(.true., fixed_potential)", "updateIndices3(fixed_potential, tot_force)")
    elif "use move_atoms,       only: wrap_xyz_atom_cell, update_atom_coord, updateIndices, update_H" in line:
        line = line.replace("updateIndices", "updateIndices3")
    new_lines.append(line)

with open("src/bec_module.f90", "w") as f:
    f.writelines(new_lines)
