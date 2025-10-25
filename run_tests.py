#!/usr/bin/env python3
"""Test runner for the attendance backend."""
import subprocess
import sys


def run_tests() -> int:
    """Run the full test suite and return the exit code."""
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],  # run everything
        check=False,
    )
    if completed.returncode == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code {completed.returncode}")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(run_tests())
