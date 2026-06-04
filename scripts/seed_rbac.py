"""Seed RBAC roles and permissions into a target (file or DB).

This is a minimal, non-destructive seeder that reads `config/roles.json`
and writes an output file `data/roles_seeded.json` when run with `--apply`.
Run locally to inspect before applying in production.
"""
import argparse
import json
from pathlib import Path


def load_roles(path: Path):
    return json.loads(path.read_text())


def write_seed(output: Path, data):
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/roles.json")
    parser.add_argument("--out", default="data/roles_seeded.json")
    parser.add_argument("--apply", action="store_true", help="Write seed output")
    args = parser.parse_args()

    cfg = Path(args.config)
    if not cfg.exists():
        print(f"Config file not found: {cfg}")
        return 2

    roles = load_roles(cfg)
    print(f"Loaded {len(roles)} roles from {cfg}")
    if args.apply:
        write_seed(Path(args.out), roles)
        print(f"Wrote seed output to {args.out}")
    else:
        print("Dry run: pass --apply to write the seed output")


if __name__ == "__main__":
    raise SystemExit(main())
