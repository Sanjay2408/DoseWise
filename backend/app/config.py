"""Where DoseWise keeps its data.

Locally everything lives in app/storage/. Serverless hosts such as Vercel only
allow writes under /tmp, so the data directory moves there automatically.
Set DOSEWISE_DATA_DIR to override either default.
"""

import os
from pathlib import Path

_DEFAULT_DIR = Path(__file__).resolve().parent / "storage"


def _data_dir() -> Path:
    configured = os.environ.get("DOSEWISE_DATA_DIR", "").strip()
    if configured:
        return Path(configured)
    if os.environ.get("VERCEL"):
        return Path("/tmp/dosewise")
    return _DEFAULT_DIR


DATA_DIR = _data_dir()
