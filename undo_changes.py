"""Undo changes made by system_diagnostics.py."""

import subprocess
import platform

IS_WINDOWS = platform.system() == "Windows"


def revert_safe_mode():
    if not IS_WINDOWS:
        print("Safe Mode revert unsupported on this OS")
        return
    try:
        subprocess.check_call(["bcdedit", "/deletevalue", "{current}", "safeboot"])
        print("Safe Mode boot option removed.")
    except Exception as e:
        print(f"Could not revert Safe Mode boot: {e}")


if __name__ == "__main__":
    revert_safe_mode()
