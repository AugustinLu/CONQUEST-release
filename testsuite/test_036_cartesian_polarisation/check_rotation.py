#!/usr/bin/env python3
"""Fresh MPI checks of Cartesian polarization, including branch changes."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def run_case(binary, directory, lattice, pol_dir=0):
    directory.mkdir(parents=True, exist_ok=False)
    shutil.copy(ROOT / 'testsuite/test_001_bulk_Si_1proc_Diag/Si.ion', directory)
    fractional = np.array([[0., 0., 0.], [.28, .25, .25]])
    with (directory / 'coords.dat').open('w') as handle:
        np.savetxt(handle, lattice, fmt='%.14f')
        handle.write('2\n')
        for position in fractional @ lattice:
            handle.write(' '.join(f'{x:.14f}' for x in position) + ' 1 T T T\n')
    (directory / 'Conquest_input').write_text(f'''IO.Title polarization_rotation
IO.Coordinates coords.dat
IO.FractionalAtomicCoords F
IO.Iprint 2
General.NumberOfSpecies 1
General.PAOFromFiles T
General.CalcPol T
General.PolDir {pol_dir}
%block ChemicalSpeciesLabel
1 28.086 Si Si.ion
%endblock
AtomMove.TypeOfRun static
AtomMove.FullStress T
Grid.GridCutoff 80
DM.SolutionMethod diagon
minE.SelfConsistent T
minE.SCTolerance 1.0e-8
Diag.MPMesh T
Diag.GammaCentred T
Diag.MPMeshX 1
Diag.MPMeshY 1
Diag.MPMeshZ 1
''')
    env = dict(os.environ, TMPDIR='/tmp', OMP_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', VECLIB_MAXIMUM_THREADS='1')
    with (directory / 'mpi.log').open('w') as log:
        subprocess.run([os.environ.get('MPI_LAUNCHER', 'mpirun'), '-np', '1', str(binary)],
                       cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=180)
    text = (directory / 'Conquest_out').read_text()
    assert 'Reached SCF tolerance' in text
    return text


def parse(text):
    scalar = np.array([float(x) for x in re.findall(
        r'Total polarisation:\s+([-+0-9.eE]+)\s+e / Bohr\^2', text)])
    quantum = np.array([float(x) for x in re.findall(
        r'Quantum of polarisation:\s+([-+0-9.eE]+)\s+e / Bohr\^2', text)])
    match = re.search(r'Cartesian total polarisation:\s+(.+?)\s+e / Bohr\^2', text)
    vector = np.array([float(x) for x in match[1].split()]) if match else None
    energy = float(re.findall(r'Harris-Foulkes energy\s+=\s+([-+0-9.eE]+)', text)[-1])
    return scalar / quantum, vector, energy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', type=Path, default=ROOT / 'bin/Conquest')
    parser.add_argument('--results', type=Path, required=True)
    parser.add_argument('--baseline', action='store_true')
    args = parser.parse_args()
    angle = np.pi / 4
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0],
                         [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
    lattice = np.eye(3) * 10.36
    rotated = lattice @ rotation.T
    c0, p0, e0 = parse(run_case(args.binary.resolve(), args.results / 'base', lattice))
    c1, p1, e1 = parse(run_case(args.binary.resolve(), args.results / 'rotated', rotated))
    delta = c1 - c0
    branch = np.rint(delta)
    metrics = {'energy_residual_ha': abs(e1-e0),
               'coefficient_residual_modulo_quantum': float(np.max(np.abs(delta-branch))),
               'branch_change': branch.tolist()}
    assert metrics['energy_residual_ha'] < 1.e-8
    assert metrics['coefficient_residual_modulo_quantum'] < 1.e-5
    if not args.baseline:
        assert p0 is not None and p1 is not None
        volume = abs(np.linalg.det(lattice))
        np.testing.assert_allclose(p0, c0 @ lattice / volume, atol=1.e-12)
        np.testing.assert_allclose(p1, c1 @ rotated / volume, atol=1.e-12)
        aligned = p1 - branch @ rotated / volume
        metrics['cartesian_rotation_residual_e_per_bohr2'] = float(np.max(np.abs(aligned-rotation @ p0)))
        assert metrics['cartesian_rotation_residual_e_per_bohr2'] < 1.e-7
        for direction in (1, 2, 3):
            single = run_case(args.binary.resolve(), args.results / f'single_{direction}', rotated, direction)
            assert 'Cartesian total polarisation:' not in single
            assert 'Full Cartesian polarisation requires General.PolDir 0.' in single
            assert f'Polarisation contribution (lattice {direction}):' in single
            assert f'Polarisation quantum vector (lattice {direction}):' in single
    print(json.dumps(metrics, indent=2))
    (args.results / 'summary.json').write_text(json.dumps(metrics, indent=2) + '\n')


if __name__ == '__main__':
    main()
