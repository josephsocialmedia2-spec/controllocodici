from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path:
    sys.path.insert(0, str(BASE))

from f1.audio import default_indices, list_devices


def main() -> int:
    microphones, customer_devices = list_devices()
    default_mic, default_customer = default_indices()
    print("MICROFONI JOSEPH")
    print("=" * 60)
    for device in microphones:
        marker = "  < PREDEFINITO" if device.index == default_mic else ""
        print(f"{device.index:3d} | {device.label}{marker}")
    print("\nSORGENTI CLIENTE")
    print("=" * 60)
    for device in customer_devices:
        marker = "  < SUGGERITO" if device.index == default_customer else ""
        print(f"{device.index:3d} | {device.label}{marker}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
