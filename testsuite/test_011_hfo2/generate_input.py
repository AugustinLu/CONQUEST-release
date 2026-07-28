import math

a = 5.1156
b = 5.1722
c = 5.2948
beta = 99.18 * math.pi / 180.0

ax = a
ay = 0.0
az = 0.0

bx = 0.0
by = b
bz = 0.0

cx = c * math.cos(beta)
cy = 0.0
cz = c * math.sin(beta)

print(f"{ax:.6f} {ay:.6f} {az:.6f}")
print(f"{bx:.6f} {by:.6f} {bz:.6f}")
print(f"{cx:.6f} {cy:.6f} {cz:.6f}")
print("12")

def get_positions(frac):
    x, y, z = frac
    return [
        (x, y, z),
        (-x, -y, -z),
        (-x, y+0.5, -z+0.5),
        (x, -y+0.5, z+0.5)
    ]

hf_frac = (0.275, 0.040, 0.208)
o1_frac = (0.074, 0.332, 0.347)
o2_frac = (0.449, 0.758, 0.480)

hf_pos = get_positions(hf_frac)
o1_pos = get_positions(o1_frac)
o2_pos = get_positions(o2_frac)

for pos in hf_pos:
    print(f"{pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f} 1 F F F")
for pos in o1_pos:
    print(f"{pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f} 2 F F F")
for pos in o2_pos:
    print(f"{pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f} 2 F F F")
