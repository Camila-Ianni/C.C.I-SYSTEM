#!/usr/bin/env python3
"""run_web.py - Inicia el servidor de la Landing Page de C.C.I. SYSTEM."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# Si existe .venv local y no estamos dentro de él, re-ejecutar automáticamente
venv_py = ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
if sys.prefix == sys.base_prefix and venv_py.exists():
    os.execv(str(venv_py), [str(venv_py)] + sys.argv)

from web.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"\n=======================================================")
    print(f"  C.C.I. SYSTEM — LANDING PAGE OFICIAL")
    print(f"  Autora: Camila Carolina Ianni")
    print(f"  Abre en tu navegador: http://127.0.0.1:{port}")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=False)
