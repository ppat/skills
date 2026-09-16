#!/usr/bin/env python3
"""Lint every skill against the Agent Skills spec with skillscheck, honouring named exceptions.

skillscheck runs against `skills/` rather than the repository root: at the root its Claude adapter demands a
`plugin.json`, which this repository deliberately does not have (see scripts/check_marketplace.py).

Errors fail the lint, and so do the findings in PROMOTED_TO_ERROR, which skillscheck rates lower than this
repository does. Other warnings and info are printed only. skillscheck has no per-skill suppression, so the
exceptions live here instead of weakening the whole lint.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Frontmatter outside the spec is rejected by claude.ai and the Skills API; a broken link is broken for every consumer.
PROMOTED_TO_ERROR = {"1d.unknown-field", "2c.broken-link", "2c.broken-link.fragment", "2c.escapes-skill"}

# (skill folder, skillscheck check id) -> why the error is accepted for now. Keep each entry to one skill and
# one check. An entry that no longer matches an error fails the lint, so no exception outlives its fix.
ALLOWED_ERRORS = {
    ("derive-commit-taxonomy", "1b.description.length"): (
        "description exceeds the spec's 1,024-character limit but is within Claude Code's 1,536; "
        "follow-up: trim the description, then delete this entry"
    ),
}


def main() -> int:
    run = subprocess.run(
        ["skillscheck", "skills", "--format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        report = json.loads(run.stdout)
    except json.JSONDecodeError:
        print(run.stdout + run.stderr, file=sys.stderr)
        print("ERROR: skillscheck did not produce a JSON report", file=sys.stderr)
        return 1

    failures: list[str] = []
    matched: set[tuple[str, str]] = set()
    for skill, categories in sorted(report["skills"].items()):
        for category, findings in sorted(categories.items()):
            for finding in findings:
                check, message = finding["check"], finding["message"]
                level = "error" if check in PROMOTED_TO_ERROR else finding["level"]
                line = f"{skill}: [{category}/{check}] {message}"
                if level != "error":
                    print(f"{level.upper()}: {line}")
                elif (skill, check) in ALLOWED_ERRORS:
                    matched.add((skill, check))
                    print(f"ALLOWED: {line} ({ALLOWED_ERRORS[(skill, check)]})")
                else:
                    failures.append(line)

    for skill, check in sorted(ALLOWED_ERRORS.keys() - matched):
        failures.append(f"{skill}: exception for {check} no longer matches an error; remove it from scripts/lint_skills_spec.py")

    for failure in failures:
        print(f"ERROR: {failure}", file=sys.stderr)
    if failures:
        return 1
    print(f"OK: {len(report['skills'])} skill(s) pass the spec lint")
    return 0


if __name__ == "__main__":
    sys.exit(main())
