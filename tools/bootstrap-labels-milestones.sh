#!/bin/bash
# Bootstrap GitHub labels and milestones for Vezir Platform
# Idempotent: --force flag on label create, --title check on milestones
# Requires: gh CLI authenticated

set -euo pipefail

echo "=== Bootstrapping Labels ==="

# Sprint/phase labels
gh label create "sprint" --color "0075ca" --description "Sprint-scoped issue" --force
gh label create "phase-6" --color "5319e7" --description "Phase 6" --force

# Type labels
gh label create "automation" --color "d4c5f9" --description "Automation-related" --force
gh label create "tooling" --color "c5def5" --description "Developer tooling" --force
gh label create "github-actions" --color "fef2c0" --description "GitHub Actions workflow" --force
gh label create "github" --color "fbca04" --description "GitHub infrastructure" --force
gh label create "process" --color "bfdadc" --description "Process documentation" --force
gh label create "gate" --color "e4e669" --description "Review gate" --force
gh label create "foundation" --color "0e8a16" --description "Foundation/blocking work" --force
gh label create "security" --color "b60205" --description "Security-related" --force
gh label create "docs" --color "0075ca" --description "Documentation" --force

# Standard labels
gh label create "bug" --color "d73a4a" --description "Something isn't working" --force
gh label create "enhancement" --color "a2eeef" --description "New feature or request" --force
gh label create "good first issue" --color "7057ff" --description "Good for newcomers" --force

echo ""
echo "=== Bootstrapping Milestones ==="

# Create milestones (gh doesn't have --force, so check first)
for sprint in 19 20 21 22; do
  existing=$(gh api repos/:owner/:repo/milestones --jq ".[] | select(.title==\"Sprint $sprint\") | .number" 2>/dev/null || true)
  if [ -z "$existing" ]; then
    gh api repos/:owner/:repo/milestones --method POST -f "title=Sprint $sprint" -f "state=open" -f "description=Sprint $sprint deliverables"
    echo "Created milestone: Sprint $sprint"
  else
    echo "Milestone exists: Sprint $sprint (#$existing)"
  fi
done

echo ""
echo "=== Done ==="
echo "Labels and milestones bootstrapped successfully."
