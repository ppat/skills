const { readdirSync } = require('node:fs');
const { join } = require('node:path');

const validateBodyMaxLengthIgnoringDeps = async (parsedCommit) => {
  const { maxLineLength } = await import('@commitlint/ensure');
  const { type, scope, body } = parsedCommit
  const isDepsCommit = type === 'chore' && scope === 'deps'
  const bodyMaxLineLength = 120;
  return [
    isDepsCommit || !body || maxLineLength(body, bodyMaxLineLength),
    `commit message body line length must not exceed ${bodyMaxLineLength}`,
  ]
}

// A change to one skill is scoped by its folder name, so the changelog of the single repository-wide release says
// which skill changed. Reading the folders keeps this list from drifting as skills are added.
const skillScopes = readdirSync(join(__dirname, 'skills'), { withFileTypes: true })
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name)

module.exports = {
  extends: ['@commitlint/config-conventional'],
  plugins: ['commitlint-plugin-function-rules'],
  rules: {
    'header-max-length': [2, 'always', 120],
    'footer-max-line-length': [0, 'always'],
    'body-max-line-length': [0],
    'function-rules/body-max-line-length': [2, 'always', validateBodyMaxLengthIgnoringDeps],
    'scope-enum': [2, 'always', ['', 'github-actions', 'internal-dependencies', 'release', ...skillScopes]],
    'body-case': [0, 'always']
  }
}
