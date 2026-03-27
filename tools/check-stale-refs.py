#!/usr/bin/env python3
"""Check for stale file references in active docs.

Usage: python tools/check-stale-refs.py
"""
import re
import sys
from pathlib import Path

# Docs to scan for references
SCAN_DIRS = ["docs/ai", "docs/shared"]
SCAN_FILES = ["CLAUDE.md"]
# Patterns to match file references
REF_PATTERNS = [
    re.compile(r'`([a-zA-Z][\w/.-]+\.\w+)`'),  # `path/to/file.ext`
    re.compile(r'\[.*?\]\((\./[^\)]+)\)'),  # [text](./path)
    re.compile(r'\[.*?\]\(([a-zA-Z][\w/.-]+\.(?:md|py|sh|yml|yaml|json|txt))\)'),  # [text](file.ext)
]
# Extensions that indicate a file reference
FILE_EXTENSIONS = {'.md', '.py', '.sh', '.yml', '.yaml', '.json', '.txt', '.ps1'}


def find_docs():
    """Find all docs to scan."""
    docs = []
    for d in SCAN_DIRS:
        p = Path(d)
        if p.is_dir():
            docs.extend(p.rglob("*.md"))
    for f in SCAN_FILES:
        p = Path(f)
        if p.exists():
            docs.append(p)
    return docs


def extract_refs(filepath):
    """Extract file references from a document."""
    refs = []
    content = filepath.read_text(encoding='utf-8', errors='replace')
    for i, line in enumerate(content.splitlines(), 1):
        for pattern in REF_PATTERNS:
            for match in pattern.finditer(line):
                ref = match.group(1)
                # Skip URLs, anchors, common false positives
                if ref.startswith('http') or ref.startswith('#') or ref.startswith('mailto:'):
                    continue
                # Only check refs with file extensions
                if Path(ref).suffix in FILE_EXTENSIONS:
                    refs.append((i, ref))
    return refs


def main():
    docs = find_docs()
    print(f"Scanning {len(docs)} documents for stale references...")
    print()

    stale = []
    checked = 0

    for doc in docs:
        refs = extract_refs(doc)
        for line_num, ref in refs:
            checked += 1
            # Resolve relative to doc's parent or repo root
            candidates = [
                doc.parent / ref,
                Path(ref),
            ]
            found = any(c.exists() for c in candidates)
            if not found:
                stale.append((doc, line_num, ref))

    print(f"References checked: {checked}")
    print(f"Stale references: {len(stale)}")
    print()

    if stale:
        print("STALE REFERENCES:")
        for doc, line_num, ref in stale:
            print(f"  {doc}:{line_num} -> {ref}")
        print()
        print("FAIL: Stale references found")
        sys.exit(1)
    else:
        print("PASS: No stale references found")
        sys.exit(0)


if __name__ == "__main__":
    main()
