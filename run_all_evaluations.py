#!/usr/bin/env python3
"""
run_all_evaluations.py - Orquestador y auditor de ejecución integral de pruebas para C.C.I. SYSTEM.

Garantías de auditoría (Revisión v5):
1. Ejecuta las 22 suites mediante un recolector estructurado de `unittest.TestResult` (sin depender de heurísticas de texto).
2. Contabiliza `tests_run`, `passed`, `failures`, `errors` y `skipped` por separado (`passed = tests_run - failures - errors - skipped`).
3. Prohíbe que pruebas omitidas (`skipped > 0`) cuenten como aprobadas: cualquier `skip`, `failure` o `error` invalida la certificación (`exit 1`).
4. Registra en `evaluations_report.json` el desglose individual de cada caso de prueba (`id`, `status`, `elapsed_ms`) y hash SHA-256 de la salida.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time


ROOT_DIR = Path(__file__).resolve().parent

# Batería Central de la Consola, Evolución (Fases 1 a 10) y Subsistema Communities
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
    "test_communities_phase4.py",
    "test_communities_phase5.py",
    "test_communities_phase6.py",
    "test_communities_phase7.py",
    "test_communities_ui.py",
    "test_communities_merge_audit.py",
    "test_game_library_scanner.py",
]

_STRUCTURED_RUNNER_CODE = r"""
import importlib.util
import json
import sys
import time
import unittest
from pathlib import Path

suite_file = Path(sys.argv[1]).resolve()
json_out = Path(sys.argv[2]).resolve()

class StructuredTestResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._case_start = {}
        self.records = []

    def startTest(self, test):
        self._case_start[test.id()] = time.perf_counter()
        super().startTest(test)

    def _elapsed_ms(self, test):
        t0 = self._case_start.get(test.id(), time.perf_counter())
        return round((time.perf_counter() - t0) * 1000.0, 2)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"id": test.id(), "status": "PASS", "elapsed_ms": self._elapsed_ms(test)})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({"id": test.id(), "status": "FAIL", "elapsed_ms": self._elapsed_ms(test)})

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({"id": test.id(), "status": "ERROR", "elapsed_ms": self._elapsed_ms(test)})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.records.append({
            "id": test.id(),
            "status": "SKIP",
            "reason": str(reason),
            "elapsed_ms": self._elapsed_ms(test),
        })

loader = unittest.TestLoader()
suite = loader.loadTestsFromName(suite_file.stem)
runner = unittest.TextTestRunner(stream=sys.stderr, verbosity=1, resultclass=StructuredTestResult)
result = runner.run(suite)

tests_run = int(result.testsRun)
failures = len(result.failures)
errors = len(result.errors)
skipped = len(result.skipped)
passed = max(0, tests_run - failures - errors - skipped)

payload = {
    "tests_run": tests_run,
    "passed": passed,
    "failures": failures,
    "errors": errors,
    "skipped": skipped,
    "test_cases": result.records,
}
json_out.write_text(json.dumps(payload), encoding="utf-8")
sys.exit(0 if (result.wasSuccessful() and skipped == 0 and tests_run > 0) else 1)
"""


def run_suite_process(suite_path: Path) -> dict:
    """Ejecuta una suite de tests mediante `StructuredTestResult` en un subproceso aislado."""
    rel_path = suite_path.relative_to(ROOT_DIR)
    start_t = time.time()

    with tempfile.NamedTemporaryFile(prefix="cci_suite_", suffix=".json", delete=False) as tf:
        json_result_path = Path(tf.name)

    try:
        cmd = [sys.executable, "-c", _STRUCTURED_RUNNER_CODE, str(suite_path), str(json_result_path)]
        env = os.environ.copy()
        env["PYTHONPATH"] = str(ROOT_DIR) + ":" + str(suite_path.parent)

        proc = subprocess.run(cmd, cwd=str(suite_path.parent), capture_output=True, text=True, env=env)
        elapsed = round(time.time() - start_t, 3)
        output = proc.stdout + proc.stderr
        output_sha256 = hashlib.sha256(output.encode("utf-8", errors="replace")).hexdigest()

        if json_result_path.is_file() and json_result_path.stat().st_size > 0:
            structured = json.loads(json_result_path.read_text(encoding="utf-8"))
            tests_run = int(structured.get("tests_run", 0))
            failures = int(structured.get("failures", 0))
            errors = int(structured.get("errors", 0))
            skipped = int(structured.get("skipped", 0))
            passed = tests_run - failures - errors - skipped
            test_cases = structured.get("test_cases", [])
        else:
            tests_run = 0
            failures = 0
            errors = 1
            skipped = 0
            passed = 0
            test_cases = []
    finally:
        try:
            json_result_path.unlink(missing_ok=True)
        except OSError:
            pass

    success = (
        proc.returncode == 0
        and tests_run > 0
        and failures == 0
        and errors == 0
        and skipped == 0
        and passed == tests_run
    )

    return {
        "suite": str(rel_path),
        "returncode": proc.returncode,
        "tests_run": tests_run,
        "passed": passed,
        "failures": failures,
        "errors": errors,
        "skipped": skipped,
        "elapsed": elapsed,
        "success": success,
        "output_sha256": output_sha256,
        "test_cases": test_cases,
        "raw_output": output,
    }


def main():
    print("=" * 88)
    print(" C.C.I. SYSTEM v2.1.0 — PROTOCOLO DE VALIDACIÓN Y REGRESIÓN INTEGRAL (ESTRICTO SIN SKIPS)")
    print("=" * 88)
    print(f"Intérprete Python: {sys.executable}")
    print(f"Raíz del Proyecto: {ROOT_DIR}\n")

    results = []
    missing_suites = 0

    print("[1/2] Ejecutando Suites Principales de la Consola, Evolución y Communities (22 suites)...")
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
                "skipped": 0,
                "elapsed": 0.0,
                "success": False,
                "output_sha256": "",
                "test_cases": [],
                "raw_output": f"Error crítico: El archivo {suite_name} no existe en el repositorio.",
            })
            continue

        res = run_suite_process(suite_path)
        if res["tests_run"] == 0 or res["returncode"] != 0 or res["skipped"] > 0:
            res["success"] = False
            if res["failures"] == 0 and res["errors"] == 0 and res["skipped"] == 0:
                res["errors"] = 1

        sym = "[PASS]" if res["success"] else "[FAIL]"
        print(
            f"  {sym} {suite_name:35} | {res['passed']:3}/{res['tests_run']:<3} pass "
            f"| skip={res['skipped']} | {res['elapsed']:6}s"
        )
        if not res["success"]:
            print(f"    --- DETALLE DE FALLO EN {suite_name} ---")
            for line in res["raw_output"].splitlines()[-40:]:
                print(f"    {line}")
        results.append(res)

    print("\n" + "=" * 88)
    print(" RESUMEN AUDITADO DE PRUEBAS")
    print("=" * 88)
    total_run = sum(r["tests_run"] for r in results)
    total_passed = sum(r["passed"] for r in results)
    total_failed = sum(r["failures"] for r in results)
    total_errors = sum(r["errors"] for r in results)
    total_skipped = sum(r["skipped"] for r in results)
    total_time = round(sum(r["elapsed"] for r in results), 2)

    print(f"{'SUITE':38} | {'RUN':4} | {'PASS':4} | {'FAIL':4} | {'ERR':4} | {'SKIP':4} | {'TIME':6}")
    print("-" * 88)
    for r in results:
        status_marker = "OK" if r["success"] else "FAIL"
        print(
            f"{r['suite']:38} | {r['tests_run']:4} | {r['passed']:4} | "
            f"{r['failures']:4} | {r['errors']:4} | {r['skipped']:4} | {r['elapsed']:6}s [{status_marker}]"
        )

    print("-" * 88)
    print(
        f"TOTAL EJECUTADO: {total_run} tests | APROBADOS: {total_passed} | "
        f"FALLIDOS: {total_failed} | ERRORES: {total_errors} | OMITIDOS (SKIP): {total_skipped} | TIEMPO: {total_time}s"
    )

    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(ROOT_DIR), text=True).strip()
    except Exception:
        git_sha = "unknown"
    try:
        git_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(ROOT_DIR), text=True).strip()
    except Exception:
        git_branch = "unknown"
    try:
        docker_ver = subprocess.check_output(["docker", "--version"], cwd=str(ROOT_DIR), text=True).strip()
    except Exception:
        docker_ver = "unavailable"
    try:
        tracked = subprocess.check_output(["git", "ls-files"], cwd=str(ROOT_DIR), text=True).splitlines()
        tree_hasher = hashlib.sha256()
        for rel in sorted(tracked):
            if rel == "evaluations_report.json":
                continue
            fp = ROOT_DIR / rel
            if fp.is_file():
                tree_hasher.update(rel.encode("utf-8") + b"\x00")
                tree_hasher.update(hashlib.sha256(fp.read_bytes()).digest())
        git_code_tree_sha256 = tree_hasher.hexdigest()
    except Exception:
        git_code_tree_sha256 = "unknown"

    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "git_commit_sha": git_sha,
        "git_code_tree_sha256": git_code_tree_sha256,
        "git_branch": git_branch,
        "python_interpreter": sys.executable,
        "python_version": sys.version,
        "platform": platform.platform(),
        "docker_version": docker_ver,
        "suites_expected": len(CORE_EVOLUTION_SUITES),
        "suites_executed": len(results),
        "missing_suites": missing_suites,
        "total_run": total_run,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "total_errors": total_errors,
        "total_skipped": total_skipped,
        "total_time_seconds": total_time,
        "suites": [
            {
                "suite": r["suite"],
                "returncode": r["returncode"],
                "tests_run": r["tests_run"],
                "passed": r["passed"],
                "failures": r["failures"],
                "errors": r["errors"],
                "skipped": r["skipped"],
                "elapsed": r["elapsed"],
                "success": r["success"],
                "output_sha256": r["output_sha256"],
                "test_cases": r["test_cases"],
            }
            for r in results
        ],
    }
    report_file = ROOT_DIR / "evaluations_report.json"
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n[INFO] Reporte estructurado generado en: {report_file}")

    all_suites_present = (len(results) == len(CORE_EVOLUTION_SUITES) and missing_suites == 0)
    all_tests_passed = (
        total_failed == 0
        and total_errors == 0
        and total_skipped == 0
        and total_run > 0
        and total_passed == total_run
    )
    each_suite_ok = all(
        r["success"] and r["tests_run"] > 0 and r["skipped"] == 0 and r["returncode"] == 0
        for r in results
    )

    if all_suites_present and all_tests_passed and each_suite_ok:
        print(">>> CERTIFICACIÓN EXITOSA: 100% de las suites verificadas con 0 fallos, 0 errores y 0 omisiones (skips).")
        sys.exit(0)
    else:
        print("\n>>> FALLO EN REGRESIÓN O PRUEBA OMITIDA (SKIP): Revise el informe de auditoría.")
        sys.exit(1)


if __name__ == "__main__":
    main()
