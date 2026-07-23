import sys

with open("src/bec_module.f90", "r") as f:
    text = f.read()

# We need to explicitly clear restart_DM too!
text = text.replace("flag_calc_bec, ne_in_cell, species_glob, flag_LmatrixReuse, flag_DM_converged", "flag_calc_bec, ne_in_cell, species_glob, flag_LmatrixReuse, flag_DM_converged, restart_DM")

# Replace update calls with update_pos_and_matrices(0) THEN update_H
text = text.replace("          call wrap_xyz_atom_cell()\n          call update_r_atom_cell()\n          call check_move_atoms()\n          call updateIndices(.true., fixed_potential)\n          call update_H(fixed_potential)\n          flag_DM_converged = .false.\n          call get_E_and_F(fixed_potential, vary_mu, total_energy, .true., .true., 0)", "          call update_pos_and_matrices(0)\n          call update_H(fixed_potential)\n          flag_DM_converged = .false.\n          restart_DM = .false.\n          call get_E_and_F(fixed_potential, vary_mu, total_energy, .true., .true., 0)")

text = text.replace("use move_atoms,       only: update_r_atom_cell, updateIndices, update_H, wrap_xyz_atom_cell, check_move_atoms", "use move_atoms,       only: update_pos_and_matrices, update_H")

with open("src/bec_module.f90", "w") as f:
    f.write(text)
