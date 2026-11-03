"""
test_phase3.py - Suite de pruebas unitarias para la Fase 3 de C.C.I. SYSTEM:
- Sistema de versionado canónico (version.json)
- Módulo de actualización automática en segundo plano (cci_updater.py)
- Endpoint de versiones /api/v1/version (web/app.py)
- Reglas de empaquetado y exclusión de datos de fábrica (build_distribution.py)
"""
import json
import time
import unittest
import urllib.request
from pathlib import Path

import build_distribution
import cci_updater


class TestPhase3PackagingAndUpdater(unittest.TestCase):
    def test_01_version_json_validity(self):
        v_file = Path("version.json")
        self.assertTrue(v_file.exists(), "version.json debe existir en la raíz")
        data = json.loads(v_file.read_text(encoding="utf-8"))
        self.assertEqual(data["version"], "2.1.0")
        self.assertIn("downloads", data)
        self.assertIn("mac", data["downloads"])
        self.assertIn("windows", data["downloads"])
        self.assertIn("Escuela Da Vinci", data["academic_project"])

    def test_02_semver_parsing_and_comparison(self):
        self.assertEqual(cci_updater.parse_semver("2.1.0"), (2, 1, 0))
        self.assertEqual(cci_updater.parse_semver("v3.0"), (3, 0, 0))
        self.assertEqual(cci_updater.parse_semver("1"), (1, 0, 0))

        # Comparaciones
        self.assertTrue(cci_updater.is_newer_version("2.2.0", "2.1.0"))
        self.assertTrue(cci_updater.is_newer_version("3.0.0", "2.9.9"))
        self.assertFalse(cci_updater.is_newer_version("2.1.0", "2.1.0"))
        self.assertFalse(cci_updater.is_newer_version("2.0.9", "2.1.0"))

    def test_03_http_version_endpoint(self):
        req = urllib.request.Request("http://127.0.0.1:5050/api/v1/version")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["version"], "2.1.0")
            self.assertIn("changelog", data)
            self.assertTrue(len(data["changelog"]) >= 3)

    def test_04_updater_sync_check(self):
        res = cci_updater.check_for_updates_sync("http://127.0.0.1:5050")
        self.assertEqual(res["status"], "up_to_date")
        self.assertFalse(res["has_update"])
        self.assertEqual(res["current_version"], "2.1.0")

    def test_05_updater_background_check(self):
        cb_results = []
        t = cci_updater.check_for_updates_background(
            api_url="http://127.0.0.1:5050",
            on_result=lambda r: cb_results.append(r)
        )
        t.join(timeout=3.0)
        self.assertEqual(len(cb_results), 1)
        self.assertEqual(cb_results[0]["status"], "up_to_date")

    def test_06_build_distribution_exclusions(self):
        db_path = Path("test.sqlite3")
        self.assertFalse(
            build_distribution._should_include(db_path, "test.sqlite3", "macOS"),
            "Los archivos de base de datos no deben ser empaquetados en releases"
        )
        user_json = Path(".cci-user-data/users/cami.json")
        self.assertFalse(
            build_distribution._should_include(user_json, ".cci-user-data/users/cami.json", "macOS"),
            "Los perfiles de usuario deben excluirse para garantizar 0 perfiles de fábrica"
        )
        sys_json = Path(".cci-user-data/system.json")
        self.assertFalse(
            build_distribution._should_include(sys_json, ".cci-user-data/system.json", "macOS")
        )

    def test_07_system_badge(self):
        badge = cci_updater.get_system_badge()
        self.assertIn("v2.1.0", badge)
        self.assertIn("C.C.I. SYSTEM", badge)


if __name__ == "__main__":
    unittest.main()
