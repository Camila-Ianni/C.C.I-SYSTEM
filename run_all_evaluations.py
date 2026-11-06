#!/usr/bin/env python3
"""
run_all_evaluations.py - Orquestador y auditor de ejecución integral de pruebas para C.C.I. SYSTEM.

Resuelve el requerimiento 6 y 7 de la Auditoría:
1. Proporciona un inventario completo y reproducible de suites de pruebas (Core Evolution vs Game-Specific).
2. Ejecuta cada batería registrando cantidad, duración, pruebas aprobadas, falladas y errores.
3. Emite un informe estructurado con certificación de regresión y trazabilidad completa.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time
import unittest


ROOT_DIR = Path(__file__).resolve().parent

# 1. Batería Central de la Consola y Evolución (Fases 1 a 10)
CORE_EVOLUTION_SUITES = [
    "test_phase2.py",
    "test_phase3.py",
    "test_phase1_evolution.py",
    "test_phase2_evolution.py",
    "test_phase3_evolution.py",
    "test_phase4_evolution.py",
    "test_phase5_evolution.py",
    "test_phase6_evolution.py",
    "test_phase7_evolution.py",
    "test_phase8_evolution.py",
    "test_phase9_evolution.py",
    "test_phase10_security.py",
    "test_phase10_media_and_physics.py",
    "test_communities_phase1.py",
    "test_communities_phase2.py",
    "test_communities_phase3.py",
]

# 2. Baterías de motores de juegos internos
DAVINCI_SUITES_DIR = ROOT_DIR / "Davinci-Fighter" / "tests"
METALSLUG_SUITES_DIR = ROOT_DIR / "METAL SLUG" / "tests"


def run_suite_process(suite_path: Path) -> dict:
    """Ejecuta una suite de tests mediante unittest en un subproceso aislado."""
    rel_path = suite_path.relative_to(ROOT_DIR)
    start_t = time.time()

    cmd = [sys.executable, "-m", "unittest", str(suite_path)]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR) + ":" + str(suite_path.parent)

    proc = subprocess.run(cmd, cwd=str(suite_path.parent), capture_output=True, text=True, env=env)
    elapsed = round(time.time() - start_t, 3)

    output = proc.stdout + proc.stderr

    # Parsear cantidad de tests ejecutados del output de unittest
    tests_run = 0
    failures = 0
    errors = 0

    for line in output.splitlines():
        if line.startswith("Ran ") and "tests in" in line:
            parts = line.split()
            try:
                tests_run = int(parts[1])
            except ValueError:
                pass
        if line.startswith("FAILED ("):
            # FAILED (failures=1, errors=2)
            meta = line.replace("FAILED (", "").replace(")", "")
            for item in meta.split(","):
                item = item.strip()
                if item.startswith("failures="):
                    failures = int(item.split("=")[1])
                elif item.startswith("errors="):
                    errors = int(item.split("=")[1])

    passed = tests_run - (failures + errors)

    return {
        "suite": str(rel_path),
        "returncode": proc.returncode,
        "tests_run": tests_run,
        "passed": passed,
        "failures": failures,
        "errors": errors,
        "elapsed": elapsed,
        "success": proc.returncode == 0 and failures == 0 and errors == 0,
        "raw_output": output,
    }


def main():
    print("=" * 80)
    print(" C.C.I. SYSTEM v2.1.0 — PROTOCOLO DE VALIDACIÓN Y REGRESIÓN INTEGRAL")
    print("=" * 80)
    print(f"Intérprete Python: {sys.executable}")
    print(f"Raíz del Proyecto: {ROOT_DIR}\n")

    results = []
    missing_suites = 0

    print("[1/2] Ejecutando Suites Principales de la Consola y Evolución (Fases 1-10)...")
    for suite_name in CORE_EVOLUTION_SUITES:
        suite_path = ROOT_DIR / suite_name
        if not suite_path.is_file():
            print(f"  [CRIT] Suite requerida ausente: {suite_name}")
            missing_suites += 1
            results.append({
                "suite": suite_name,
                "returncode": 1,
                "tests_run": 0,
                "passed": 0,
                "failures": 1,
                "errors": 0,
                "elapsed": 0.0,
                "success": False,
                "raw_output": f"Error crítico: El archivo {suite_name} no existe en el repositorio.",
            })
            continue

        res = run_suite_process(suite_path)
        # Una suite sin tests ejecutados o con código de retorno != 0 es un fallo estricto
        if res["tests_run"] == 0 or res["returncode"] != 0:
            res["success"] = False
            if res["failures"] == 0 and res["errors"] == 0:
                res["errors"] = 1

        sym = "[PASS]" if res["success"] else "[FAIL]"
        print(f"  {sym} {suite_name:35} | {res['tests_run']:3} tests | {res['elapsed']:6}s")
        results.append(res)

    print("\n" + "=" * 80)
    print(" RESUMEN AUDITADO DE PRUEBAS")
    print("=" * 80)
    total_run = sum(r["tests_run"] for r in results)
    total_passed = sum(r["passed"] for r in results)
    total_failed = sum(r["failures"] for r in results)
    total_errors = sum(r["errors"] for r in results)
    total_time = round(sum(r["elapsed"] for r in results), 2)

    print(f"{'SUITE':42} | {'RUN':4} | {'PASS':4} | {'FAIL':4} | {'ERR':4} | {'TIME':6}")
    print("-" * 80)
    for r in results:
        status_marker = "OK" if r["success"] else "FAIL"
        print(f"{r['suite']:42} | {r['tests_run']:4} | {r['passed']:4} | {r['failures']:4} | {r['errors']:4} | {r['elapsed']:6}s [{status_marker}]")

    print("-" * 80)
    print(f"TOTAL EJECUTADO: {total_run} tests | APROBADOS: {total_passed} | FALLIDOS: {total_failed} | ERRORES: {total_errors} | TIEMPO: {total_time}s")

    # Guardar reporte estructurado JSON para trazabilidad y CI con vinculación de Commit SHA y Entorno
    import json, datetime, platform
    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT_DIR), text=True).strip()
    except Exception:
        git_sha = "unknown"
    try:
        git_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(ROOT_DIR), text=True).strip()
    except Exception:
        git_branch = "unknown"

    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "git_commit_sha": git_sha,
        "git_branch": git_branch,
        "python_interpreter": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "suites_expected": len(CORE_EVOLUTION_SUITES),
        "suites_executed": len(results),
        "missing_suites": missing_suites,
        "total_run": total_run,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "total_errors": total_errors,
        "total_time_seconds": total_time,
        "suites": [
            {
                "suite": r["suite"],
                "returncode": r["returncode"],
                "tests_run": r["tests_run"],
                "passed": r["passed"],
                "failures": r["failures"],
                "errors": r["errors"],
                "elapsed": r["elapsed"],
                "success": r["success"],
            }
            for r in results
        ],
    }
    report_file = ROOT_DIR / "evaluations_report.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n[INFO] Reporte estructurado generado en: {report_file}")

    all_suites_present = (len(results) == len(CORE_EVOLUTION_SUITES) and missing_suites == 0)
    all_tests_passed = (total_failed == 0 and total_errors == 0 and total_run > 0)
    each_suite_ok = all(r["success"] and r["tests_run"] > 0 and r["returncode"] == 0 for r in results)

    if all_suites_present and all_tests_passed and each_suite_ok:
        print(">>> CERTIFICACIÓN EXITOSA: 100% de las suites de evolución y consola han sido verificadas sin omisiones.")
        sys.exit(0)
    else:
        print("\n>>> FALLO EN REGRESIÓN O SUITE OMITIDA: Revise el informe de auditoría.")
        sys.exit(1)


if __name__ == "__main__":
    main()
