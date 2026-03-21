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
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def split_row(line: str) -> list[str]:
    # 1. \| を退避
    placeholder = "\x00"
    line = line.replace(r"\|", placeholder)

    # 2. strip（左右の空白）
    line = line.strip()

    # 3. 先頭/末尾の pipe を除去
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]

    # 4. split
    parts = line.split("|")

    # 5. trim + 復元
    result = [p.strip().replace(placeholder, "|") for p in parts]

    return result


def get_delimiter_ncol(line: str, expected_cols: int) -> int:
    cells = split_row(line)
    if len(cells) != expected_cols:
        return 0
    for cell in cells:
        if not re.match(r"^:?-+:?$", cell):
            return 0
    return expected_cols


def get_table_ncol(line: str, next_line: str) -> int:
    if "|" not in line:
        return 0

    header_cells = split_row(line)
    if not header_cells:
        return 0

    return get_delimiter_ncol(next_line, len(header_cells))


def is_table_break(line: str) -> bool:
    return "|" not in line


def parse_align(cell: str) -> str:
    if cell.startswith(":") and cell.endswith(":"):
        return "center"
    if cell.endswith(":"):
        return "right"
    return "left"


def print_attr_file() -> None:
    print(
        json.dumps(
            {
                "kind": "attr_file",
                "version": FORMAT_VERSION,
            },
            ensure_ascii=False,
        )
    )


def print_attr_plain() -> None:
    print(
        json.dumps(
            {
                "kind": "attr_plain",
            },
            ensure_ascii=False,
        )
    )


def print_attr_grid(line: str) -> None:
    delimiter_cells = split_row(line)
    columns = [{"align": parse_align(c)} for c in delimiter_cells]
    print(
        json.dumps(
            {
                "kind": "attr_grid",
                "columns": columns,
            },
            ensure_ascii=False,
        )
    )


def print_plain(line: str) -> None:
    print(
        json.dumps(
            {
                "kind": "plain",
                "line": line,
            },
            ensure_ascii=False,
        )
    )


def print_grid(line: str, ncol) -> None:
    cells = split_row(line)
    cells = normalize_cells(cells, ncol, "")
    print(
        json.dumps(
            {
                "kind": "grid",
                "row": cells,
            },
            ensure_ascii=False,
        )
    )


def normalize_cells(cells: list[str], ncol, padding) -> list[str]:
    # 列数調整
    if len(cells) < ncol:
        cells += [padding] * (ncol - len(cells))
    elif len(cells) > ncol:
        cells = cells[:ncol]
    return cells


def parse(input_file_path=None):
    lines = read_lines(input_file_path)
    state = "INIT"
    print_attr_file()
    iline = 0
    nline = len(lines)

    while iline < nline:
        line = lines[iline]
        next_line = lines[iline + 1] if iline + 1 < nline else ""
        ncol = get_table_ncol(line, next_line)
        if ncol > 0:
            grid_ncol = ncol
            state = "GRID"
            print_attr_grid(next_line)
            print_grid(line, grid_ncol)
            iline += 1  # header + delimiterを消費
        elif is_table_break(line):
            if state != "PLAIN":
                print_attr_plain()
            state = "PLAIN"
            print_plain(line)
        elif state == "INIT":
            state = "PLAIN"
            print_attr_plain()
            print_plain(line)
        elif state == "PLAIN":
            print_plain(line)
        elif state == "GRID":
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


def make_delimiter(columns):
    result = []
    for col in columns:
        align = col.get("align", "left")

        if align == "left":
            result.append("---")
        elif align == "right":
            result.append("---:")
        elif align == "center":
            result.append(":---:")
        else:
            result.append("---")

    return result


def escape_cell(cell: str) -> str:
    return cell.replace("|", r"\|")


def format_row(row):
    escaped = [escape_cell(c) for c in row]
    return "| " + " | ".join(escaped) + " |"


def unparse(output_file_path) -> None:
    import sys
    import json

    state = "INIT"
    columns = []
    out_lines = []
    for iline, line in enumerate(sys.stdin, 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exception:
            raise ValueError(f"JSON error at line {iline}: {exception}") from exception
        kind = record.get("kind")
        if kind == "plain":
            state = "PLAIN"
            out_lines.append(record.get("line", ""))
            columns = []
        elif kind == "attr_grid":
            columns = record.get("columns", [])
        elif kind == "grid":
            row = record.get("row", [])
            if state != "GRID":
                ncol = max(len(row), len(columns))
                row = normalize_cells(row, ncol, "")
                columns = normalize_cells(columns, ncol, {"align": "left"})
                delimiter = make_delimiter(columns)
                out_lines.append(format_row(row))
                out_lines.append(format_row(delimiter))
            else:
                out_lines.append(format_row(row))
            state = "GRID"
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
