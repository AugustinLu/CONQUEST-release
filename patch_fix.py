import sys

with open("src/bec_module.f90", "r") as f:
    text = f.read()

# Make sure we actually set flag_DM_converged = .false. inside bec_run
text = text.replace("flag_calc_bec, ne_in_cell, species_glob, flag_LmatrixReuse", "flag_calc_bec, ne_in_cell, species_glob, flag_LmatrixReuse, flag_DM_converged")
text = text.replace("call get_E_and_F(fixed_potential, vary_mu, total_energy, .true., .true., 0)", "flag_DM_converged = .false.\n          call get_E_and_F(fixed_potential, vary_mu, total_energy, .true., .true., 0)")

with open("src/bec_module.f90", "w") as f:
    f.write(text)
