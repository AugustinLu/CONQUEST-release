import sys

with open("src/bec_module.f90", "r") as f:
    text = f.read()

# Need to set flag_LmatrixReuse = .false. around bec_run AND set restart_DM = .false. before EACH get_E_and_F!
# Wait! In minimise.f90 `if(restart_DM) then reset_L = .false. ; restart_DM = .false. endif`.
# We need `restart_DM = .false.` otherwise `reset_L` gets suppressed.
# Let's add it explicitly before every `get_E_and_F` in `bec_module.f90`
text = text.replace("          flag_DM_converged = .false.\n          call get_E_and_F(fixed_potential, vary_mu, total_energy, .true., .true., 0)", "          flag_DM_converged = .false.\n          restart_DM = .false.\n          call get_E_and_F(fixed_potential, vary_mu, total_energy, .true., .true., 0)")
text = text.replace("    flag_DM_converged = .false.\n          call get_E_and_F(fixed_potential, vary_mu, total_energy, .true., .true., 0)", "    flag_DM_converged = .false.\n          restart_DM = .false.\n          call get_E_and_F(fixed_potential, vary_mu, total_energy, .true., .true., 0)")

with open("src/bec_module.f90", "w") as f:
    f.write(text)
