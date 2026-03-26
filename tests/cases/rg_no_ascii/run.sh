#!/bin/sh
set -eu

rg -n -g '*.py' -g '*.sh' '[^\x00-\x7F]' $TIRENVI_ROOT > out-actual.txt