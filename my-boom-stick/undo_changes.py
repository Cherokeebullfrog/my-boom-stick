"""Utility to revert Safe Mode boot configuration."""

import subprocess


def undo_safe_mode():
    """Remove the Safe Mode boot flag."""
    subprocess.run(["bcdedit", "/deletevalue", "{current}", "safeboot"])


if __name__ == "__main__":
    undo_safe_mode()
    print("Safe Mode boot flag removed. You can reboot normally.")
