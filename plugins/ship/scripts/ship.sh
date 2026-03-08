#!/usr/bin/env bash
set -euo pipefail

# ship.sh — Stage all, commit, and push in one step.
# Usage: ship.sh [commit message]
# If no message is provided, a default is used.

# Ensure we're in a git repo
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  echo "Error: not inside a git repository." >&2
  exit 1
fi

# Check for changes
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  echo "Nothing to ship — working tree is clean."
  exit 0
fi

# Build commit message
if [ $# -gt 0 ]; then
  MSG="$*"
else
  MSG="Update $(date +%Y-%m-%d)"
fi

# Stage all changes
git add -A

# Commit with co-author trailer
git commit -m "${MSG}

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

# Push — set upstream if needed
BRANCH="$(git symbolic-ref --short HEAD)"
if git config "branch.${BRANCH}.remote" &>/dev/null; then
  git push
else
  git push -u origin HEAD
fi

echo "Shipped on branch ${BRANCH}: $(git log --oneline -1)"
