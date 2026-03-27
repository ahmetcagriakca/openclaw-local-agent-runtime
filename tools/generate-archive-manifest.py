#!/usr/bin/env python3
"""Generate archive manifest for a sprint.

Usage: python tools/generate-archive-manifest.py 19
"""
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/generate-archive-manifest.py <sprint-number>")
        sys.exit(1)

    sprint = sys.argv[1]
    sprint_dir = Path(f"docs/sprints/sprint-{sprint}")
    evidence_dir = Path(f"evidence/sprint-{sprint}")

    if not sprint_dir.is_dir():
        print(f"FAIL: {sprint_dir} not found")
        sys.exit(1)

    manifest = {
        "sprint": int(sprint),
        "generated_at": None,  # filled at runtime
        "moves": []
    }

    # Sprint docs → archive
    archive_base = f"docs/archive/sprints/sprint-{sprint}"
    if sprint_dir.is_dir():
        for f in sorted(sprint_dir.iterdir()):
            if f.is_file():
                manifest["moves"].append({
                    "source": str(f).replace("\\", "/"),
                    "destination": f"{archive_base}/{f.name}",
                    "type": "sprint-doc"
                })

    # Evidence → archive
    evidence_archive = f"docs/archive/evidence/sprint-{sprint}"
    if evidence_dir.is_dir():
        for f in sorted(evidence_dir.iterdir()):
            if f.is_file():
                manifest["moves"].append({
                    "source": str(f).replace("\\", "/"),
                    "destination": f"{evidence_archive}/{f.name}",
                    "type": "evidence"
                })

    print(json.dumps(manifest, indent=2))
    print(f"\n# Total files: {len(manifest['moves'])}", file=sys.stderr)


if __name__ == "__main__":
    main()
