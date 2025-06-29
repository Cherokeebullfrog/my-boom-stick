import platform
import psutil
import GPUtil
import subprocess
import re
import argparse
import logging
import builtins
from pathlib import Path
from datetime import datetime, timedelta

IS_WINDOWS = platform.system() == "Windows"

try:
    if IS_WINDOWS:
        import wmi  # type: ignore
    else:
        wmi = None  # type: ignore
except ModuleNotFoundError:
    wmi = None  # type: ignore


LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)

def log_print(*args, **kwargs):
    builtins.print(*args, **kwargs)
    logging.info(" ".join(str(a) for a in args))

print = log_print


def get_system_info():
    print("\n--- SYSTEM INFORMATION ---")
    print(f"OS: {platform.system()} {platform.release()} ({platform.version()})")
    print(f"Architecture: {platform.machine()}")
    print(f"Hostname: {platform.node()}")
    print(f"Processor: {platform.processor()}")
    print(f"CPU Cores: {psutil.cpu_count(logical=False)}, Threads: {psutil.cpu_count(logical=True)}")
    print(f"RAM: {round(psutil.virtual_memory().total / (1024 ** 3), 2)} GB")

    print("\n--- GPU INFORMATION ---")
    try:
        gpus = GPUtil.getGPUs()
        for gpu in gpus:
            print(f"GPU: {gpu.name}")
            print(f"  Driver: {gpu.driver}")
            print(f"  Memory: {gpu.memoryTotal} MB")
    except Exception as e:
        print(f"GPU information unavailable: {e}")


def get_bios_and_mobo_info():
    print("\n--- BIOS & MOTHERBOARD ---")
    if not IS_WINDOWS or wmi is None:
        print("BIOS/Motherboard information unavailable on this platform.")
        return
    try:
        c = wmi.WMI()
        for board in c.Win32_BaseBoard():
            print(f"Motherboard: {board.Product} - {board.Manufacturer}")
        for bios in c.Win32_BIOS():
            print(f"BIOS Version: {bios.SMBIOSBIOSVersion} - {bios.ReleaseDate}")
    except Exception as e:
        print(f"BIOS/Motherboard information unavailable: {e}")


def get_boot_and_security_info():
    print("\n--- BOOT & SECURITY ---")
    secure_boot = None
    virtualization = None
    if not IS_WINDOWS or wmi is None:
        print("Boot/TPM information unavailable on this platform.")
    else:
        try:
            c = wmi.WMI()
            for os_info in c.Win32_OperatingSystem():
                print(f"Boot Time: {os_info.LastBootUpTime}")
            for secure in c.Win32_Tpm():
                print(f"TPM Present: {secure.IsActivated_InitialValue}")
        except Exception as e:
            print(f"Boot/TPM information unavailable: {e}")

    # Secure Boot
    if not IS_WINDOWS:
        print("Secure Boot Enabled: Unsupported on this OS")
    else:
        try:
            output = subprocess.check_output([
                "powershell",
                "-Command",
                "Confirm-SecureBootUEFI"
            ], stderr=subprocess.STDOUT, universal_newlines=True)
            secure_boot = output.strip().lower() == "true"
            print(f"Secure Boot Enabled: {secure_boot}")
        except subprocess.CalledProcessError as e:
            print(f"Secure Boot Enabled: Unknown ({e.output.strip()})")
        except Exception as e:
            print(f"Secure Boot Enabled: Unknown ({e})")

    # Virtualization
    if not IS_WINDOWS or wmi is None:
        print("Virtualization Enabled: Unsupported on this OS")
    else:
        try:
            c = wmi.WMI()
            for cs in c.Win32_ComputerSystem():
                virtualization = bool(cs.HypervisorPresent)
                print(f"Virtualization Enabled: {virtualization}")
        except Exception as e:
            print(f"Virtualization Enabled: Unknown ({e})")

    return secure_boot, virtualization


def check_windows_updates():
    print("\n--- PENDING WINDOWS UPDATES ---")
    if not IS_WINDOWS:
        print("Windows update check unsupported on this OS")
        return
    try:
        cmd = [
            "powershell",
            "-Command",
            "(New-Object -ComObject Microsoft.Update.Session).CreateUpdateSearcher().Search('IsInstalled=0').Updates | Select -ExpandProperty Title"
        ]
        output = subprocess.check_output(cmd, universal_newlines=True)
        updates = [line.strip() for line in output.splitlines() if line.strip()]
        if updates:
            for up in updates:
                print(up)
        else:
            print("No pending updates.")
    except Exception as e:
        print(f"Error retrieving updates: {e}")


def list_installed_drivers():
    print("\n--- INSTALLED DRIVERS ---")
    if not IS_WINDOWS or wmi is None:
        print("Driver information unavailable on this platform.")
        return
    try:
        c = wmi.WMI()
        for driver in c.Win32_PnPSignedDriver():
            print(f"{driver.DeviceName} - Version: {driver.DriverVersion} - Date: {driver.DriverDate}")
    except Exception as e:
        print(f"Driver information unavailable: {e}")


def check_outdated_drivers(years=2):
    print("\n--- POTENTIALLY OUTDATED DRIVERS ---")
    threshold = datetime.now() - timedelta(days=years * 365)
    outdated = []
    if not IS_WINDOWS or wmi is None:
        print("Outdated driver check unsupported on this platform.")
        return outdated
    try:
        c = wmi.WMI()
        for driver in c.Win32_PnPSignedDriver():
            date_str = str(driver.DriverDate).split('.')[0]
            try:
                driver_dt = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                if driver_dt < threshold:
                    outdated.append((driver.DeviceName, driver.DriverVersion, driver_dt.date()))
            except Exception:
                continue
    except Exception as e:
        print(f"Outdated driver check failed: {e}")
        return outdated

    if outdated:
        for name, ver, dt in outdated:
            print(f"{name} - Version: {ver} - Date: {dt}")
    else:
        print(f"No drivers older than {years} years detected.")

    return outdated


def restore_point_created_today() -> bool:
    print("\n--- RESTORE POINT ---")
    if not IS_WINDOWS:
        print("Restore point check unsupported on this OS")
        return True
    try:
        cmd = [
            "powershell",
            "-Command",
            "(Get-ComputerRestorePoint | Sort-Object CreationTime -Descending | Select -First 1).CreationTime"
        ]
        output = subprocess.check_output(cmd, universal_newlines=True).strip()
        if not output:
            print("No restore points detected.")
            return False
        today_str1 = datetime.now().strftime('%m/%d/%Y')
        today_str2 = datetime.now().strftime('%Y-%m-%d')
        if today_str1 in output or today_str2 in output:
            print("Restore point was created today.")
            return True
        print("No restore point created today.")
        return False
    except Exception as e:
        print(f"Could not check restore points: {e}")
        return True


def check_power_plan():
    print("\n--- POWER PLAN ---")
    if not IS_WINDOWS:
        print("Power plan information unsupported on this OS")
        return None
    try:
        output = subprocess.check_output(["powercfg", "/getactivescheme"], universal_newlines=True)
        match = re.search(r":\s*(.+?)\s*\\(", output)
        plan_name = match.group(1) if match else output.strip()
        print(f"Active Power Plan: {plan_name}")
        high_perf = 'high performance' in plan_name.lower()
        if high_perf:
            print("Power plan is set to High Performance.")
        else:
            print("Power plan is NOT set to High Performance.")
        return high_perf
    except Exception as e:
        print(f"Error checking power plan: {e}")
        return None


def list_startup_programs():
    print("\n--- STARTUP PROGRAMS ---")
    programs = []
    if not IS_WINDOWS or wmi is None:
        print("Startup program listing unsupported on this platform.")
        return programs
    try:
        c = wmi.WMI()
        for item in c.Win32_StartupCommand():
            name = item.Name or item.Caption or item.Command
            enabled = True
            try:
                output = subprocess.check_output([
                    "reg",
                    "query",
                    r"HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\StartupApproved\\Run",
                    "/v",
                    name,
                ], universal_newlines=True)
                m = re.search(r"REG_BINARY\s+([0-9A-Fa-f ]+)", output)
                if m:
                    first_byte = int(m.group(1).split()[0], 16)
                    enabled = first_byte == 2
            except subprocess.CalledProcessError:
                pass
            programs.append((name, enabled))
            status = "Enabled" if enabled else "Disabled"
            print(f"{name} - {status}")
    except Exception as e:
        print(f"Startup program listing failed: {e}")
    return programs


def list_heavy_services(cpu_threshold=10.0, mem_threshold=10.0):
    print("\n--- RESOURCE-INTENSIVE SERVICES ---")
    heavy = []
    if IS_WINDOWS and wmi is not None:
        try:
            c = wmi.WMI()
            service_map = {s.ProcessId: s.Name for s in c.Win32_Service(State="Running") if s.ProcessId}
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['pid'] in service_map:
                    cpu = proc.cpu_percent(interval=0.1)
                    mem = proc.memory_percent()
                    if cpu > cpu_threshold or mem > mem_threshold:
                        heavy.append((service_map[proc.info['pid']], cpu, mem))
                        print(f"{service_map[proc.info['pid']]} - CPU {cpu:.1f}% - MEM {mem:.1f}%")
            if not heavy:
                print("No services exceeding thresholds.")
        except Exception as e:
            print(f"Could not analyze services: {e}")
    else:
        try:
            for proc in psutil.process_iter(['name']):
                name = proc.info['name'] or ''
                if 'service' in name.lower() or 'daemon' in name.lower():
                    cpu = proc.cpu_percent(interval=0.1)
                    mem = proc.memory_percent()
                    if cpu > cpu_threshold or mem > mem_threshold:
                        heavy.append((name, cpu, mem))
                        print(f"{name} - CPU {cpu:.1f}% - MEM {mem:.1f}%")
            if not heavy:
                print("No background services exceeding thresholds.")
        except Exception as e:
            print(f"Could not analyze background processes: {e}")
    return heavy


def check_disk_space(threshold=15):
    print("\n--- DISK SPACE ---")
    low = []
    for part in psutil.disk_partitions(all=False):
        if not part.fstype:
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            free_percent = usage.free / usage.total * 100
            print(f"{part.device} ({part.mountpoint}) - Free: {free_percent:.1f}%")
            if free_percent < threshold:
                print("  WARNING: Low disk space!")
                low.append((part.device, free_percent))
        except PermissionError:
            continue
        except Exception as e:
            print(f"{part.device} - Error: {e}")
    return low


def print_system_health_summary(power_high, outdated, virt_enabled, secure_boot_enabled, low_disks, startup_programs, heavy_services):
    print("\n=== SYSTEM HEALTH SUMMARY ===")
    issues = False
    recommendations = []
    if power_high is False:
        print("- Power plan is not High Performance.")
        recommendations.append("Set power plan to High Performance")
        issues = True
    if outdated:
        print(f"- {len(outdated)} outdated drivers detected.")
        recommendations.append("Update outdated drivers")
        issues = True
    if virt_enabled is False or secure_boot_enabled is False:
        if virt_enabled is False:
            print("- Virtualization is disabled.")
            recommendations.append("Enable virtualization in BIOS")
        if secure_boot_enabled is False:
            print("- Secure Boot is disabled.")
            recommendations.append("Enable Secure Boot")
        issues = True
    if low_disks:
        print("- Low disk space on:")
        for dev, free in low_disks:
            print(f"  {dev}: {free:.1f}% free")
        recommendations.append("Clean up disk space")
        issues = True
    if heavy_services:
        print(f"- {len(heavy_services)} services using high resources.")
        recommendations.append("Disable unnecessary services")
        issues = True
    enabled_startups = [p for p in startup_programs if p[1]]
    if enabled_startups:
        print(f"- {len(enabled_startups)} startup programs enabled.")
        recommendations.append("Disable unnecessary startup apps")
        issues = True
    if not issues:
        print("System looks healthy!")
    print("=== END SUMMARY ===")
    return recommendations


def schedule_safe_mode(dry_run: bool):
    if not IS_WINDOWS:
        print("Safe Mode scheduling unsupported on this OS")
        return
    ans = input("Would you like to boot into Safe Mode on next restart as a precaution? [y/N]: ").strip().lower()
    if ans != 'y':
        print("Safe Mode scheduling skipped.")
        return
    cmd = ["bcdedit", "/set", "{current}", "safeboot", "minimal"]
    if dry_run:
        print(f"DRY RUN: Would run: {' '.join(cmd)}")
    else:
        try:
            subprocess.check_call(cmd)
            print("System configured to boot into Safe Mode on next restart.")
        except Exception as e:
            print(f"Failed to schedule Safe Mode boot: {e}")


def apply_actions(actions, dry_run: bool):
    if not actions:
        return
    if dry_run:
        print("\nDRY RUN: The following actions would be taken:")
        for act in actions:
            print(f"  - {act}")
        confirm = input("Proceed with these actions? [y/N]: ").strip().lower()
        if confirm != 'y':
            print("No changes applied.")
        return
    else:
        print("\nApplying recommended actions (simulated)...")
        for act in actions:
            print(f"Simulating: {act}")
        print("Actions completed. (Simulation)")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="System Diagnostics Tool")
    parser.add_argument("--apply", action="store_true", help="Apply recommended actions")
    args = parser.parse_args()

    dry_run = not args.apply

    if dry_run:
        print("Running in DRY RUN mode. No changes will be made.")

    if not IS_WINDOWS:
        print("Non-Windows system detected. Some checks will be skipped.")

    try:
        if not restore_point_created_today():
            print("WARNING: It is recommended to create a restore point before applying changes.")

        get_system_info()
        get_bios_and_mobo_info()
        secure_boot, virt_enabled = get_boot_and_security_info()
        check_windows_updates()
        list_installed_drivers()
        outdated = check_outdated_drivers()
        power_high = check_power_plan()
        startup_programs = list_startup_programs()
        heavy_services = list_heavy_services()
        low_disks = check_disk_space()
        actions = print_system_health_summary(
            power_high,
            outdated,
            virt_enabled,
            secure_boot,
            low_disks,
            startup_programs,
            heavy_services,
        )
        apply_actions(actions, dry_run)
        schedule_safe_mode(dry_run)
    except Exception as e:
        print(f"\n[ERROR] {e}")
