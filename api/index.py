"""api/index.py - Entry point serverless para Vercel en Python puro.
Permite ejecutar C.C.I. SYSTEM Web como Serverless WSGI en Vercel.
Autora: Camila Carolina Ianni
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from web.app import app
