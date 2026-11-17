"""Verify the imported instructor host without depending on a sibling checkout."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

MANIFEST = Path("config/lab8_source_manifest.json")
EXTENSIONS = {"src/harness_map.yaml"}  # M4 explicitly adds the eval section here.


def check() -> list[str]:
    source = json.loads(MANIFEST.read_text(encoding="utf-8"))
    root = Path(__file__).resolve().parents[2]
    problems = []
    for name, expected in source["files"].items():
        if name in EXTENSIONS:
            continue
        path = root / name
        if not path.is_file():
            problems.append(f"missing instructor file: {name}")
        elif hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != expected:
            problems.append(f"changed instructor file: {name}")
    original = {name for name in source["files"] if name.startswith("src/lab8/")}
    current = {path.relative_to(root).as_posix() for path in (root / "src/lab8").rglob("*.py")}
    if current != original:
        problems.append("Lab08 Python file inventory differs from the instructor source")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.parse_args()
    problems = check()
    for problem in problems:
        print("FAIL", problem)
    print(f"instructor source: {len(problems)} problem(s)")
    return int(bool(problems))


if __name__ == "__main__":
    raise SystemExit(main())
