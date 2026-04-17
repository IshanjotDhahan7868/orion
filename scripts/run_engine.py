from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
ROOT_PARENT = ROOT_DIR.parent

for path in (ROOT_PARENT, ROOT_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

import uvicorn


def main() -> None:
    host = os.getenv("ORION_ENGINE_HOST", "0.0.0.0")
    port = int(os.getenv("ORION_ENGINE_PORT", "8000"))
    reload = os.getenv("ORION_ENGINE_RELOAD", "0") == "1"
    uvicorn.run("api.app:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
