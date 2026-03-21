#!/bin/sh
# When input is provided via stdin, the file name becomes null

set -eu
exec > out-actual.txt 2>&1

tir-gfm-lite parse < "$TIRENVI_ROOT/tests/data/complex.md"
