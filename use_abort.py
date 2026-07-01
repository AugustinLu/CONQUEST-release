import re

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    new_content = content
    # Change cq_warn to cq_abort for non-orthorhombic cell check
    new_content = new_content.replace("call cq_warn('read_atomic_positions', &\n               'Non-orthorhombic cell support is under development. Please wait.')",
                                      "call cq_abort('Non-orthorhombic cell support is under development. Please wait.')")

    with open(filepath, 'w') as f:
        f.write(new_content)

process_file("src/io_module.f90")
