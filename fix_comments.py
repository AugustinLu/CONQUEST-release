import os
import re
import glob
from datetime import datetime

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Step 1: Revert historical comments.
    # The script mistakenly replaced "rcellx" in the history section.
    # For example: !!    Removed lat_vec(1,1) references
    # We should look for !! .*lat_vec\(1,1\) and revert it if it was originally rcellx.
    # However, it's easier to just reset the repo, but the problem is we already made the commit.
    # Actually, we can just replace `lat_vec(1,1)` back to `rcellx` inside lines starting with `!!`.

    lines = content.split('\n')
    new_lines = []
    modified = False

    in_history = False
    for i, line in enumerate(lines):
        if re.match(r'^\s*!!\s*MODIFICATION HISTORY', line, re.IGNORECASE):
            in_history = True

        if re.match(r'^\s*!!\s*SOURCE', line, re.IGNORECASE):
            # We add our modification history here
            date_str = "2026/06/30"
            history_str = f"  !!   {date_str} Augustin LU\n  !!    Replaced rcellx, rcelly, rcellz with lat_vec(3,3)"
            new_lines.append(history_str)
            modified = True
            in_history = False

        if in_history and re.match(r'^\s*!!', line):
            # Revert any changes done to history
            line = re.sub(r'lat_vec\(1,1\)', 'rcellx', line)
            line = re.sub(r'lat_vec\(2,2\)', 'rcelly', line)
            line = re.sub(r'lat_vec\(3,3\)', 'rcellz', line)
            line = re.sub(r'lat_vec\b', 'rcellx, rcelly, rcellz', line) # It might have been replaced in `use global_module` equivalent comments.

        # also revert any general comment lines that might have been hit:
        if re.match(r'^\s*!!', line):
            if 'lat_vec(1,1)' in line:
                line = re.sub(r'lat_vec\(1,1\)', 'rcellx', line)
            if 'lat_vec(2,2)' in line:
                line = re.sub(r'lat_vec\(2,2\)', 'rcelly', line)
            if 'lat_vec(3,3)' in line:
                line = re.sub(r'lat_vec\(3,3\)', 'rcellz', line)

        new_lines.append(line)

    new_content = '\n'.join(new_lines)

    if new_content != content:
        with open(filepath, 'w') as f:
            f.write(new_content)

files = [
    "src/PAO_grid_transform_module.f90",
    "src/S_matrix_module.f90",
    "src/UpdateInfo_module.f90",
    "src/UpdateMember_module.f90",
    "src/XC_CQ_module.f90",
    "src/XC_LibXC_v4_module.f90",
    "src/XC_LibXC_v5_module.f90",
    "src/XLBOMD_module.f90",
    "src/atom_dispenser_module.f90",
    "src/blip_grid_transform_module.f90",
    "src/constraint_module.f90",
    "src/control.f90",
    "src/cover_module.f90",
    "src/density_module.f90",
    "src/force_module.f90",
    "src/global_module.f90",
    "src/initial_read_module.f90",
    "src/initialisation_module.f90",
    "src/io_module.f90",
    "src/md_control_module.f90",
    "src/md_misc_module.f90",
    "src/md_model_module.f90",
    "src/move_atoms.module.f90",
    "src/primary_module.f90",
    "src/pseudo_tm_module.f90",
    "src/pseudopotential.module.f90",
    "src/set_blipgrid_module.f90",
    "src/store_matrix_module.f90"
]

for filepath in files:
    process_file(filepath)
