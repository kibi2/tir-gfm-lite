# tir-gfm-lite

GFM <-> TIR converter backend for tirenvi.

## Install

```bash
pip install tir-gfm-lite
```

## Usage

tir-gfm-lite parse file.md
tir-gfm-lite unparse file.tir

## Behavior

- Table cells do not support multiline content in GFM
- Newlines inside a cell are encoded as `\n` on unparse
- `\n` in GFM is treated as a literal string (not converted back to newline on parse)

## Note

This is a simplified (lite) GFM parser.

- Tables end when a line does not contain a pipe (`|`)
- Not fully compliant with the GFM specification
