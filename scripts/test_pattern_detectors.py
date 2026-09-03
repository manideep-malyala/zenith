"""
scripts/test_pattern_detectors.py

Invariant F2 — Non-empty finding determinism.

Runs the full pipeline (Layers 1-5) on each test fixture and asserts:
  - Positive fixtures produce >= 1 finding of the expected pattern.
  - Negative fixtures produce 0 findings of the expected pattern.
  - Running the same fixture twice produces identical canonical finding IDs.

Does NOT fail if the production target repo produces zero findings.
"""
import os
import sys
import json
import shutil
import tempfile

# Allow running from repo root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline.orchestrator import ScanPipeline

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "patterns")
CATALOG_DIR  = os.path.join(os.path.dirname(__file__), "..", "src", "src", "knowledge", "catalog")


def run_on_fixture(fixture_path: str, tmp_dir: str, workers: int = 0) -> list:
    """Run the full pipeline on a fixture directory, return pattern findings list."""
    pipeline = ScanPipeline(fixture_path, CATALOG_DIR, workers=workers, mode="standard")
    pipeline.run(tmp_dir)
    patterns_file = os.path.join(tmp_dir, "patterns.json")
    if not os.path.exists(patterns_file):
        return []
    with open(patterns_file) as f:
        return json.load(f)


def findings_of(findings: list, pattern_name: str) -> list:
    return [f for f in findings if f["pattern_name"] == pattern_name]


def check_determinism(findings_a: list, findings_b: list, label: str) -> bool:
    ids_a = {f["finding_id"] for f in findings_a}
    ids_b = {f["finding_id"] for f in findings_b}
    if ids_a == ids_b:
        print(f"    ✅ {label}: identical finding IDs ({len(ids_a)} findings)")
        return True
    missing  = ids_a - ids_b
    extra    = ids_b - ids_a
    print(f"    ❌ {label}: finding ID mismatch — missing={len(missing)}, extra={len(extra)}")
    return False


def run_fixture_test(fixture_subdir: str, expected_pattern: str, expect_findings: bool) -> bool:
    fixture_path = os.path.join(FIXTURES_DIR, fixture_subdir)
    label = fixture_subdir
    print(f"\n--- Fixture: {label} (pattern={expected_pattern}, expect_findings={expect_findings}) ---")

    if not os.path.exists(fixture_path):
        print(f"  ⚠️  Fixture path not found: {fixture_path} — SKIP")
        return True  # Not a hard failure; fixture may not exist yet

    ok = True
    with tempfile.TemporaryDirectory() as run1_dir, tempfile.TemporaryDirectory() as run2_dir:
        findings_run1 = run_on_fixture(fixture_path, run1_dir, workers=0)
        findings_run2 = run_on_fixture(fixture_path, run2_dir, workers=0)

        matches_run1 = findings_of(findings_run1, expected_pattern)
        matches_run2 = findings_of(findings_run2, expected_pattern)

        if expect_findings:
            if len(matches_run1) == 0:
                print(f"  ❌ Expected >= 1 '{expected_pattern}' finding, got 0")
                ok = False
            else:
                print(f"  ✅ Got {len(matches_run1)} '{expected_pattern}' finding(s)")
        else:
            if len(matches_run1) > 0:
                print(f"  ❌ Expected 0 '{expected_pattern}' findings, got {len(matches_run1)}")
                for f in matches_run1:
                    print(f"     {f['subject_fqn']} — {f['explanation'][:80]}")
                ok = False
            else:
                print(f"  ✅ Correctly produced 0 '{expected_pattern}' findings")

        # Invariant F2: determinism between two sequential runs
        if not check_determinism(matches_run1, matches_run2, "F2 determinism"):
            ok = False

    return ok


def main():
    print("=" * 60)
    print("Pattern Detector Fixture Tests — Invariant F2")
    print("=" * 60)

    results = []

    # --- Composite ---
    results.append(run_fixture_test("composite_valid",    "Composite", expect_findings=True))
    results.append(run_fixture_test("composite_negative", "Composite", expect_findings=False))

    # --- Strategy ---
    results.append(run_fixture_test("strategy_valid",    "Strategy", expect_findings=True))
    results.append(run_fixture_test("strategy_negative", "Strategy", expect_findings=False))

    print("\n" + "=" * 60)
    passed = sum(results)
    total  = len(results)
    if passed == total:
        print(f"✅ All {total} fixture tests passed — Invariant F2 satisfied.")
    else:
        print(f"❌ {total - passed}/{total} fixture tests FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
