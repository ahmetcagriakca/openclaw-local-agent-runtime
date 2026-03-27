#!/bin/bash
# Validates current branch name matches sprint naming convention
BRANCH=$(git rev-parse --abbrev-ref HEAD)

if [[ "$BRANCH" == "main" || "$BRANCH" == "master" ]]; then
  echo "FAIL: Cannot work directly on $BRANCH"
  exit 1
fi

if [[ "$BRANCH" =~ ^sprint-[0-9]+/t[0-9]+(\.[0-9]+)*-.+ ]]; then
  echo "PASS: Branch '$BRANCH' matches naming convention"
  exit 0
else
  echo "FAIL: Branch '$BRANCH' does not match pattern sprint-N/tN.M-slug"
  echo "Expected: sprint-N/tN.M-slug or sprint-N/tN.M.K-slug"
  exit 1
fi
