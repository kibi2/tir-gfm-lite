#!/usr/bin/env python3

import json
import sys
import re
from typing import Optional, Iterable, Any

FORMAT_VERSION = "tir/0.1"
TABLE_DELIM_RE = re.compile(r"^:?-+:?$")

# ------------------------------------------------------------
# parse : GFM lite -> TIR (NDJSON)
# ------------------------------------------------------------


def read_lines(path: Optional[str]) -> list[str]:
    if path is None or path == "-":
        return sys.stdin.read().splitlines()
    with open(path, encoding="utf-8") as file:
        return file.read().splitlines()


def print_json(obj: dict[str, Any]) -> None:
    print(json.dumps(obj, ensure_ascii=False))


def split_row(line: str) -> list[str]:
    if "|" not in line:
        return []
    # 1. Temporarily escape \|
    placeholder = "\0PIPE\0"
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
    cells = []
    for cell in parts:
        cell = cell.strip()
        cell = cell.replace(placeholder, "|")
        cells.append(cell)
    return cells


def detect_table_header(header_cells: list[str], next_cells: list[str]) -> int:
    ncol = len(header_cells)
    if len(next_cells) != ncol:
        return 0
    for cell in next_cells:
        if not TABLE_DELIM_RE.match(cell):
            return 0
    return ncol


def detect_table(line: str, next_line: str) -> int:
    header_cells = split_row(line)
    next_cells = split_row(next_line)
    return detect_table_header(header_cells, next_cells)


def is_non_table_line(line: str) -> bool:
    return "|" not in line


def print_attr_file() -> None:
    print_json(
        {
            "kind": "attr_file",
            "version": FORMAT_VERSION,
        }
    )


def emit_plain(line: str) -> None:
    print_json(
        {
            "kind": "plain",
            "line": line,
        },
    )


def emit_grid_row(line: str, ncol: int) -> None:
    cells = split_row(line)
    normalize_cells(cells, ncol, "")
    print_json(
        {
            "kind": "grid",
            "row": cells,
        },
    )


def normalize_cells(cells: list[str], ncol: int, padding: str) -> None:
    # Adjust number of columns
    if len(cells) < ncol:
        cells += [padding] * (ncol - len(cells))
    elif len(cells) > ncol:
        del cells[ncol:]


def parse(input_file_path: Optional[str] = None) -> None:
    lines = read_lines(input_file_path)
    print_attr_file()
    state = "PLAIN"
    grid_ncol = 0
    iline = 0
    nline = len(lines)
    while iline < nline:
        line = lines[iline]
        if state == "PLAIN":
            next_line = lines[iline + 1] if iline + 1 < nline else ""
            ncol = detect_table(line, next_line)
            if ncol > 0:
                state = "GRID"
                grid_ncol = ncol
                emit_grid_row(line, grid_ncol)
                emit_grid_row(next_line, grid_ncol)
                iline += 1  # consume header + delimiter
            else:
                emit_plain(line)
        else:
            if is_non_table_line(line):
                state = "PLAIN"
                emit_plain(line)
            else:
                emit_grid_row(line, grid_ncol)
        iline += 1


# ------------------------------------------------------------
# unparse : TIR (NDJSON) -> GFM
# ------------------------------------------------------------


def make_delimiter(ncol: int) -> list[str]:
    return ["---"] * ncol


def encode_newline(cell: str) -> str:
    return cell.replace("\n", r"\n")


def escape_gfm(cell: str) -> str:
    return cell.replace("|", r"\|")


def escape_cell(cell: str) -> str:
    cell = encode_newline(cell)
    cell = escape_gfm(cell)
    return cell


def format_row(row: list[str]) -> str:
    escaped = [escape_cell(c) for c in row]
    return "| " + " | ".join(escaped) + " |"


def read_ndjson_records(lines: list[str]) -> list[dict[str, Any]]:
    records = []
    for iline, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exception:
            raise ValueError(
                f"JSON error at line {iline+1}: {exception}"
            ) from exception
        records.append(record)
    return records


def get_next_row(records: list[dict[str, Any]], irec: int) -> list[str]:
    try:
        return records[irec + 1].get("row", [])
    except IndexError:
        return []


def get_delimiter(records: list[dict[str, Any]], irec: int) -> tuple[str, int]:
    row = records[irec].get("row", [])
    next_row = get_next_row(records, irec)
    ncol = detect_table_header(row, next_row)
    if ncol > 0:
        return format_row(next_row), 1
    else:
        return format_row(make_delimiter(len(row))), 0


def write_lines(path: Optional[str], lines: Iterable[str]) -> None:
    output = "\n".join(lines)
    if output and not output.endswith("\n"):
        output += "\n"

    if path is None or path == "-":
        sys.stdout.write(output)
    else:
        with open(path, "w", encoding="utf-8") as file:
            file.write(output)


def unparse(output_file_path: Optional[str] = None) -> None:
    out = (
        sys.stdout
        if output_file_path in (None, "-")
        else open(output_file_path, "w", encoding="utf-8")
    )

    def emit(line: str):
        out.write(line + "\n")

    lines = read_lines(None)
    records = read_ndjson_records(lines)
    prev_kind = None
    irec = 0
    nrec = len(records)
    while irec < nrec:
        record = records[irec]
        kind = record.get("kind")
        if kind == "plain":
            emit(record.get("line", ""))
        elif kind == "grid":
            row = record.get("row", [])
            emit(format_row(row))
            if prev_kind != "grid":
                delimiter, consumed = get_delimiter(records, irec)
                emit(delimiter)
                irec += consumed
        elif kind == "attr_file":
            pass
        else:
            raise ValueError(f"unknown kind: {kind}")
        prev_kind = kind
        irec += 1
    if out is not sys.stdout:
        out.close()


# ------------------------------------------------------------
# utilities
# ------------------------------------------------------------


from importlib.metadata import version


def get_version():
    return version("tir-gfm-lite")


def usage() -> None:
    print(
        f"""tir-gfm-lite {get_version()}

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
        print(get_version())
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
