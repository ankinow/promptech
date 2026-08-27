#!/usr/bin/env python3
"""Entrypoint único do command center — usado pelo autostart e hotkey F9."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from promptech_cc.app import main  # noqa: E402

if __name__ == "__main__":
    main()
