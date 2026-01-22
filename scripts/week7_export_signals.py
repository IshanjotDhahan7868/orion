# orion/scripts/week7_export_signals.py
from __future__ import annotations

from orion.signals.exporter import export_signals

def main():
    export_signals(limit=20)

if __name__ == "__main__":
    main()
