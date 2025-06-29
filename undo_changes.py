import subprocess

def undo_safe_mode():
    subprocess.run(["bcdedit", "/deletevalue", "{current}", "safeboot"])

if __name__ == "__main__":
    undo_safe_mode()
    print("Safe Mode boot flag removed. You can reboot normally.")
