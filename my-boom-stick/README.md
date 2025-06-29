# my-boom-stick

This repository contains a pair of diagnostic utilities for Windows.

* `system_diagnostics.py` — checks Secure Boot, updates and disk space.
* It can optionally schedule the next boot in Safe Mode.
* Pass `--undo` to remove the Safe Mode boot flag.

Both scripts require Python 3 and the `psutil` package.

```bash
python system_diagnostics.py           # Run diagnostics only
python system_diagnostics.py --apply   # Schedule Safe Mode boot
python system_diagnostics.py --undo    # Cancel Safe Mode boot
```

Logs are written to the `logs` directory with a timestamped filename.
