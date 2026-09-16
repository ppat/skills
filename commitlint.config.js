const { readdirSync } = require('node:fs');
const { join } = require('node:path');

// Commit taxonomy for this repo. How to choose a header lives in .claude/rules/commits.md; this file checks the
// vocabulary and the type/scope pairing. Whether a header is true of its diff is checked by
// .github/scripts/check_commit_header.py, which can see the diff.
//
// release-please (release-type simple, one package at ".") hides some types and sizes the single repository-wide
// release by the rest. No release is routed by scope. On rendered types the scope is what the release notes print in
// bold in front of each line, and consumers select skills one at a time but share one version, so it names the skills
// that changed. On hidden types it names the internal surface, in the vocabulary every ppat repository shares.

// One scope per skill, named as consumers select it. Read from disk so the enum is exactly the skills that exist.
const skillScopes = readdirSync(join(__dirname, 'skills'), { withFileTypes: true })
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name)

// Surfaces no consumer receives. Their names and meanings are shared across ppat repositories; Renovate emits
// `github-actions`, `internal-dependencies` and `renovate`, and release-please `release`.
const INTERNAL_SCOPES = [
  'agents',                 // CLAUDE.md, .claude/**: instructions for agents working on this repository
  'github-actions',         // a `uses:` ref moved, and nothing else
  'internal-dependencies',  // any other pinned tool, hook or lockfile version moved, and nothing else
  'internal-workflows',     // this repository's CI, checks, scripts, lint and release configuration
  'release',                // a release cut authored by release-please
  'renovate',               // this repository's Renovate configuration, including its shared-preset pins
]

// `marketplace` is .claude-plugin/marketplace.json, the plugin listing. It also names the removal of a skill, whose
// folder name has already left the enum.
const collisions = skillScopes.filter((name) => [...INTERNAL_SCOPES, 'marketplace'].includes(name))
if (collisions.length > 0) {
  throw new Error(`skill folder names collide with fixed commit scopes: ${collisions.join(', ')}`)
}
const ARTIFACT_SCOPES = [...skillScopes, 'marketplace']

// Rendered types: each cuts a release, and names the artifacts it changed.
const RELEASE_FORCING_TYPES = ['feat', 'fix', 'perf', 'refactor', 'revert']

// Hidden types: no release, no changelog line.
const HIDDEN_TYPES = ['chore', 'ci', 'docs']

// Both directions hold:
// - a rendered type cuts a release, so it must name the artifacts consumers receive, and only those;
// - a hidden type must not name them: `skills` CLI users receive a skill-folder change on merge, so hiding one leaves
//   plugin users without a release and the changelog without the line. It takes an internal scope, or none for
//   repo-level files (README.md, LICENSE).
// A header cannot mix the two: once a pull request lands anything that releases, its non-releasing files are subsumed
// under the releasing scopes. .github/scripts/check_commit_header.py checks that against the diff.
const validateScopeByType = async (parsedCommit) => {
  const type = parsedCommit.type || ''
  const scopes = parsedCommit.scope ? parsedCommit.scope.split(',') : []
  if (RELEASE_FORCING_TYPES.includes(type)) {
    return [
      scopes.length > 0 && scopes.every((scope) => ARTIFACT_SCOPES.includes(scope)),
      `type '${type}' cuts a release, so it must name the artifacts it changed: one or more of ` +
      `${ARTIFACT_SCOPES.join(', ')}, comma-separated.`,
    ]
  }
  return [
    scopes.length <= 1 && scopes.every((scope) => INTERNAL_SCOPES.includes(scope)),
    `type '${type}' cuts no release, so it takes one internal scope (${INTERNAL_SCOPES.join(', ')}) or none. ` +
    `A change consumers receive takes ${RELEASE_FORCING_TYPES.join('/')}.`,
  ]
}

// A breaking marker cuts a major release and renders even on a hidden type, so it needs a rendered type. Read from
// both the header ('!') and the parsed notes (`BREAKING CHANGE:` / `BREAKING-CHANGE:` footers): the parser exposes
// each spelling in only one of those places.
const validateBreakingMarker = async (parsedCommit) => {
  const hasBang = /^\w+(\([^)]*\))?!:/.test(parsedCommit.header || '')
  const hasNote = (parsedCommit.notes || []).length > 0
  if (!hasBang && !hasNote) {
    return [true]
  }
  return [
    RELEASE_FORCING_TYPES.includes(parsedCommit.type || ''),
    `a breaking marker cuts a major release, so it needs a ${RELEASE_FORCING_TYPES.join('/')} type.`,
  ]
}

// Dependency updates may carry pasted upstream release notes whose lines cannot be rewrapped.
const validateBodyMaxLengthIgnoringDeps = async (parsedCommit) => {
  const { maxLineLength } = await import('@commitlint/ensure');
  const { type, scope, body } = parsedCommit
  const isDepsCommit = type === 'chore' && ['github-actions', 'internal-dependencies', 'renovate'].includes(scope)
  const bodyMaxLineLength = 120;
  return [
    isDepsCommit || !body || maxLineLength(body, bodyMaxLineLength),
    `commit message body line length must not exceed ${bodyMaxLineLength}`,
  ]
}

module.exports = {
  extends: ['@commitlint/config-conventional'],
  plugins: [
    'commitlint-plugin-function-rules',
    {
      rules: {
        'local/scope-by-type': validateScopeByType,
        'local/breaking-marker': validateBreakingMarker,
      },
    },
  ],
  rules: {
    'header-max-length': [2, 'always', 120],
    'footer-max-line-length': [0, 'always'],
    'body-max-line-length': [0],
    'function-rules/body-max-line-length': [2, 'always', validateBodyMaxLengthIgnoringDeps],

    // Must equal the type keys of `changelog-sections` in release-please-config.json: a type with no section renders
    // nothing and cuts no release, silently. `build` (nothing here is built), `style` (no edit to a skill is
    // cosmetic) and `test` (nothing here has tests; the checks under scripts/ are `ci`) name nothing in this repo.
    'type-enum': [2, 'always', [...HIDDEN_TYPES, ...RELEASE_FORCING_TYPES].sort()],

    // Each comma-separated scope is checked on its own. `local/scope-by-type` decides which of these a type may carry.
    'scope-enum': [2, 'always', ['', ...ARTIFACT_SCOPES, ...INTERNAL_SCOPES].sort()],

    'local/scope-by-type': [2, 'always'],
    'local/breaking-marker': [2, 'always'],

    'body-case': [0, 'always']
  }
}
