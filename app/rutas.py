import sys
from pathlib import Path


def _congelado() -> bool:
    return bool(getattr(sys, "frozen", False))


def datos_dir() -> Path:
    if _congelado():
        return Path(sys.executable).resolve().parent / "data"
    return Path(__file__).resolve().parents[1] / "data"


def assets_dir() -> Path:
    if _congelado():
        return Path(sys._MEIPASS) / "assets"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[1] / "app" / "assets"
