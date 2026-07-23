import sys

with open("src/bec_module.f90", "r") as f:
    text = f.read()

# Since get_E_and_F is not actually completely clearing the density history
# because `resetL` logic in get_E_and_F has `reset_L = .false.` and `if(restart_DM) reset_L = .false.`
# The sure-fire way is to physically delete the density matrix K/L arrays.
# BUT wait! If I just set `flag_DM_converged = .false.`, then `get_E_and_F` sets `reset_L = .true.`.
# Let's verify `reset_L = .true.` behavior.
# Wait, for exact diagonalisation (which the BEC test is using), the density matrix K is generated from eigenvalues!
# If it converges in 1 iteration, it means the Pulay mixer is perfectly guessing the density.
# But why does `Z*` output identically 0? Because the charge density/polarization does NOT change between the + and - displacement!
# Why doesn't it change? Because the K matrix generated via diagonalization relies on the Hamiltonian `H` and Overlap `S` matrices.
# If `H` and `S` don't change, the resulting density matrix won't change.
# Are `H` and `S` actually updating?
# In `bec_module.f90`:
# call update_pos_and_matrices(1) -> update_method 1 is `updateLorK`
# Let's check `update_method` constants:
# In move_atoms.f90:
#    integer, parameter :: updateL = 1
#    integer, parameter :: updateLorK = 2
#    integer, parameter :: updateS = 3
#    integer, parameter :: updateX = 4
#    integer, parameter :: updateSFcoeff = 5
#    integer, parameter :: extrplL = 6
# So `update_pos_and_matrices(1)` only updates L/K, NOT `S` or `H` !!!
# Wait, `update_pos_and_matrices(0)` updates EVERYTHING (update_method=0 -> update_H).
# But `update_pos_and_matrices(0)` crashed with INFO=16 in pzhegvx because `update_r_atom_cell` was not called properly before it maybe?
# Or because `flag_LmatrixReuse = .false.` made it crash?
