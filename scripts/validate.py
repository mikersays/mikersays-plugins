#!/usr/bin/env python3
"""Validate the mikersays-plugins marketplace.

Checks plugin manifests, skill frontmatter, and that every plugin appears
consistently across the sync surfaces (all three marketplace.json files,
INSTALL.md, UNINSTALL.md, docs/index.html). Stdlib only.

Exit 0 on success, 1 on any failure. Run from anywhere — paths are resolved
relative to the repo root the script lives in.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ERRORS: list[str] = []

# The maintenance plugin is registered in all three marketplace.json files but
# deliberately omitted from end-user install/uninstall flows and the landing
# page. See plugins/maintenance/skills/sync-docs/SKILL.md.
USER_FACING_EXCLUDE = {"maintenance"}


def err(msg: str) -> None:
    ERRORS.append(msg)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO))
    except ValueError:
        return str(path)


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse a SKILL.md YAML frontmatter block. Handles simple key: value pairs.

    Raises ValueError on malformed input. Doesn't try to be a full YAML parser —
    skill frontmatter is shallow scalar key/value, never nested.
    """
    text = text.lstrip("﻿")  # strip BOM if present
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening '---'")
    body = lines[1:]
    try:
        end = body.index("---")
    except ValueError:
        raise ValueError("missing closing '---'") from None
    fm: dict[str, str] = {}
    for line in body[:end]:
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        fm[key] = value
    return fm


def load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        err(f"{rel(path)}: missing")
    except json.JSONDecodeError as e:
        err(f"{rel(path)}: invalid JSON ({e.msg} at line {e.lineno})")
    return None


def discover_plugins() -> list[Path]:
    return sorted(p for p in (REPO / "plugins").iterdir() if p.is_dir())


def discover_skills(plugin_dir: Path) -> list[Path]:
    skills_dir = plugin_dir / "skills"
    if not skills_dir.is_dir():
        return []
    return sorted(s for s in skills_dir.iterdir() if s.is_dir())


def check_plugin(plugin_dir: Path) -> None:
    name = plugin_dir.name

    # Claude manifest
    cm = plugin_dir / ".claude-plugin" / "plugin.json"
    data = load_json(cm)
    if data is not None:
        if data.get("name") != name:
            err(f"{rel(cm)}: name {data.get('name')!r} != directory {name!r}")
        if not data.get("description"):
            err(f"{rel(cm)}: missing or empty description")
        if "version" not in data:
            err(f"{rel(cm)}: missing version")

    # Codex manifest
    xm = plugin_dir / ".codex-plugin" / "plugin.json"
    data = load_json(xm)
    if data is not None:
        if data.get("name") != name:
            err(f"{rel(xm)}: name {data.get('name')!r} != directory {name!r}")
        if not data.get("description"):
            err(f"{rel(xm)}: missing or empty description")
        if data.get("skills") != "./skills/":
            err(f"{rel(xm)}: skills should be './skills/', got {data.get('skills')!r}")
        if not isinstance(data.get("interface"), dict):
            err(f"{rel(xm)}: missing interface object")

    # Skills
    skill_dirs = discover_skills(plugin_dir)
    if not skill_dirs:
        err(f"{rel(plugin_dir)}: no skills/ subdirectory or empty")
        return
    for sdir in skill_dirs:
        smd = sdir / "SKILL.md"
        if not smd.exists():
            err(f"{rel(smd)}: missing")
            continue
        try:
            fm = parse_frontmatter(smd.read_text())
        except ValueError as e:
            err(f"{rel(smd)}: invalid frontmatter — {e}")
            continue
        if fm.get("name") != sdir.name:
            err(
                f"{rel(smd)}: frontmatter name {fm.get('name')!r} "
                f"!= directory {sdir.name!r}"
            )
        if not fm.get("description"):
            err(f"{rel(smd)}: missing or empty description in frontmatter")
        oyaml = sdir / "agents" / "openai.yaml"
        if oyaml.exists():
            text = oyaml.read_text().strip()
            if not text:
                err(f"{rel(oyaml)}: file is empty")
            elif "interface:" not in text:
                err(f"{rel(oyaml)}: missing 'interface:' key")


def check_marketplace(path: Path, all_names: set[str]) -> None:
    data = load_json(path)
    if data is None:
        return
    if not isinstance(data, dict) or "plugins" not in data:
        err(f"{rel(path)}: missing top-level 'plugins' array")
        return
    entry_names = {p.get("name") for p in data["plugins"] if isinstance(p, dict)}
    for missing in sorted(all_names - entry_names):
        err(f"{rel(path)}: missing entry for plugin {missing!r}")
    for orphan in sorted(entry_names - all_names):
        err(f"{rel(path)}: orphan entry {orphan!r} (no plugins/{orphan}/ directory)")


def check_sync_surfaces(plugin_names: set[str], all_skills: set[str]) -> None:
    install = (REPO / "INSTALL.md").read_text()
    uninstall = (REPO / "UNINSTALL.md").read_text()
    index_html = (REPO / "docs" / "index.html").read_text()
    user_facing = plugin_names - USER_FACING_EXCLUDE

    # Plugin presence — grep-level check, intentionally loose
    for name in sorted(user_facing):
        if name not in install:
            err(f"INSTALL.md: no mention of plugin {name!r}")
        if name not in uninstall:
            err(f"UNINSTALL.md: no mention of plugin {name!r}")
        # docs/index.html PLUGINS array entries look like `id: 'name'`
        if f"id: '{name}'" not in index_html and f'id: "{name}"' not in index_html:
            err(f"docs/index.html: no PLUGINS entry for {name!r}")

    # Skill presence in install/uninstall loops
    user_facing_skills = {
        s
        for s in all_skills
        # crude: exclude maintenance skills by checking each skill's plugin dir
    }
    # Build a precise user-facing skill set
    user_facing_skills = set()
    for pdir in discover_plugins():
        if pdir.name in USER_FACING_EXCLUDE:
            continue
        for sdir in discover_skills(pdir):
            user_facing_skills.add(sdir.name)

    for skill in sorted(user_facing_skills):
        if skill not in install:
            err(f"INSTALL.md: no mention of skill {skill!r}")
        if skill not in uninstall:
            err(f"UNINSTALL.md: no mention of skill {skill!r}")


def main() -> int:
    plugins = discover_plugins()
    if not plugins:
        err("plugins/: no plugin directories found")
        print_results(0, 0)
        return 1

    plugin_names = {p.name for p in plugins}

    for p in plugins:
        check_plugin(p)

    check_marketplace(REPO / ".claude-plugin" / "marketplace.json", plugin_names)
    check_marketplace(REPO / ".codex-plugin" / "marketplace.json", plugin_names)
    check_marketplace(REPO / ".agents" / "plugins" / "marketplace.json", plugin_names)

    for doc in ("CLAUDE.md", "AGENTS.md"):
        if not (REPO / doc).exists():
            err(f"{doc}: missing (required for cross-platform compatibility)")

    all_skills = {s.name for p in plugins for s in discover_skills(p)}
    check_sync_surfaces(plugin_names, all_skills)

    return print_results(len(plugins), len(all_skills))


def print_results(plugin_count: int, skill_count: int) -> int:
    if ERRORS:
        print(f"FAIL: {len(ERRORS)} issue(s)")
        for e in ERRORS:
            print(f"  - {e}")
        return 1
    print(
        f"PASS: {plugin_count} plugin(s), {skill_count} skill(s), "
        "sync surfaces consistent"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
