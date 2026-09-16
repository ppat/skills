---
description: How to choose the type and scope of a commit in this repo. Type decides whether a release happens; scope tells consumers which skill changed.
---

# Commit types and scopes

The header carries two fields with different jobs:

> **Type is the release decision.** release-please sizes the one repository-wide release by type, and a window of
> only hidden types cuts no release at all.
>
> **Scope names what the diff changed.** No release is routed by it. On a rendered type it names the artifacts
> consumers receive: the release notes print it in bold in front of the line, and consumers select skills one at a
> time but share one version, so that is where they learn which skill changed. On a hidden type it names the internal
> surface, in the vocabulary every ppat repository shares.

`chore(release):` is also matched by machinery: release-please tags a merged release pull request by matching its title
against `pull-request-title-pattern`, and the shared release-sweep action finds release pull requests with a
`chore(release): release … vX.Y.Z` regex.

## What reaches a consumer

| Path | Who receives it, and when |
| --- | --- |
| `skills/<name>/**` | `skills` CLI users on merge (unless pinned to a tag); plugin users on the next release |
| `.claude-plugin/marketplace.json` | plugin users, on the next release |
| everything else | nobody: CI, checks, pins, Renovate and release configuration, `README.md`, `CLAUDE.md`, `.claude/` |

Every byte of a skill folder is instruction an agent reads, so no change there is cosmetic. A skill change typed
`docs` or `chore` would reach CLI users on merge while plugin users got no release and the changelog no line.

## Types

| Type | Renders | Use for |
| --- | --- | --- |
| `feat` | ✨ Features, minor bump | a skill gains or widens what it does: a new skill, a new question, trap or trigger |
| `fix` | 🚀 Enhancements + Bug Fixes, patch bump | a skill's guidance corrected: wrong advice, a broken link, a mis-trigger |
| `perf` | 🚀 Enhancements + Bug Fixes, patch bump | the same guidance at lower cost to the agent loading it: a shorter description or body |
| `refactor` | 🚀 Enhancements + Bug Fixes, patch bump | a skill restructured with its guidance unchanged |
| `revert` | ⚙️ Other, patch bump | undoing a released change |
| `chore` | hidden | a pinned version moved; Renovate and release-please housekeeping; repo-level upkeep |
| `ci` | hidden | this repo's machinery: workflows, `scripts/`, `.github/scripts/`, `mise.toml` tasks, commitlint, lint, Renovate and release-please configuration |
| `docs` | hidden | prose for people or agents working on this repo: `README.md`, `CLAUDE.md`, `.claude/**` |

`build`, `style` and `test` are not accepted: nothing here is built, no edit to a skill is cosmetic, and nothing here
has tests (the checks under `scripts/` are `ci`). A type exists only if it has a `changelog-sections` entry in
`release-please-config.json`; a type without one renders nothing and cuts no release. Change the two together.

A bug in a workflow or check is `ci(internal-workflows): fix …`, never `fix:`. `fix` claims a consumer received a correction.

## Scopes

Closed set. Which scopes a header may carry depends on what else lands in the same pull request, because squash-merge
lands one header for the whole diff.

### Step 1: what does the pull request land?

| The diff | Header | Why |
| --- | --- | --- |
| only what release-please writes in a release cut (`marketplace.json` version, `.release-please-manifest.json`, `CHANGELOG.md`) | `chore(release): release vX.Y.Z` | Machinery matches this title, so it lands **alone**, never combined with anything |
| any file under `skills/<name>/`, or a hand edit to `marketplace.json` | a rendered type with **releasing scopes only** (step 2) | The release is the change consumers receive; every non-releasing file in the diff (`README.md`, `CLAUDE.md`, a check, a workflow, a pin) is subsumed under it and gets no scope of its own |
| nothing consumers receive | a hidden type with **one non-releasing scope** or none (step 3) | Non-releasing scopes are valid only when nothing that releases lands with them |

### Step 2: releasing scopes

| Scope | The diff changes |
| --- | --- |
| each skill folder name, comma-separated | the `skills/<name>/` folders still on disk: `fix(derive-commit-taxonomy):`, `feat(alpha,beta):` |
| `marketplace` | `marketplace.json` with no skill folder changed, or a skill folder deleted (its name has left the enum): `feat(marketplace)!: remove <name>`, `refactor(<new-name>,marketplace)!: rename …` |

List every releasing artifact the diff changes and nothing else. `marketplace` is not listed alongside a skill whose
own entry was added or edited, because that entry rides with the skill.

### Step 3: non-releasing scopes

Apply **in order, stopping at the first match**.

| # | Scope | The diff | Type |
| --- | --- | --- | --- |
| 1 | `renovate` | this repo's Renovate configuration, and nothing else, including a shared-preset pin bump and a config migration | `chore`, `ci` |
| 2 | `github-actions` | moves a `uses:` ref, anywhere, and nothing else | `chore` |
| 3 | `internal-dependencies` | moves any other pinned tool, hook or lockfile version (`mise.toml`, `mise.lock`, `.mise/locks/`, `.pre-commit-config.yaml`, workflow `env:` pins), and nothing else | `chore` |
| 4 | `internal-workflows` | this repo's machinery: `.github/workflows/**`, `.github/scripts/**`, `scripts/`, `mise.toml` tasks and settings, commitlint, lint and release-please configuration | `ci` |
| 5 | `agents` | `CLAUDE.md`, `.claude/**` | `docs` |
| 6 | *(empty)* | `README.md`, `LICENSE` and other repo-level files on their own | `docs`, `chore` |

Rows 1–3 are line-level ("a version moved and nothing else"), so they sort first: a workflow edit that also re-pins an
action fails row 2 and lands on row 4. When a diff spans rows 4–6, scope it to what motivated it. A rule document, a
commitlint change and a workflow landing together to enforce one convention are `internal-workflows`.

The skill scopes are read from `skills/` by `commitlint.config.js`, so the enum is exactly the skills that exist.

## Breaking changes

`!` (or a `BREAKING CHANGE: <what consumers must do>` footer) cuts a **major** release, even before 1.0.0: there is no
`bump-minor-pre-major`. It renders even on a hidden type, so commitlint accepts it only on a rendered type.

A skill's folder name is public API: consumers select it (`--skill <name>`), invoke it (`/ppatlabs:<name>`) and the
CLI names the installed folder after it. Breaking means a consumer must act:

| Situation | Header |
| --- | --- |
| Remove a skill | `feat(marketplace)!: remove <name>` |
| Rename a skill | `refactor(<new-name>,marketplace)!: rename <old-name> to <new-name>` |
| A skill's behaviour changes in a way a consumer relying on it must adapt to | `feat(<name>)!:` with the footer saying what changed |

Nothing that reaches no consumer is ever breaking: a major bump of a tool, action or preset is `chore(<scope>):`.

## Where it is checked

| Check | Reads | Catches |
| --- | --- | --- |
| `commit-messages` (lint.yaml) | every commit on the branch | vocabulary, rendered types on skill/`marketplace` scopes and hidden types on internal ones, `!` only on rendered types |
| `commit-header` (commit-header.yaml), title step | the pull request title, on every edit | the same, for the string a multi-commit pull request lands |
| `commit-header`, diff step (`.github/scripts/check_commit_header.py`) | the header that will land, against the whole diff | the step 1 landing rule: a non-releasing scope or hidden type alongside a releasing change; releasing scopes naming the wrong, too few or too many artifacts; `chore(release)` combined with anything |

Squash-merge lands a single-commit pull request's **commit header** and a multi-commit one's **title**, so keep the
title conforming whatever the commit count. The landed body is the concatenation of the branch's commit messages: land
one commit if the body should read as one message.

## Bot headers

Leave Renovate's and release-please's titles alone.

- **Renovate** emits `chore(github-actions):`, `chore(internal-dependencies):` or `chore(renovate):`. Nothing this repo
  pins reaches a consumer. The shared presets would type updates `feat`/`fix` by semver level on an empty scope and
  add `!` to majors, so `.github/renovate.json` claims type, scope and a `!`-free prefix after them. Config migration
  pull requests are no package update, so no packageRule reaches them: the repository-level `chore(renovate):` prefix
  is what keeps them from hard-coding the scope `config`.
- **release-please** renders `chore(release): release vX.Y.Z` from `pull-request-title-pattern`.

When a shared-preset pin moves, re-check the invariant rather than the preset's contents: the local prefix rules still
match every update, including those without a package name (lockfile maintenance). A header they miss fails the
`commit-header` diff step or commitlint, so a Renovate pull request goes red instead of merging a false release.

## Gotchas

- **`!` on a hidden type still cuts a major.** release-please renders breaking notes regardless of `hidden`.
- **A release window of only hidden types cuts nothing**, including after a `docs` or `ci` change. That is intended.
- **Removing a skill in the same branch as an earlier commit scoped to it** fails `commit-messages` on that earlier
  commit: the enum is read at the branch head, where the folder is gone. Squash before pushing.
- **`Release-As:` footers and `BEGIN_COMMIT_OVERRIDE` in the pull request body** change what release-please does
  without changing the header, and no check here reads them.
