import sys

with open("src/bec_module.f90", "r") as f:
    text = f.read()

# Instead of fighting CONQUEST internal index updates or SCF logic manually,
# we need to be very explicit and careful. `update_pos_and_matrices(0)` works correctly
# but since it resets DM automatically maybe we don't need flag_LmatrixReuse = .false.
# Actually, the problem is SCF reaches tolerance in 1 iteration (`PulayMixSC: reached SCF residual of 0.87157E-07 after 1 iterations`)
# That means it is still using the density from the previous state somehow and not converging from scratch!
text = text.replace("call update_pos_and_matrices(1)", "call update_pos_and_matrices(0)")
# We need to tell CONQUEST to restart the SCF from scratch!
# In minimise.f90: `if((.not.reset_L) .and. (.not.flag_DM_converged) .and. (.not.restart_DM)) reset_L = .true.`
# So if we set `flag_DM_converged = .false.`, it will trigger `reset_L = .true.`!
# But we already did `flag_DM_converged = .false.` and it didn't fully reset the density matrix K/L!
# Maybe we need to set `restart_DM = .false.` too? `restart_DM` defaults to .false.
# Oh, the issue might be `flag_LmatrixReuse` allows it to keep K.
# Let's set BOTH `flag_LmatrixReuse = .false.` and `flag_DM_converged = .false.` and `update_pos_and_matrices(0)`.

with open("src/bec_module.f90", "w") as f:
    f.write(text)
