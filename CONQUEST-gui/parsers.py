import os
import re

def parse_conquest_input(filepath):
    """Parses Conquest_input and returns a dictionary of settings."""
    data = {}
    if not os.path.exists(filepath):
        return data

    with open(filepath, 'r') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue

        if ' ' in line or '\t' in line:
            # Try splitting by first whitespace
            parts = re.split(r'\s+', line, maxsplit=1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                data[key] = value

    return data

def parse_structure_file(filepath):
    """Parses coords.dat or similar structure files.
    Returns lattice vectors, total atoms, and counts of each species.
    Note: Requires knowledge of species mapping from Conquest_input to accurately get species types.
    For now, it counts atoms per species index.
    """
    data = {
        'lattice_vectors': [],
        'total_atoms': 0,
        'species_counts': {}
    }

    if not os.path.exists(filepath):
        return data

    with open(filepath, 'r') as f:
        lines = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]

    if len(lines) >= 4:
        # First 3 lines are usually lattice vectors
        for i in range(3):
            data['lattice_vectors'].append([float(x) for x in lines[i].split()])

        # 4th line is total atoms
        data['total_atoms'] = int(lines[3])

        # Remaining lines are atoms: x y z species_index
        for line in lines[4:]:
            parts = line.split()
            if len(parts) >= 4:
                species_index = parts[3]
                data['species_counts'][species_index] = data['species_counts'].get(species_index, 0) + 1

    return data

def parse_ion_file(filepath):
    """Parses a Conquest_ion_input file (or similar .ion) to get basis set info."""
    data = {}
    if not os.path.exists(filepath):
        return data

    with open(filepath, 'r') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if 'Atom.BasisSize' in line:
            parts = re.split(r'\s+', line, maxsplit=1)
            if len(parts) == 2:
                data['basis_size'] = parts[1]

    return data

def combine_data(conquest_input_path, coords_path, ion_paths):
    """Combines parsing of all files into a structured dictionary."""
    input_data = parse_conquest_input(conquest_input_path)
    coords_data = parse_structure_file(coords_path)

    # Try to map species indices to labels
    species_labels = {}
    if 'General.NumberOfSpecies' in input_data:
        try:
            with open(conquest_input_path, 'r') as f:
                content = f.read()
                # Find block ChemicalSpeciesLabel
                match = re.search(r'%block ChemicalSpeciesLabel(.*?)(?:%endblock|\Z)', content, re.DOTALL | re.IGNORECASE)
                if match:
                    block_lines = match.group(1).strip().split('\n')
                    for line in block_lines:
                        parts = line.split()
                        if len(parts) >= 3:
                            idx = parts[0]
                            label = parts[2]
                            species_labels[idx] = label
        except Exception:
            pass

    mapped_counts = {}
    for idx, count in coords_data['species_counts'].items():
        label = species_labels.get(idx, f"Species {idx}")
        mapped_counts[label] = count

    return {
        'input': input_data,
        'coords': coords_data,
        'species_summary': mapped_counts,
        'ion_files': [parse_ion_file(p) for p in ion_paths]
    }
