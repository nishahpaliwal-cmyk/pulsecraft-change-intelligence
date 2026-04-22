#!/usr/bin/env python3
"""Sanity check: confirms PulseCraft installs and the Python environment is ready."""

import sys

import pulsecraft


def main() -> None:
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print("PulseCraft scaffolding OK — ready for prompt 01.")
    print(f"  Python  : {py_ver}")
    print(f"  Package : pulsecraft {pulsecraft.__version__}")


if __name__ == "__main__":
    main()
