#!/usr/bin/env bash
set -eo pipefail
if [ -f /usr/share/openfoam/etc/bashrc ]; then
    source /usr/share/openfoam/etc/bashrc
elif [ -f /opt/openfoam1912/etc/bashrc ]; then
    source /opt/openfoam1912/etc/bashrc
fi
case_name="${1:-coarse}"
cd "/analysis/${case_name}"
checkMesh -allGeometry -allTopology > log.checkMesh 2>&1
decomposePar -force > log.decomposePar 2>&1
mpirun --allow-run-as-root --oversubscribe -np 4 simpleFoam -parallel > log.simpleFoam 2>&1
reconstructPar -latestTime > log.reconstructPar 2>&1
postProcess -func writeCellVolumes -latestTime > log.cellVolumes 2>&1
postProcess -func writeCellCentres -latestTime > log.cellCentres 2>&1
foamToVTK -latestTime -noPointValues > log.foamToVTK 2>&1
printf '%s\n' "CFD_RUN_COMPLETE ${case_name}"
