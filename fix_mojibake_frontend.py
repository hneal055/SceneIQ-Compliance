"""Scan and fix mojibake (UTF-8 read as Latin-1/cp1252, re-saved as UTF-8) in frontend source files.

Usage:
  python fix_mojibake_frontend.py          # dry run - report only, changes nothing
  python fix_mojibake_frontend.py --fix    # apply fixes and write files back as UTF-8 (no BOM)
"""
import sys
from pathlib import Path

ROOT = Path(r"C:\Projects\SceneIQ-Compliance\frontend\src")
EXTS = {".tsx", ".ts", ".css", ".html"}

# Common double-encoded sequences -> correct character
FIXES = {
    "\u00c3\u2014": "\u00d7",        # Ã— -> multiplication sign
    "\u00e2\u20ac\u201d": "\u2014",  # â€" -> em dash
    "\u00e2\u20ac\u201c": "\u2013",  # â€" -> en dash
    "\u00e2\u20ac\u02dc": "\u2018",  # â€˜ -> left single quote
    "\u00e2\u20ac\u2122": "\u2019",  # â€™ -> right single quote
    "\u00e2\u20ac\u0153": "\u201c",  # â€œ -> left double quote
    "\u00e2\u20ac\u009d": "\u201d",  # â€ -> right double quote
    "\u00e2\u20ac\u00a6": "\u2026",  # â€¦ -> ellipsis
    "\u00e2\u20ac\u00a2": "\u2022",  # â€¢ -> bullet
    "\u00c2\u00b7": "\u00b7",        # Â· -> middle dot
    "\u00c2\u00b0": "\u00b0",        # Â° -> degree sign
    "\u00c2\u00a0": " ",             # Â + nbsp -> plain space
    "\u00e2\u0086\u0092": "\u2192",  # â†' -> right arrow
    "\u00e2\u009c\u0093": "\u2713",  # âœ" -> check mark
}

apply_fix = "--fix" in sys.argv
total_files = 0
total_hits = 0

for path in sorted(ROOT.rglob("*")):
    if path.suffix.lower() not in EXTS or not path.is_file():
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    original = text
    file_hits = []
    for bad, good in FIXES.items():
        count = text.count(bad)
        if count:
            file_hits.append((repr(bad), repr(good), count))
            text = text.replace(bad, good)
    if file_hits:
        total_files += 1
        rel = path.relative_to(ROOT)
        print(f"\n{rel}")
        for bad, good, count in file_hits:
            total_hits += count
            print(f"  {bad} -> {good}  x{count}")
        if apply_fix:
            path.write_text(text, encoding="utf-8", newline="")
            print("  WRITTEN (utf-8, no BOM)")

    # Report any leftover suspicious sequences not in the map
    for i, line in enumerate(text.splitlines(), 1):
        if "\u00c2" in line or "\u00e2\u20ac" in line or "\u00c3" in line:
            print(f"  UNMAPPED leftover at {path.relative_to(ROOT)}:{i}: {line.strip()[:100]}")

print(f"\n{'FIXED' if apply_fix else 'DRY RUN'}: {total_hits} occurrences in {total_files} files")
if not apply_fix and total_hits:
    print("Run again with --fix to apply.")
