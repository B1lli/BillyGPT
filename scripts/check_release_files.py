#!/usr/bin/env python3
# coding=utf-8
"""Run the smoke check from a copy of files tracked by Git."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def tracked_files():
    output = subprocess.check_output(
        ["git", "ls-files"],
        cwd=ROOT,
        text=True,
    )
    return [line for line in output.splitlines() if line.strip()]


def copy_tracked_tree(destination):
    for name in tracked_files():
        source = ROOT / name
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def main():
    with tempfile.TemporaryDirectory() as tmp_dir:
        release_root = Path(tmp_dir) / "release"
        release_root.mkdir()
        copy_tracked_tree(release_root)

        env = os.environ.copy()
        env.setdefault("OPENAI_API_KEY", "test-key")
        result = subprocess.run(
            [sys.executable, "scripts/smoke_check.py"],
            cwd=release_root,
            env=env,
            text=True,
            capture_output=True,
        )
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr, file=sys.stderr)
            raise SystemExit(result.returncode)

    print("Release file check passed")


if __name__ == "__main__":
    main()
