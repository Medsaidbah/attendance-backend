#!/usr/bin/env python3
"""Test runner for the attendance backend."""
import subprocess
import sys
import os


def run_tests():
    """Run all tests."""
    # Change to the app directory to run tests
    os.chdir("app")

    try:
        # Run pytest with verbose output
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "students/test_import.py",
                "-v",
                "--tb=short",
            ],
            check=True,
        )

        print("\n✅ All tests passed!")
        return 0

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Tests failed with exit code {e.returncode}")
        return e.returncode
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
