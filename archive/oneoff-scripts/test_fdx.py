# =============================================================================
# test_fdx.py
# Place this file in the SceneIQ-Compliance project root.
# Run from PowerShell: python test_fdx.py
# Tests the Final Draft importer against sample_breakdown.fdx
# =============================================================================

import sys
import os

# Make sure the project root is on the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.services.production_schedule.importers.fdx_importer import parse_fdx_file

print("=" * 60)
print("Phase 4 — Final Draft Importer Verification")
print("=" * 60)

# Run the parser
scenes = parse_fdx_file("tests/sample_data/sample_breakdown.fdx")

print(f"\nScenes parsed: {len(scenes)}")
print()

# Expected results for verification
expected = [
    {"scene_number": "1", "loc_type": "EXT",  "time_of_day": "DAWN",  "location": "HARBOUR DOCKS",         "cast_count": 2},
    {"scene_number": "2", "loc_type": "INT",  "time_of_day": "DAY",   "location": "POLICE PRECINCT",        "cast_count": 4},
    {"scene_number": "3", "loc_type": "EXT",  "time_of_day": "DAY",   "location": "HARBOUR MASTER OFFICE",  "cast_count": 2},
    {"scene_number": "4", "loc_type": "EXT",  "time_of_day": "NIGHT", "location": "BROOKLYN WATERFRONT",    "cast_count": 2},
    {"scene_number": "5", "loc_type": "INT",  "time_of_day": "NIGHT", "location": "BROOKLYN WAREHOUSE",     "cast_count": 3},
    {"scene_number": "6", "loc_type": "EXT",  "time_of_day": "DUSK",  "location": "HARBOUR DOCKS",          "cast_count": 1},
]

all_passed = True

for i, scene in enumerate(scenes):
    exp = expected[i] if i < len(expected) else {}
    checks = {
        "scene_number" : scene.scene_number == exp.get("scene_number"),
        "loc_type"     : scene.location_type == exp.get("loc_type"),
        "time_of_day"  : scene.time_of_day == exp.get("time_of_day"),
        "location"     : scene.location is not None,
        "cast_count"   : len(scene.cast) == exp.get("cast_count", 0),
    }

    status = "PASS" if all(checks.values()) else "FAIL"
    if status == "FAIL":
        all_passed = False

    print(f"  Scene {scene.scene_number}: {status}")
    print(f"    location_type : {scene.location_type}")
    print(f"    time_of_day   : {scene.time_of_day}")
    print(f"    location      : {scene.location}")
    print(f"    cast          : {scene.cast}")
    print(f"    title         : {scene.title[:60] if scene.title else None}")

    # Check failed details
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"    FAILED checks : {failed}")
    print()

# Bad path test
print("Bad-path test (missing file):")
result = parse_fdx_file("tests/sample_data/does_not_exist.fdx")
bad_path_ok = result == []
print(f"  Missing file -> [] : {'PASS' if bad_path_ok else 'FAIL'}")
print()

# V.O. / O.S. cleaning test
print("Parenthetical cleaning test:")
scene2 = scenes[1] if len(scenes) > 1 else None
if scene2:
    dispatch_clean = "DISPATCH" in scene2.cast
    dispatch_dirty = "DISPATCH (V.O.)" not in scene2.cast
    print(f"  DISPATCH in cast (not DISPATCH (V.O.)): {'PASS' if dispatch_clean and dispatch_dirty else 'FAIL'}")
print()

print("=" * 60)
if all_passed and bad_path_ok:
    print("All tests passed. Phase 4 complete.")
else:
    print("Some tests failed — check output above.")
print("=" * 60)
