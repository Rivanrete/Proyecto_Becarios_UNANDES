"""Arranque de la app (desarrollo y empaquetado PyInstaller).

Doble clic en el .exe o `python BecariosUNANDES.py`: abre el login.
"""
from app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
