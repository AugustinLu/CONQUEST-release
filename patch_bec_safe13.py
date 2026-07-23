import sys

with open("src/bec_module.f90", "r") as f:
    text = f.read()

# We need to use updatePos (0).
# The crash with INFO=16 in pzhegvx happened when using `update_pos_and_matrices(0)` while `flag_LmatrixReuse = .false.`.
# Wait, no. The crash happened when I did NOT reset `flag_DM_converged`.
# When I reset `flag_DM_converged = .false.`, it didn't crash on `update_pos_and_matrices(0)`.
# Let's verify: In step patch_bec_safe9.py I set it back to `update_pos_and_matrices(0)`.
# And then it crashed with INFO=16 in pzhegvx again in `output.log`!!
# Okay, so `update_pos_and_matrices(0)` ALWAYS crashes with INFO=16 if we do it inside `bec_run`.
# Why? Because `update_pos_and_matrices` internally calls `updateIndices3`, which relies on `wrap_xyz_atom_cell` having run properly BEFORE?
# Actually, inside `update_pos_and_matrices`, it DOES run `wrap_xyz_atom_cell` and `update_atom_coord` internally!
# And then it runs `updateIndices3`.
# So why does pzhegvx crash?
# pzhegvx is finding eigenvalues. It fails when matrix B (overlap matrix) is not positive definite.
# This means the overlap matrix `S` is somehow corrupted.
# Why is `S` corrupted? Because `update_H` was called after `updateIndices3`, and `update_H` calculates `S`!
# But wait, `update_pos_and_matrices(0)` DOES NOT call `update_H`!!!
# `update_pos_and_matrices` ONLY updates positions, indices, and optionally reloads L/K matrices from disk if told to.
# Let's check `update_pos_and_matrices(0)`. `update_method = 0` means `updatePos`.
# It does NOT set `flag_S = .true.` or anything. It just rearranges indices.
# Ah! So the matrices `S` and `H` are NEVER rebuilt! They are just re-indexed for the new partition layout, but their actual numerical values correspond to the old positions!
# Then `pzhegvx` tries to diagonalize a mix-and-match garbage matrix!
# We MUST call `update_H` after `update_pos_and_matrices`!
