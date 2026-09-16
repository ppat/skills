#!/usr/bin/env python3
"""Install this checkout with the `skills` CLI into a throwaway project and compare the result with the source.

The CLI names an installed folder after the frontmatter `name` and skips skills it cannot parse or that are
marked internal, so an install that differs from `skills/` means consumers do not get what is on disk.
"""

import filecmp
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def differences(left: Path, right: Path) -> list[str]:
    cmp = filecmp.dircmp(left, right)
    found = [f"only in source: {left / n}" for n in cmp.left_only]
    found += [f"only in install: {right / n}" for n in cmp.right_only]
    _, mismatch, errors = filecmp.cmpfiles(left, right, cmp.common_files, shallow=False)
    found += [f"content differs: {left / n}" for n in mismatch + errors]
    for sub in cmp.common_dirs:
        found += differences(left / sub, right / sub)
    return found


def main() -> int:
    source = {p.parent.name: p.parent for p in (ROOT / "skills").glob("*/SKILL.md")}
    with tempfile.TemporaryDirectory() as tmp:
        home, project = Path(tmp, "home"), Path(tmp, "project")
        home.mkdir()
        project.mkdir()
        env = {"PATH": os.environ["PATH"], "HOME": str(home), "DISABLE_TELEMETRY": "1", "CI": "true"}
        run = subprocess.run(
            ["skills", "add", str(ROOT), "--skill", "*", "--agent", "claude-code", "--copy", "--yes"],
            cwd=project,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if run.returncode != 0:
            print(run.stdout + run.stderr, file=sys.stderr)
            print(f"ERROR: skills add exited {run.returncode}", file=sys.stderr)
            return 1

        installed_root = project / ".claude" / "skills"
        installed = {p.name: p for p in installed_root.iterdir()} if installed_root.is_dir() else {}
        errors = [f"skill folder not installed: {n}" for n in sorted(source.keys() - installed.keys())]
        errors += [f"installed but no matching skill folder: {n}" for n in sorted(installed.keys() - source.keys())]
        for name in sorted(source.keys() & installed.keys()):
            errors += differences(source[name], installed[name])

    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        return 1
    print(f"OK: skills CLI installs {len(source)} skill(s) identical to skills/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
