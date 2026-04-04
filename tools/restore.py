"""Restore CLI — restore from backup with integrity validation.

Sprint 51 Task 51.2 (B-022): Validate manifest SHA-256 before restoring.
Usage: python tools/restore.py BACKUP_DIR [--dry-run] [--force]
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
OC_ROOT = SCRIPT_DIR.parent


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


def validate_backup(backup_dir: Path) -> tuple[bool, list[str]]:
    """Validate backup integrity against manifest.

    Returns (valid, errors).
    """
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        return False, ["manifest.json not found in backup"]

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []

    if manifest.get("version") != 1:
        errors.append(f"Unknown manifest version: {manifest.get('version')}")

    for rel_path, info in manifest.get("files", {}).items():
        file_path = backup_dir / rel_path
        if not file_path.exists():
            errors.append(f"Missing file: {rel_path}")
            continue

        actual_hash = sha256_file(file_path)
        expected_hash = info.get("sha256", "")
        if actual_hash != expected_hash:
            errors.append(
                f"Hash mismatch for {rel_path}: "
                f"expected {expected_hash[:12]}..., got {actual_hash[:12]}..."
            )

        actual_size = file_path.stat().st_size
        expected_size = info.get("size", 0)
        if actual_size != expected_size:
            errors.append(
                f"Size mismatch for {rel_path}: "
                f"expected {expected_size}, got {actual_size}"
            )

    return len(errors) == 0, errors


def restore_backup(backup_dir: Path, dry_run: bool = False) -> tuple[int, list[str]]:
    """Restore files from backup to project root.

    Returns (restored_count, warnings).
    """
    manifest_path = backup_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    warnings = []
    restored = 0

    for rel_path in manifest.get("files", {}):
        src = backup_dir / rel_path
        dest = OC_ROOT / rel_path

        if not src.exists():
            warnings.append(f"Skipped missing source: {rel_path}")
            continue

        if dry_run:
            action = "OVERWRITE" if dest.exists() else "CREATE"
            print(f"  [{action}] {rel_path}")
            restored += 1
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dest))
        restored += 1

    return restored, warnings


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Vezir Platform Restore")
    parser.add_argument("backup_dir", type=str,
                        help="Path to backup directory")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be restored without doing it")
    parser.add_argument("--force", action="store_true",
                        help="Skip integrity check (not recommended)")
    args = parser.parse_args()

    backup_dir = Path(args.backup_dir)
    if not backup_dir.exists():
        print(f"ERROR: Backup directory not found: {backup_dir}")
        sys.exit(1)

    print("Vezir Platform Restore")
    print(f"  Backup: {backup_dir}")
    print(f"  Target: {OC_ROOT}")
    print()

    # Validate first
    if not args.force:
        print("Validating backup integrity...")
        valid, errors = validate_backup(backup_dir)
        if not valid:
            print(f"FAIL: {len(errors)} integrity error(s):")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)
        print("  Integrity: OK")
        print()

    if args.dry_run:
        print("Dry run — no files will be modified:")

    restored, warnings = restore_backup(backup_dir, dry_run=args.dry_run)

    if warnings:
        for w in warnings:
            print(f"  WARNING: {w}")

    action = "Would restore" if args.dry_run else "Restored"
    print(f"\n  {action}: {restored} files")
    print("  Status: OK")


if __name__ == "__main__":
    main()
