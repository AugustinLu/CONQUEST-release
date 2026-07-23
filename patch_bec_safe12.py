import sys

with open("src/bec_module.f90", "r") as f:
    text = f.read()

text = text.replace("flag_calc_bec, ne_in_cell, species_glob, flag_LmatrixReuse, flag_DM_converged", "flag_calc_bec, ne_in_cell, species_glob, flag_LmatrixReuse, flag_DM_converged, restart_DM")
text = text.replace("          flag_DM_converged = .false.\n", "          flag_DM_converged = .false.\n          restart_DM = .false.\n")
text = text.replace("    flag_DM_converged = .false.\n", "    flag_DM_converged = .false.\n    restart_DM = .false.\n")

with open("src/bec_module.f90", "w") as f:
    f.write(text)
