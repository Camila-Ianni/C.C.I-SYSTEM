#!/usr/bin/env python3
"""tools/audit_catalog_integrity.py - Informe de Auditoría Automatizada para el Catálogo Completo (Sección 9 y 11).

Verifica para cada una de las 90 entradas de MODERN_GAMES_CATALOG y cada paquete instalado:
- game_id: ID único y estable; sin colisiones.
- Título y plataforma: Coherencia entre ficha, plataforma y metadatos del paquete.
- Archivo: Existe, es archivo regular y su formato está permitido para esa plataforma.
- Identidad: Metadatos internos o identificadores verificables coinciden con el título esperado.
- Emulador: Core o emulador compatible y disponible en el sistema operativo.
- Asociación: No comparte ROM/ejecutable con un título diferente.
- Estado: Clasificación explícita y motivo de cualquier bloqueo.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.games.package_validator import ROMPackageIdentityValidator
from backend.games.scanner_service import GameLibraryScannerService


def main() -> int:
    scanner = GameLibraryScannerService.get_instance(ROOT)
    scanner.refresh()
    report = ROMPackageIdentityValidator.audit_entire_catalog(scanner=scanner)

    print("=" * 110)
    print("C.C.I. SYSTEM — AUDITORÍA AUTOMATIZADA DE INTEGRIDAD DE CATÁLOGO Y ASOCIACIONES (90 TÍTULOS)")
    print("=" * 110)
    print(f"Total fichas auditadas : {report['total_catalog_games']}")
    print(f"IDs duplicados         : {len(report['duplicate_ids'])}")
    print(f"ROMs compartidas       : {len(report['shared_roms'])}")
    print(f"Estado de auditoría    : {report['audit_status']}")
    print(f"Asociaciones válidas   : {'SÍ (100%)' if report['all_associations_valid'] else 'NO'}")
    print("-" * 110)
    for k, v in report["status_counts"].items():
        print(f"  {k:26s}: {v}")
    print("-" * 110)

    print(f"{'GAME_ID':52s} | {'PLAT':8s} | {'ESTADO':24s} | {'DETALLE'}")
    print("-" * 110)
    for e in report["entries"]:
        print(
            f"{e['game_id'][:52]:52s} | {str(e['badge'])[:8]:8s} | {e['status']:24s} | {e['reason']}"
        )

    out_json = ROOT / "outputs" / "audit_catalog_report.json"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("=" * 110)
    print(f"Informe JSON guardado en: {out_json.relative_to(ROOT)}")
    return 0 if report["audit_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
