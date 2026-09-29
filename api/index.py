"""Vercel entrypoint: serves the FastAPI backend as a single serverless function."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app  # noqa: E402,F401
