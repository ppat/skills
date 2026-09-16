#!/usr/bin/env python3
"""Check that the Claude Code marketplace manifest agrees with the repository.

Invariants (see CLAUDE.md):
- the `skills` paths across all plugin entries are exactly the `skills/<name>/` folders holding a SKILL.md,
  each listed once; `claude plugin validate` ignores an unlisted folder and so cannot catch drift;
- every plugin entry's `version` equals the release-please manifest version, which proves the release-please
  `extra-files` jsonpath still reaches the entry;
- no `plugin.json` exists: its `version` would silently override the marketplace entry's.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
RELEASE_MANIFEST = ROOT / ".release-please-manifest.json"
IGNORED_DIRS = {".git", "node_modules"}


def main() -> int:
    errors: list[str] = []
    marketplace = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    release_version = json.loads(RELEASE_MANIFEST.read_text(encoding="utf-8"))["."]

    on_disk = {f"./skills/{p.parent.name}" for p in (ROOT / "skills").glob("*/SKILL.md")}
    listed: list[str] = []
    for plugin in marketplace.get("plugins", []):
        name = plugin.get("name", "<unnamed>")
        listed.extend(plugin.get("skills", []))
        if plugin.get("version") != release_version:
            errors.append(
                f"plugin '{name}' version {plugin.get('version')!r} != .release-please-manifest.json "
                f"{release_version!r}; check the extra-files jsonpath in release-please-config.json"
            )

    duplicates = sorted({s for s in listed if listed.count(s) > 1})
    for path in duplicates:
        errors.append(f"{path} is listed more than once in {MARKETPLACE.relative_to(ROOT)}")
    for path in sorted(on_disk - set(listed)):
        errors.append(f"{path} exists on disk but is not listed in {MARKETPLACE.relative_to(ROOT)}")
    for path in sorted(set(listed) - on_disk):
        errors.append(f"{path} is listed in {MARKETPLACE.relative_to(ROOT)} but has no SKILL.md on disk")

    for manifest in ROOT.rglob("plugin.json"):
        if not IGNORED_DIRS.intersection(manifest.relative_to(ROOT).parts):
            errors.append(f"{manifest.relative_to(ROOT)} must not exist: its version overrides marketplace.json")

    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print(f"OK: {len(on_disk)} skill folder(s) match the marketplace at version {release_version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
