# Copilot Instructions

This repository is a monorepo of Docker container GitHub Actions for Synapse
JSON Schema management. Each action is a Python script that runs in a Docker
image based on `ghcr.io/sage-bionetworks/synapsepythonclient`. The actions do
not use an `entrypoint.sh` script.

## Repository Structure

| Path                                 | Description                                              |
| ------------------------------------ | -------------------------------------------------------- |
| `generate-jsonschema/`               | Action that makes JSON Schemas from a CSV or JSONLD file |
| `generate-jsonschema/src/`           | Python script of the action                              |
| `generate-jsonschema/test/`          | pytest tests and fixtures                                |
| `register-jsonschema/`               | Action that registers schemas in Synapse                 |
| `register-jsonschema/src/`           | Python script of the action                              |
| `register-jsonschema/tests/`         | pytest tests and fixtures                                |
| `<action>/action.yml`                | GitHub Action metadata                                   |
| `<action>/Dockerfile`                | Docker image of the action                               |
| `<action>/requirements.txt`          | Test-only Python dependencies                            |
| `.github/workflows/<action>-ci.yml`  | CI workflow of one action                                |
| `.github/workflows/python-tests.yml` | Reusable test workflow for all actions                   |
| `.github/workflows/linter.yml`       | super-linter for all files                               |
| `.github/dependabot.yml`             | Dependabot configuration                                 |
| `.ruff.toml`, `.yaml-lint.yml`, `.*` | Linter and formatter configuration                       |
| `CLAUDE.md`, `<action>/CLAUDE.md`    | Detailed rules for AI assistants                         |

The `CLAUDE.md` files have the full project rules. Read them before you change
the code.

## General Coding Guidelines

- Write Python. Do not write shell scripts for the action logic.
- Use built-in types (`list`, `dict`, `tuple`) in type annotations, not the
  `typing` aliases.
- Make sure that black and ruff format give the same result. The line length
  is 88. Keep each `assert` statement on one line of 88 characters or less,
  because the two formatters wrap long `assert` statements differently.
- Keep the changes consistent with the patterns and style that exist.
- Write comments that explain _why_, not _what_.
- Keep functions small, and use names that tell their purpose.
- Prefer the most maintainable approach, and do not repeat code. jscpd runs with
  `threshold: 0`, so a copied block fails the lint.

## Docker and Dependencies

- Each `Dockerfile` uses a `ghcr.io/sage-bionetworks/synapsepythonclient`
  release tag and a `@sha256:<digest>` in its `FROM` line, for example
  `FROM ghcr.io/sage-bionetworks/synapsepythonclient:vX.Y.Z@sha256:<digest>`.
  Update the tag and the digest together. Python and synapseclient come from
  this image.
- Do not add `pip install` to a `Dockerfile`. The CI reads the synapseclient
  version from the `FROM` line.

## Workflows

- Pin each action whose owner is not `actions/` to a full commit SHA, with the
  tag in a comment, for example `uses: owner/action@<sha> # v1.2.3`.
- Change the shared test steps in `python-tests.yml`, not in the caller
  workflows.
- Do not change the Synapse org `dpetest` that the CI uses.
- Do not put secret values in workflows. Use
  `${{ secrets.SYNAPSE_AUTH_TOKEN }}`.
- Do not format the workflow files or `action.yml` files with Prettier. Use the
  yamllint rules.

### Versioning

One `vX.Y.Z` tag versions all actions together, and a floating `v1` tag points
to the latest 1.x release. Follow [Semantic Versioning](https://semver.org/). A
breaking change in one action needs a new major version for all actions.

## Pull Request Guidelines

When you create a pull request (PR), make sure that:

- The changes are focused and small. Split large changes into smaller PRs.
- The tests, formatting checks and linting checks pass.
- The `README.md` of the changed action shows changes to its functionality or
  usage.

The body of the PR must include:

- A summary of the changes
- A special note of changes to dependencies or to the base image
- A link to the related issues or discussions
- Other context that helps the reviewers

## Code Review Guidelines

When you do a code review:

- If a change modifies the inputs, outputs or behavior of an action, make sure
  that the `README.md` and `action.yml` of that action show the change.
- Make sure that new behavior has pytest tests.
- Make sure that a change to the output of `generate-jsonschema` does not break
  `register-jsonschema`. The register CI uses the generate output.
