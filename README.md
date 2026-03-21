# tir-gfm-lite

GFM <-> TIR converter backend for tirenvi.

## Install

```bash
pip install tir-gfm-lite
```

## Usage

tir-gfm-lite parse file.md

## Note

This is a simplified (lite) GFM parser.

- Tables end when a line does not contain a pipe (|)
- Alignment has no default in TIR:
  - parse: default -> left
  - unparse: left -> default
- Not fully compliant with the GFM specification
