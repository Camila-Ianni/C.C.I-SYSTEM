#!/usr/bin/env python3
"""
run_tests.py - Test Runner unificado para C.C.I. SYSTEM Virtual Console.
Ejecuta la suite integral de pruebas unitarias y de integración para todas las fases:
- Fase 2: Persistencia SQLite relacional, REST API v1, sincronización desacoplada y Salón de la Fama.
- Fase 3: Auto-actualizador SemVer, manifiesto version.json, y exclusiones de build.
Retorna código de salida 0 en éxito para pipelines de integración continua.
"""
from __future__ import annotations

import sys
import time
import unittest
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def run_all_tests() -> int:
    start_time = time.perf_counter()

    print("=" * 72)
    print("   C.C.I. SYSTEM · SUITE DE PRUEBAS AUTOMATIZADA (ACADEMIC CI/CD)")
    print("   Arquitectura 100% Python Nativo · Autora: Camila Carolina Ianni")
    print("=" * 72)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Cargar fases de testing
    try:
        import test_phase2
        s2 = loader.loadTestsFromModule(test_phase2)
        suite.addTests(s2)
        count_p2 = s2.countTestCases()
    except Exception as exc:
        print(f"❌ Error al cargar test_phase2: {exc}")
        return 1

    try:
        import test_phase3
        s3 = loader.loadTestsFromModule(test_phase3)
        suite.addTests(s3)
        count_p3 = s3.countTestCases()
    except Exception as exc:
        print(f"❌ Error al cargar test_phase3: {exc}")
        return 1

    print(f"\n[Descubrimiento] Suites detectadas:")
    print(f"  • Fase 2 (SQLite Database & REST API v1): {count_p2} pruebas")
    print(f"  • Fase 3 (Auto-Updater & Packaging SemVer): {count_p3} pruebas")
    print(f"  • Total pruebas planificadas: {suite.countTestCases()}\n")

    # Ejecutar runner con captura de resultados
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.perf_counter() - start_time

    print("\n" + "=" * 72)
    print("                      REPORTE DE RESULTADOS")
    print("=" * 72)
    total = result.testsRun
    failed = len(result.failures)
    errored = len(result.errors)
    passed = total - failed - errored
    pass_rate = (passed / total * 100) if total > 0 else 0

    print(f"  Tests Ejecutados: {total}")
    print(f"  Tests Exitosos:   {passed} (OK)")
    print(f"  Fallos:           {failed}")
    print(f"  Errores:          {errored}")
    print(f"  Tasa de Éxito:    {pass_rate:.1f}%")
    print(f"  Tiempo Total:     {elapsed:.3f} segundos")
    print("=" * 72)

    if result.wasSuccessful():
        print("✅ TODAS LAS PRUEBAS PASARON SATISFACTORIAMENTE (EXIT CODE 0)\n")
        return 0
    else:
        print("❌ SE DETECTARON FALLOS EN LA SUITE DE TESTING (EXIT CODE 1)\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
