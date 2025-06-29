"""Utility to run system diagnostics on Windows."""

import os
import logging
import argparse
import datetime
import subprocess
import psutil

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = datetime.datetime.now().strftime("log_%Y%m%d_%H%M%S.txt")
log_path = os.path.join(LOG_DIR, log_filename)

logging.basicConfig(
    filename=log_path,
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)


def log_print(message):
    """Print and log a message."""
    print(message)
    logging.info(message)


def check_secure_boot():
    """Return Secure Boot status."""
    try:
        result = subprocess.run(
            ["powershell", "-Command", "(Confirm-SecureBootUEFI)"],
            capture_output=True,
            text=True,
        )
        return "Enabled" if "True" in result.stdout else "Disabled"
    except Exception:
        return "Unknown"


def check_virtualization():
    """Return virtualization status."""
    try:
        output = subprocess.check_output("systeminfo", shell=True).decode()
        if "Virtualization Enabled In Firmware: Yes" in output:
            return "Enabled"
        return "Disabled"
    except Exception:
        return "Unknown"


def check_pending_updates():
    """List pending Windows updates."""
    try:
        result = subprocess.run(
            ["powershell", "-Command", "Get-WindowsUpdate"],
            capture_output=True,
            text=True,
        )
        return result.stdout if result.stdout else "No pending updates"
    except Exception:
        return "Unknown"


def check_startup_programs():
    """Return configured startup programs."""
    try:
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                "Get-CimInstance -ClassName Win32_StartupCommand",
            ],
            capture_output=True,
            text=True,
        )
        return result.stdout
    except Exception:
        return "Failed to get startup programs"


def check_drivers():
    """List drivers older than two years."""
    try:
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                (
                    "Get-WmiObject Win32_PnPSignedDriver | "
                    "Where-Object { $_.DriverDate -lt "
                    "(Get-Date).AddYears(-2) }"
                ),
            ],
            capture_output=True,
            text=True,
        )
        return result.stdout
    except Exception:
        return "Failed to check drivers"


def check_disk_space():
    """Check for disk partitions with less than 15% free space."""
    warnings = []
    for part in psutil.disk_partitions():
        if os.name == 'nt' and 'cdrom' in part.opts:
            continue
        usage = psutil.disk_usage(part.mountpoint)
        percent_free = 100 - usage.percent
        if percent_free < 15:
            warnings.append(
                f"{part.device} low on space: {percent_free:.2f}% free"
            )
    return warnings


def create_restore_point():
    """Create a system restore point."""
    subprocess.run(
        [
            "powershell",
            "-Command",
            (
                "Checkpoint-Computer -Description 'PreDiagnosticsRestorePoint'"
                " -RestorePointType 'MODIFY_SETTINGS'"
            ),
        ]
    )


def restore_point_created_today():
    """Return True if a restore point was created today."""
    try:
        result = subprocess.run(
            [
                "powershell",
                "-Command",
                (
                    "Get-ComputerRestorePoint | "
                    "Where-Object { $_.CreationTime -gt (Get-Date).Date }"
                ),
            ],
            capture_output=True,
            text=True,
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def schedule_safe_mode():
    """Schedule a Safe Mode boot for the next restart."""
    subprocess.run(["bcdedit", "/set", "{current}", "safeboot", "minimal"])


def undo_safe_mode():
    """Remove the Safe Mode boot flag."""
    subprocess.run(["bcdedit", "/deletevalue", "{current}", "safeboot"])


def apply_actions(dry_run=True):
    """Apply scheduled actions unless running in dry-run mode."""
    if dry_run:
        log_print("Dry run: No changes will be made.")
    else:
        schedule_safe_mode()
        log_print("Scheduled Safe Mode boot on next restart.")


def main():
    """Run diagnostics and optionally schedule Safe Mode."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (schedule safe mode boot)",
    )
    parser.add_argument(
        "--undo",
        action="store_true",
        help="Undo Safe Mode boot flag if previously scheduled",
    )
    args = parser.parse_args()

    if args.undo:
        undo_safe_mode()
        log_print("Safe Mode boot flag removed. You can reboot normally.")
        return

    log_print("=== Starting System Diagnostics ===")
    if not restore_point_created_today():
        log_print(
            "⚠️  No restore point created today. "
            "It's recommended to create one."
        )

    log_print(f"Secure Boot: {check_secure_boot()}")
    log_print(f"Virtualization: {check_virtualization()}")
    log_print("Checking for Windows updates...")
    log_print(check_pending_updates())
    log_print("Startup Programs:")
    log_print(check_startup_programs())
    log_print("Outdated Drivers (2+ years):")
    log_print(check_drivers())
    for warning in check_disk_space():
        log_print(f"⚠️  {warning}")

    apply_actions(dry_run=not args.apply)
    log_print("=== Diagnostics Completed ===")


if __name__ == "__main__":
    main()
