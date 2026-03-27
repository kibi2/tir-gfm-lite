#!/bin/sh
set -u

tir-gfm-lite help > gen.txt 2>&1
grep -vE '^tir-gfm-lite [0-9]' gen.txt > out-actual.txt || true