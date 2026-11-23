#!/usr/bin/env bash
# Build our own VocalTractLab engine library (roadmap Step 1).
# Source: VocalTractLabBackend from the vocaltractlab-cython 0.0.17 source package (API 2.4.2, GPL-3.0),
# vendored here so every change to the physics is a reviewable diff.
#   bash engine/build.sh  ->  engine/build/libVocalTractLabApi_bun.so
set -euo pipefail
cd "$(dirname "$0")/VocalTractLabBackend"
mkdir -p ../build
g++ -std=c++17 -O3 -fPIC -shared -D_USE_MATH_DEFINES -D_CRT_SECURE_NO_WARNINGS \
    -I include -I include/VocalTractLabApi \
    src/VocalTractLabBackend/*.cpp src/VocalTractLabApi/VocalTractLabApi.cpp \
    -o ../build/libVocalTractLabApi_bun.so
echo "built engine/build/libVocalTractLabApi_bun.so"
