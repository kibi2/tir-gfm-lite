#!/bin/sh
set -eu
exec > out-actual.txt 2>&1

tir-gfm-lite unparse out < "$TIRENVI_ROOT/tests/data/complex.tir"

rm -f out-actual.txt
mv out out-actual.txt