#!/usr/bin/env python3
"""Check fresh Method-1/2 constrained runs and raw stress serialization."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def stress_tensors(text):
    lines = text.splitlines()
    values = []
    for i, line in enumerate(lines):
        if 'force: Total stress:' in line:
            values.append(np.array([[float(x) for x in line.split('force: Total stress:')[1].replace('GPa','').split()[:3]],
                                    [float(x) for x in lines[i+1].split()[:3]],
                                    [float(x) for x in lines[i+2].split()[:3]]]))
    return values


def run(binary, directory, lattice, constraint, method=1, pressure=0, static=False, safe=False):
    directory.mkdir(parents=True, exist_ok=False)
    shutil.copy(ROOT / 'testsuite/test_001_bulk_Si_1proc_Diag/Si.ion', directory)
    with (directory / 'coords.dat').open('w') as handle:
        np.savetxt(handle, lattice, fmt='%.14f')
        handle.write('2\n0 0 0 1 T T T\n.25 .25 .25 1 T T T\n')
    (directory / 'Conquest_input').write_text(f'''IO.Title constrained_rotation
IO.Coordinates coords.dat
IO.FractionalAtomicCoords T
IO.Iprint 1
IO.Iprint_MD 2
General.NumberOfSpecies 1
General.PAOFromFiles T
%block ChemicalSpeciesLabel
1 28.086 Si Si.ion
%endblock
AtomMove.TypeOfRun {'static' if static else 'cg'}
AtomMove.OptCell {'F' if static else 'T'}
AtomMove.OptCellMethod {method}
AtomMove.OptCell.Constraint {constraint}
AtomMove.TargetPressure {pressure}
AtomMove.NumSteps 1
AtomMove.MaxForceTol 100
AtomMove.CGLineMin {'safe' if safe else 'backtrack'}
AtomMove.FullStress T
AtomMove.WriteExtXYZ T
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
    env = dict(os.environ, TMPDIR='/tmp', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               VECLIB_MAXIMUM_THREADS='1')
    with (directory / 'mpi.log').open('w') as log:
        subprocess.run([os.environ.get('MPI_LAUNCHER','mpirun'), '-np', '1', str(binary)],
                       cwd=directory, env=env, stdout=log, stderr=subprocess.STDOUT,
                       check=True, timeout=240)
    text = (directory / 'Conquest_out').read_text()
    assert 'Reached SCF tolerance' in text
    tensor = stress_tensors(text)
    assert tensor
    # Check the trajectory also receives the physical tensor, including
    # components forbidden to move by the optimizer's length constraints.
    trajectory = (directory / 'trajectory.xyz').read_text().splitlines()
    match = re.search(r'stress="([^"]+)"', trajectory[-3])
    assert match is not None
    serialized = np.array([float(x) for x in match[1].split()]).reshape(3,3)
    np.testing.assert_allclose(serialized*160.2176634,tensor[-1],atol=2.e-5)
    final = lattice if static else np.loadtxt(directory / 'coord_next.dat', max_rows=3)
    return final, tensor


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary',type=Path,default=ROOT / 'bin/Conquest')
    parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--baseline',action='store_true')
    parser.add_argument('--ratios',action='store_true')
    parser.add_argument('--safe-checks',action='store_true')
    args = parser.parse_args()
    binary = args.binary.resolve()
    rotation = np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]])
    lattice = np.diag([10.,10.5,10.])
    metrics = {}
    methods = [1] if args.baseline else [1,2]
    pressures = [0] if args.baseline else [0,2]
    for method in methods:
        for pressure in pressures:
            label = f'm{method}_p{pressure}'
            a, sa = run(binary,args.results / (label+'_base'),lattice,'a',method,pressure)
            b, sb = run(binary,args.results / (label+'_rotated'),lattice @ rotation.T,'a',method,pressure)
            residual = float(np.max(np.abs(b-a @ rotation.T)))
            metrics[label+'_lattice_rotation_error_bohr'] = residual
            metrics[label+'_fixed_a_error_bohr'] = abs(np.linalg.norm(a[0])-10.)
            assert abs(np.linalg.norm(a[0])-10.) < 1.e-9
            assert np.max(np.abs(a-lattice)) > 1.e-5, 'No relaxation occurred'
            if not args.baseline:
                assert residual < 1.e-6
                np.testing.assert_allclose(sb[0],rotation @ sa[0] @ rotation.T,atol=2.e-6)
                assert abs(sa[0][0,0]) > 1.e-3, 'Physical stress was zeroed'
    if not args.baseline:
        _, unconstrained = run(binary,args.results / 'static_none',lattice,'none',static=True)
        _, constrained = run(binary,args.results / 'static_a',lattice,'a',static=True)
        metrics['static_stress_constraint_error_gpa'] = float(np.max(np.abs(unconstrained[0]-constrained[0])))
        np.testing.assert_allclose(unconstrained[0],constrained[0],atol=1.e-8)
    if args.ratios:
        # Angled orthogonal rotation alone would miss shear coupling.
        skew = np.array([[10.,0.,0.],[-3.,10.5,0.],[1.2,.8,10.]])
        for constraint in ('a/b','a/c','b/c','volume'):
            label = constraint.replace('/','_')
            a, _ = run(binary,args.results / (label+'_skew'),skew,constraint)
            b, _ = run(binary,args.results / (label+'_rotated'),skew @ rotation.T,constraint)
            np.testing.assert_allclose(b,a @ rotation.T,atol=2.e-6)
            before = np.linalg.norm(skew,axis=1)
            after = np.linalg.norm(a,axis=1)
            if constraint == 'volume':
                ratios = after/before
                error = np.max(np.abs(ratios-ratios[0]))
            else:
                i,j = ('abc'.index(x) for x in constraint.split('/'))
                error = abs(after[i]/after[j]-before[i]/before[j])
            metrics[label+'_constraint_error'] = float(error)
            assert error < 1.e-9
    if args.safe_checks:
        for constraint in ('a','a/b','volume'):
            label = constraint.replace('/','_')
            final, _ = run(binary,args.results / ('safe_'+label),lattice,constraint,safe=True)
            lengths = np.linalg.norm(final,axis=1)
            if constraint == 'a':
                error = abs(lengths[0]-10.)
            elif constraint == 'a/b':
                error = abs(lengths[0]/lengths[1]-10./10.5)
            else:
                ratios = lengths/np.diag(lattice)
                error = float(np.max(np.abs(ratios-ratios[0])))
            metrics['safe_'+label+'_constraint_error'] = float(error)
            assert error < 1.e-9
    print(json.dumps(metrics,indent=2))
    (args.results / 'summary.json').write_text(json.dumps(metrics,indent=2)+'\n')


if __name__ == '__main__':
    main()
