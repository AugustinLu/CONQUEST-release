with open("testsuite/test_010_bec/Conquest_out", "rb") as f:
    text = f.read().decode(errors='ignore')

forces = []
for line in text.split("\n"):
    if line.startswith("    force:     2   "):
        forces.append(line)

print("Forces on atom 2 throughout the run:")
for f in forces:
    print(f)
