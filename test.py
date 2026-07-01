import re

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    new_content = content
    # In `read_atomic_positions`, lat_vec(1,1) = r_super_x.
    # Also we should initialize the off-diagonals to 0.

    # We should search for lat_vec(1,1) = r_super_x
    if 'lat_vec(1,1) = r_super_x' in new_content:
        new_content = new_content.replace("lat_vec(1,1) = r_super_x", "lat_vec = 0.0_double\n    lat_vec(1,1) = r_super_x")

    with open(filepath, 'w') as f:
        f.write(new_content)

process_file("src/io_module.f90")
