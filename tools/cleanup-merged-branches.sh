#!/bin/bash
# Delete remote branches that have been merged to main for a given sprint.
# Dry-run by default. Use --force to actually delete.
#
# Usage: bash tools/cleanup-merged-branches.sh 19
#        bash tools/cleanup-merged-branches.sh 19 --force

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: bash tools/cleanup-merged-branches.sh <sprint-number> [--force]"
  exit 1
fi

SPRINT=$1
FORCE=${2:-""}
PREFIX="sprint-${SPRINT}/"

echo "=== Branch Cleanup for Sprint $SPRINT ==="
echo ""

# Fetch latest
git fetch --prune origin

# Find merged remote branches for this sprint
MERGED_BRANCHES=$(git branch -r --merged origin/main | grep "origin/${PREFIX}" | sed 's|origin/||' | xargs)

if [ -z "$MERGED_BRANCHES" ]; then
  echo "No merged sprint-${SPRINT} branches found on remote."
  exit 0
fi

COUNT=$(echo "$MERGED_BRANCHES" | wc -w)
echo "Found $COUNT merged branch(es):"
for branch in $MERGED_BRANCHES; do
  echo "  - $branch"
done
echo ""

if [ "$FORCE" = "--force" ]; then
  echo "Deleting remote branches..."
  for branch in $MERGED_BRANCHES; do
    git push origin --delete "$branch" 2>&1 && echo "  Deleted: $branch" || echo "  Failed: $branch"
  done
  echo ""
  echo "Done. $COUNT branch(es) deleted."
else
  echo "DRY RUN — no branches deleted."
  echo "Run with --force to actually delete:"
  echo "  bash tools/cleanup-merged-branches.sh $SPRINT --force"
fi
