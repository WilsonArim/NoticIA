#!/bin/bash
# SOTA Skills — Project Scaffolder
# Usage: ./setup.sh /path/to/new-project

set -e

TARGET="${1:?Usage: ./setup.sh /path/to/new-project}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ -d "$TARGET/SKILLS" ]; then
  echo "SKILLS directory already exists in $TARGET. Aborting."
  exit 1
fi

mkdir -p "$TARGET"

# Copy SKILLS, CLAUDE.md, and .claude/settings.json
cp -r "$SCRIPT_DIR/SKILLS" "$TARGET/SKILLS"
cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET/CLAUDE.md"
mkdir -p "$TARGET/.claude"
cp "$SCRIPT_DIR/.claude/settings.json" "$TARGET/.claude/settings.json"

echo "SOTA Skills installed in: $TARGET"
echo ""
echo "Structure:"
echo "  $TARGET/CLAUDE.md          <- Edit project conventions here"
echo "  $TARGET/.claude/settings.json"
echo "  $TARGET/SKILLS/            <- 33 skills, 7 phases"
echo ""
echo "Next steps:"
echo "  1. Edit CLAUDE.md to set your tech stack and conventions"
echo "  2. Start coding — Claude will auto-route skills"
