#!/usr/bin/env python3

import json
import sys
import re
from typing import Optional

__version__ = "0.1.1"
FORMAT_VERSION = "tir/0.1"

# ------------------------------------------------------------
# parse : GFM lite -> TIR (NDJSON)
# ------------------------------------------------------------


def read_lines(path):
    if path is None or path == "-":
        return sys.stdin.read().splitlines()
    with open(path, encoding="utf-8") as file:
        return file.read().splitlines()


def print_json(obj):
    print(json.dumps(obj, ensure_ascii=False))


def split_row(line: str) -> list[str]:
    if is_table_break(line):
        return []
    # 1. Temporarily escape \|
    placeholder = "\x00"
    line = line.replace(r"\|", placeholder)
    # 2. strip (leading/trailing whitespace)
    line = line.strip()
    # 3. Remove leading/trailing pipes
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    # 4. split
    parts = line.split("|")
    # 5. trim + restore
    cells = [cell.strip().replace(placeholder, "|") for cell in parts]
    return cells


def parse_heaer(header_cells: list[str], next_cells: list[str]) -> int:
    expected_cols = len(header_cells)
    if len(next_cells) != expected_cols:
        return 0
    for cell in next_cells:
        if not re.match(r"^:?-+:?$", cell):
            return 0
    return expected_cols


def get_table_ncol(line: str, next_line: str) -> int:
    header_cells = split_row(line)
    next_cells = split_row(next_line)
    return parse_heaer(header_cells, next_cells)


def is_table_break(line: str) -> bool:
    return "|" not in line


def print_attr_file() -> None:
    print_json(
        {
            "kind": "attr_file",
            "version": FORMAT_VERSION,
        }
    )


def print_plain(line: str) -> None:
    print_json(
        {
            "kind": "plain",
            "line": line,
        },
    )


def print_grid(line: str, ncol) -> None:
    cells = split_row(line)
    cells = normalize_cells(cells, ncol, "")
    print_json(
        {
            "kind": "grid",
            "row": cells,
        },
    )


def normalize_cells(cells: list[str], ncol, padding) -> list[str]:
    # Adjust number of columns
    if len(cells) < ncol:
        cells += [padding] * (ncol - len(cells))
    elif len(cells) > ncol:
        cells = cells[:ncol]
    return cells


def parse(input_file_path=None):
    lines = read_lines(input_file_path)
    state = "PLAIN"
    print_attr_file()
    iline = 0
    nline = len(lines)
    while iline < nline:
        line = lines[iline]
        if state == "PLAIN":
            next_line = lines[iline + 1] if iline + 1 < nline else ""
            ncol = get_table_ncol(line, next_line)
            if ncol > 0:
                state = "GRID"
                grid_ncol = ncol
                print_grid(line, grid_ncol)
                print_grid(next_line, grid_ncol)
                iline += 1  # consume header + delimiter
            else:
                print_plain(line)
        else:
            if is_table_break(line):
                state = "PLAIN"
                print_plain(line)
            else:
                print_grid(line, grid_ncol)
        iline += 1


# ------------------------------------------------------------
# unparse : TIR (NDJSON) -> GFM
# ------------------------------------------------------------

import sys
from typing import Optional, Iterable


def write_lines(path: Optional[str], lines: Iterable[str]) -> None:
    output = "\n".join(lines)
    if output and not output.endswith("\n"):
        output += "\n"

    if path is None or path == "-":
        sys.stdout.write(output)
    else:
        with open(path, "w", encoding="utf-8") as f:
            f.write(output)


def make_delimiter(ncol):
    return ["---"] * ncol


def escape_cell(cell: str) -> str:
    return cell.replace("|", r"\|")


def format_row(row):
    escaped = [escape_cell(c) for c in row]
    return "| " + " | ".join(escaped) + " |"


def read_records():
    lines = read_lines(None)
    iline = 0
    nline = len(lines)
    records = []
    while iline < nline:
        line = lines[iline]
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exception:
            raise ValueError(f"JSON error at line {iline}: {exception}") from exception
        records.append(record)
        iline += 1
    return records


def get_delimiter(row, next_row, irec) -> tuple[str, int]:
    ncol = parse_heaer(row, next_row)
    if ncol > 0:
        irec += 1
        return format_row(next_row), irec
    else:
        ncol = len(row)
        delimiter = make_delimiter(ncol)
        return format_row(delimiter), irec


def unparse(output_file_path) -> None:
    records = read_records()
    prev_kind = "plain"
    out_lines = []
    irec = 0
    nrec = len(records)
    while irec < nrec:
        record = records[irec]
        kind = record.get("kind")
        if kind == "plain":
            out_lines.append(record.get("line", ""))
        elif kind == "grid":
            row = record.get("row", [])
            out_lines.append(format_row(row))
            if prev_kind != kind:
                next_row = records[irec + 1].get("row") if irec + 1 < nrec else []
                delimiter, irec = get_delimiter(row, next_row, irec)
                out_lines.append(delimiter)
        prev_kind = kind
        irec += 1
    write_lines(output_file_path, out_lines)


# ------------------------------------------------------------
# utilities
# ------------------------------------------------------------


def usage() -> None:
    print(
        f"""tir-gfm-lite {__version__}

usage:
  tir-gfm-lite parse    [file|-]
  tir-gfm-lite unparse  [file|-]
  tir-gfm-lite --version

Options:

If file is omitted or '-', parse reads from stdin.
If file is omitted or '-', unparse writes to stdout.
""",
        file=sys.stderr,
    )


def parse_args(argv):
    return argv


# ------------------------------------------------------------
# pip entry point
# ------------------------------------------------------------


def run(argv) -> int:
    try:
        args = parse_args(argv)
    except Exception as error:
        print(str(error), file=sys.stderr)
        usage()
        return 1

    if not args:
        usage()
        return 1

    if args[0] == "--version":
        print(__version__)
        return 0

    if len(args) not in (1, 2):
        usage()
        return 1

    command = args[0]
    file_argument = args[1] if len(args) == 2 else None

    try:
        if command == "parse":
            parse(file_argument)
        elif command == "unparse":
            unparse(file_argument)
            return 0
        else:
            print(f"unknown sub command: {command}", file=sys.stderr)
            usage()
            return 1

    except Exception as error:
        print(str(error), file=sys.stderr)
        return 1

    return 0
