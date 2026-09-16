#!/usr/bin/env python3
"""Check that the header a pull request lands on main is true of its diff.

commitlint sees a header and never a diff, so it can check vocabulary and type/scope pairing but not whether the named
artifacts are the ones that changed. That claim is what consumers read: the release notes print the scope in front of
every rendered line. This script holds the landed header to the pull request's whole diff.

The landed header is the one GitHub squash-merges with `squash_merge_commit_title: COMMIT_OR_PR_TITLE`: the commit's
own header for a single-commit pull request, the pull request title otherwise.

    check_commit_header.py --base SHA --head SHA --commits N --title TITLE
    check_commit_header.py --self-test
"""

import argparse
import re
import subprocess
import sys

RENDERED_TYPES = {"feat", "fix", "perf", "refactor", "revert"}
MARKETPLACE = ".claude-plugin/marketplace.json"
# What release-please writes in a release pull request: the one hidden-typed change allowed to touch a shipped file, and
# the only files `chore(release)` may land with, since machinery matches that title.
RELEASE_FILES = {MARKETPLACE, ".release-please-manifest.json", "CHANGELOG.md"}
HEADER = re.compile(r"^(?P<type>\w+)(?:\((?P<scope>[^()]*)\))?!?: .+$")


def verdict(header, paths, head_skills):
    """Return the list of problems with `header` for a diff touching `paths`, given the skill folders at head."""
    match = HEADER.match(header)
    if not match:
        return [f"'{header}' is not a conventional commit header"]
    type_ = match["type"]
    scopes = set(match["scope"].split(",")) if match["scope"] else set()

    touched_skills = {p.split("/")[1] for p in paths if p.startswith("skills/") and p.count("/") >= 2}
    removed_skills = touched_skills - head_skills
    marketplace = any(p.startswith(".claude-plugin/") for p in paths)

    # A pull request touching anything consumers receive lands under its releasing scopes only; the non-releasing files
    # in the same diff are subsumed and named by no scope. Non-releasing scopes are valid only on a diff with nothing
    # releasing in it.
    if type_ in RENDERED_TYPES:
        # The skills still on disk name themselves. The plugin listing is named when it changed on its own, or when a
        # skill left it: a removed skill's name has left the scope enum with its folder.
        expected = touched_skills & head_skills
        if removed_skills or (marketplace and not touched_skills):
            expected = expected | {"marketplace"}
        if not expected:
            return [f"'{type_}' cuts a release, but the diff touches nothing consumers receive (skills/**, .claude-plugin/**)"]
        if scopes != expected:
            return [f"the diff changes {', '.join(sorted(expected))}, so the scope must be ({','.join(sorted(expected))}), not ({','.join(sorted(scopes))})"]
        return []

    if scopes == {"release"}:
        extra = sorted(set(paths) - RELEASE_FILES)
        return [f"'chore(release)' is release-please's release cut and touches only {', '.join(sorted(RELEASE_FILES))}, not {', '.join(extra)}"] if extra else []
    shipped = sorted({f"skills/{s}/" for s in touched_skills} | ({MARKETPLACE} if marketplace else set()))
    if shipped:
        return [f"'{type_}' cuts no release, but the diff changes {', '.join(shipped)}, which consumers receive: type it {'/'.join(sorted(RENDERED_TYPES))} and name what changed"]
    return []


def git(*args):
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--commits", type=int)
    parser.add_argument("--title")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        return self_test()

    header = git("log", "-1", "--format=%s", args.head).strip() if args.commits == 1 else args.title
    source = "the single commit's header" if args.commits == 1 else "the pull request title"
    paths = git("diff", "--name-only", "--no-renames", f"{args.base}...{args.head}").split()
    head_skills = {line.split("/")[1] for line in git("ls-tree", "-d", "--name-only", args.head, "skills/").split()}

    print(f"landed header ({source}): {header}")
    problems = verdict(header, paths, head_skills)
    for problem in problems:
        print(f"::error::{problem}. The rules are in .claude/rules/commits.md.")
    return 1 if problems else 0


# Each case is a real way a header can lie about its diff, or a legitimate shape the check must not reject. A check that
# has never caught an injected defect is an argument, not a check.
SKILLS = {"alpha", "beta"}
CASES = [
    # (header, paths, expected to pass)
    ("fix(alpha): correct step 3", ["skills/alpha/SKILL.md"], True),
    ("feat(alpha): add a trap", ["skills/alpha/SKILL.md", "README.md", "scripts/lint_skills_spec.py", "CLAUDE.md"], True),
    ("feat(alpha): publish alpha", ["skills/alpha/SKILL.md", MARKETPLACE, "README.md"], True),
    ("fix(alpha,beta): rename a shared term", ["skills/alpha/SKILL.md", "skills/beta/SKILL.md"], True),
    ("feat(marketplace)!: remove gamma", ["skills/gamma/SKILL.md", MARKETPLACE, "README.md"], True),
    ("refactor(alpha,marketplace)!: rename gamma to alpha", ["skills/gamma/SKILL.md", "skills/alpha/SKILL.md", MARKETPLACE], True),
    ("fix(marketplace): correct the plugin description", [MARKETPLACE], True),
    ("chore(release): release v0.1.0", [MARKETPLACE, ".release-please-manifest.json", "CHANGELOG.md"], True),
    ("chore(internal-dependencies): update node (non-major)", ["mise.toml", "mise.lock"], True),
    ("chore(github-actions): update actions/checkout (v6.0.0 -> v7.0.1)", [".github/workflows/lint.yaml"], True),
    ("ci(internal-workflows): lint the landed header", [".github/workflows/commit-header.yaml", ".github/scripts/check_commit_header.py"], True),
    ("docs(agents): describe the commit rules", ["CLAUDE.md", ".claude/rules/commits.md"], True),
    ("docs: fix a typo in the README", ["README.md"], True),
    # A skill change typed hidden: reaches `skills` CLI users with no release and no changelog line.
    ("docs: tweak wording", ["skills/alpha/SKILL.md"], False),
    ("chore(agents): reflow", ["skills/alpha/references/notes.md"], False),
    # A hand edit to the plugin listing typed hidden.
    ("chore(internal-workflows): tidy marketplace.json", [MARKETPLACE], False),
    # The wrong skill, a missing one, or an extra one: the release notes would name the wrong artifact.
    ("fix(beta): correct step 3", ["skills/alpha/SKILL.md"], False),
    ("fix(alpha): rename a shared term", ["skills/alpha/SKILL.md", "skills/beta/SKILL.md"], False),
    ("fix(alpha,beta): correct step 3", ["skills/alpha/SKILL.md"], False),
    ("feat(alpha,marketplace): publish alpha", ["skills/alpha/SKILL.md", MARKETPLACE], False),
    # A release claimed for a diff no consumer receives: what the shared presets' feat/fix defaults would land.
    ("fix: update skillscheck (0.9.6 -> 0.9.7)", ["mise.toml"], False),
    ("fix(alpha): update skillscheck (0.9.6 -> 0.9.7)", ["mise.toml"], False),
    ("feat(marketplace): update node", ["mise.toml"], False),
    # A removal that names the removed skill's neighbour instead of the listing it left.
    ("feat(alpha)!: remove gamma", ["skills/gamma/SKILL.md", MARKETPLACE], False),
    # Non-releasing changes land under the releasing scope; a non-releasing header on a releasing diff is rejected.
    ("ci(internal-workflows): add a check", ["scripts/check_install.py", "skills/alpha/SKILL.md"], False),
    ("docs(agents): document alpha", ["CLAUDE.md", "skills/alpha/SKILL.md"], False),
    ("fix(alpha,internal-workflows): correct step 3", ["skills/alpha/SKILL.md", "scripts/check_install.py"], False),
    # The release cut lands alone.
    ("chore(release): release v0.1.0", [MARKETPLACE, ".release-please-manifest.json", "CHANGELOG.md", "README.md"], False),
    # The release scope borrowed for anything but release-please's cut.
    ("chore(release): prepare release", ["skills/alpha/SKILL.md", MARKETPLACE], False),
    ("not a header", ["README.md"], False),
]


def self_test():
    failures = 0
    for header, paths, should_pass in CASES:
        problems = verdict(header, paths, SKILLS)
        if (not problems) != should_pass:
            failures += 1
            print(f"FAIL: {header!r} on {paths}: expected {'pass' if should_pass else 'rejection'}, got {problems or 'pass'}")
    print(f"self-test: {len(CASES) - failures}/{len(CASES)} cases behave as expected")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
