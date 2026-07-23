import sys

with open("src/bec_module.f90", "r") as f:
    text = f.read()

text = text.replace("flag_calc_bec, ne_in_cell, species_glob", "flag_calc_bec, ne_in_cell, species_glob, flag_LmatrixReuse, flag_DM_converged, restart_DM")

text = text.replace("use move_atoms,       only: update_atom_coord, updateIndices3, update_H", "use move_atoms,       only: update_r_atom_cell, updateIndices, update_H, wrap_xyz_atom_cell, check_move_atoms")

text = text.replace("          call update_atom_coord()\n          call updateIndices3(fixed_potential, tot_force)", "          call wrap_xyz_atom_cell()\n          call update_r_atom_cell()\n          call check_move_atoms()\n          call updateIndices(.true., fixed_potential)")

text = text.replace("real(double), dimension(3) :: p_ionic_plus, p_ionic_minus", "real(double), dimension(3) :: p_ionic_plus, p_ionic_minus\n    logical :: flag_LmatrixReuse_orig\n    logical :: flag_DM_converged_orig")
text = text.replace("    if (inode == ionode) then\n       write(io_lun, fmt='(/,4x,60(\"-\"))')", "    if (inode == ionode) then\n       write(io_lun, fmt='(/,4x,60(\"-\"))')\n    end if\n\n    flag_LmatrixReuse_orig = flag_LmatrixReuse\n    flag_LmatrixReuse = .false.\n    flag_DM_converged_orig = flag_DM_converged\n    flag_DM_converged = .false.\n    if (.false.) then")

text = text.replace("call get_E_and_F(fixed_potential, vary_mu, total_energy, .true., .true., 0)", "flag_DM_converged = .false.\n          restart_DM = .false.\n          call get_E_and_F(fixed_potential, vary_mu, total_energy, .true., .true., 0)")

text = text.replace("call write_extxyz('trajectory.xyz', total_energy, tot_force, stress)", "flag_LmatrixReuse = flag_LmatrixReuse_orig\n    flag_DM_converged = flag_DM_converged_orig\n    call write_extxyz('trajectory.xyz', total_energy, tot_force, stress)")

with open("src/bec_module.f90", "w") as f:
    f.write(text)
