"""Backup CLI — snapshot missions, configs, policies, state files.

Sprint 51 Task 51.2 (B-022): Data safety backup with SHA-256 manifest.
Usage: python tools/backup.py [--output DIR] [--include-missions] [--include-configs]
"""
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OC_ROOT = SCRIPT_DIR.parent
DEFAULT_BACKUP_DIR = OC_ROOT / "backups"

# Files and directories to back up
BACKUP_TARGETS = {
    "configs": [
        "config/capabilities.json",
        "config/policies/",
        "config/templates/",
        "config/schedules/",
    ],
    "state": [
        "logs/mission-history.json",
        "logs/trace-history.json",
        "logs/metric-history.json",
        "logs/dlq.json",
        "logs/services.json",
    ],
    "missions": [
        "logs/missions/",
    ],
}


def sha256_file(path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def create_backup(
    output_dir: Path | None = None,
    include_missions: bool = True,
    include_configs: bool = True,
) -> Path:
    """Create a timestamped backup snapshot.

    Returns path to the created backup directory.
    """
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    if output_dir is None:
        output_dir = DEFAULT_BACKUP_DIR
    backup_path = Path(output_dir) / f"backup-{ts}"
    backup_path.mkdir(parents=True, exist_ok=True)

    manifest = {
        "version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(OC_ROOT),
        "files": {},
    }

    categories = ["state"]
    if include_configs:
        categories.append("configs")
    if include_missions:
        categories.append("missions")

    file_count = 0
    for category in categories:
        for target in BACKUP_TARGETS.get(category, []):
            src = OC_ROOT / target
            if not src.exists():
                continue

            if src.is_dir():
                # Copy directory recursively
                dest_dir = backup_path / target
                dest_dir.mkdir(parents=True, exist_ok=True)
                for item in src.rglob("*"):
                    if item.is_file():
                        rel = item.relative_to(OC_ROOT)
                        dest = backup_path / rel
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(str(item), str(dest))
                        manifest["files"][str(rel)] = {
                            "sha256": sha256_file(item),
                            "size": item.stat().st_size,
                            "category": category,
                        }
                        file_count += 1
            else:
                # Copy single file
                rel = src.relative_to(OC_ROOT)
                dest = backup_path / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(src), str(dest))
                manifest["files"][str(rel)] = {
                    "sha256": sha256_file(src),
                    "size": src.stat().st_size,
                    "category": category,
                }
                file_count += 1

    manifest["file_count"] = file_count

    # Write manifest
    manifest_path = backup_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return backup_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Vezir Platform Backup")
    parser.add_argument("--output", type=str, default=None,
                        help="Output directory for backup")
    parser.add_argument("--include-missions", action="store_true", default=True,
                        help="Include mission files (default: true)")
    parser.add_argument("--no-missions", action="store_true",
                        help="Exclude mission files")
    parser.add_argument("--no-configs", action="store_true",
                        help="Exclude config files")
    args = parser.parse_args()

    output_dir = Path(args.output) if args.output else None
    include_missions = not args.no_missions
    include_configs = not args.no_configs

    print("Vezir Platform Backup")
    print(f"  Source: {OC_ROOT}")
    backup_path = create_backup(output_dir, include_missions, include_configs)
    manifest = json.loads(
        (backup_path / "manifest.json").read_text(encoding="utf-8"))
    print(f"  Backup: {backup_path}")
    print(f"  Files:  {manifest['file_count']}")
    print("  Status: OK")


if __name__ == "__main__":
    main()
