"""
Master Test Runner for Metal Slug 1 Mission 1 Arcade Fidelity Overhaul.
Executes all E2E test suites (Tiers 1-4) in headless mode:
- tests/test_terrain_collision.py (R1: Features F1 - F6)
- tests/test_metal_slug_tank.py (R2: Features F7 - F11)
- tests/test_boss_tetsuyuki.py (R3: Features F12 - F15)
- tests/test_hud_presentation.py (R4: Features F16 - F18)
- tests/test_acceptance_headless.py (Acceptance: Feature F19)
"""
import os
import sys
import time
import unittest

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure headless execution before importing pygame
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
from src.config import VIRTUAL_WIDTH, VIRTUAL_HEIGHT
pygame.init()
pygame.display.set_mode((VIRTUAL_WIDTH, VIRTUAL_HEIGHT))

# Import test suites
from tests.test_terrain_collision import TestTerrainCollision
from tests.test_metal_slug_tank import TestMetalSlugTank
from tests.test_boss_tetsuyuki import TestBossTetsuyuki
from tests.test_hud_presentation import TestHUDPresentation
from tests.test_acceptance_headless import TestAcceptanceHeadless
from tests.test_weapons_and_aiming import TestWeaponsAndAiming
from tests.test_modern_architecture import TestModernArchitecture


def run_suite(suite_class):
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(suite_class)
    runner = unittest.TextTestRunner(verbosity=1, stream=sys.stdout)
    start_time = time.time()
    result = runner.run(suite)
    elapsed = time.time() - start_time
    return result, elapsed


def main():
    print("=" * 80)
    print(" METAL SLUG 1 MISSION 1 - E2E TEST SUITE RUNNER")
    print(" Headless Execution: SDL_VIDEODRIVER=dummy, SDL_AUDIODRIVER=dummy")
    print("=" * 80)

    suites = [
        ("R1: Terrain Collision (F1-F6)", TestTerrainCollision),
        ("R2: Metal Slug Tank (F7-F11)", TestMetalSlugTank),
        ("R3: Boss Tetsuyuki (F12-F15)", TestBossTetsuyuki),
        ("R4: HUD & Presentation (F16-F18)", TestHUDPresentation),
        ("R5: Weapons, Aiming & Audio", TestWeaponsAndAiming),
        ("R6: Modern Architecture (FRect/Pymunk/Layers)", TestModernArchitecture),
        ("Acceptance: 2000-Frame Headless (F19)", TestAcceptanceHeadless),
    ]

    total_run = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0
    suite_summaries = []
    overall_start = time.time()

    for name, suite_cls in suites:
        print(f"\n--- Running {name} ---")
        result, elapsed = run_suite(suite_cls)
        run_count = result.testsRun
        fail_count = len(result.failures)
        err_count = len(result.errors)
        pass_count = run_count - fail_count - err_count

        total_run += run_count
        total_passed += pass_count
        total_failed += fail_count
        total_errors += err_count

        suite_summaries.append({
            "name": name,
            "run": run_count,
            "passed": pass_count,
            "failed": fail_count,
            "errors": err_count,
            "time": elapsed,
            "failures": result.failures,
            "errors_list": result.errors
        })

    overall_elapsed = time.time() - overall_start

    print("\n" + "=" * 80)
    print(" TEST EXECUTION SUMMARY")
    print("=" * 80)
    print(f"{'Test Suite':<42} | {'Run':<5} | {'Pass':<5} | {'Fail':<5} | {'Error':<5} | {'Time (s)':<8}")
    print("-" * 80)
    for s in suite_summaries:
        status = "PASS" if s['failed'] == 0 and s['errors'] == 0 else "FAIL"
        print(f"{s['name']:<42} | {s['run']:<5} | {s['passed']:<5} | {s['failed']:<5} | {s['errors']:<5} | {s['time']:<8.2f}")
    print("-" * 80)
    print(f"{'TOTAL':<42} | {total_run:<5} | {total_passed:<5} | {total_failed:<5} | {total_errors:<5} | {overall_elapsed:<8.2f}")
    print("=" * 80)

    # Detailed report of failures/errors if any exist
    if total_failed > 0 or total_errors > 0:
        print("\n" + "=" * 80)
        print(" DETAILED FAILURE & ERROR BREAKDOWN (BASELINE DEFECTS)")
        print("=" * 80)
        for s in suite_summaries:
            if s['failed'] > 0 or s['errors'] > 0:
                print(f"\n>>> {s['name']}:")
                for test_case, tb in s['failures']:
                    print(f"\n[FAIL] {test_case}")
                    first_line = tb.strip().split("\n")[-1]
                    print(f"       Assertion: {first_line}")
                for test_case, tb in s['errors_list']:
                    print(f"\n[ERROR] {test_case}")
                    first_line = tb.strip().split("\n")[-1]
                    print(f"       Exception: {first_line}")
        print("=" * 80)

    pass_rate = (total_passed / total_run * 100.0) if total_run > 0 else 0.0
    print(f"\nOverall Result: {total_passed}/{total_run} Passed ({pass_rate:.1f}%)")

    # Exit code: 0 if all tests passed, 1 if any failed
    sys.exit(0 if (total_failed == 0 and total_errors == 0) else 1)


if __name__ == "__main__":
    main()
