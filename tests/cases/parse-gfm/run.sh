#!/bin/sh
# Test that newline and tab characters are correctly converted to \n and \t
# When a file name is specified, the absolute path of the file is output
set -eu
exec > out-actual.txt 2>&1

tir-gfm-lite parse "$TIRENVI_ROOT/tests/data/gfm.md" | tir-gfm-lite unparse