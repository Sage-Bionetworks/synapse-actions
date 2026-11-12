# CLAUDE.md

## Project

A monorepo of Docker container GitHub Actions for Synapse JSON Schema management
(DPE-1554). Each top-level action directory (`generate-jsonschema/`,
`register-jsonschema/`) has its own `action.yml`, `Dockerfile`, Python script,
tests and `CLAUDE.md`. This repository replaces the old single-action
repositories `Sage-Bionetworks-Actions/generate-jsonschema` and
`Sage-Bionetworks-Actions/register-jsonschema`. ELITE and ADKP data-model
repositories call the actions as `Sage-Bionetworks/synapse-actions/<action>@v1`
(move tracked in DPE-1619).

## Stack

- Python and synapseclient come from the base image
  `ghcr.io/sage-bionetworks/synapsepythonclient`. Each action `Dockerfile` sets
  its own `FROM` tag. See "Constraints" for the version rules.
- pytest for tests, one `requirements.txt` for each action (test-only deps).
- super-linter slim (`.github/workflows/linter.yml`) with the configs at the
  root (`LINTER_RULES_PATH: .`).
- Dependabot (`.github/dependabot.yml`) updates the `FROM` lines and the
  workflow actions each week.

## Commands

To run the full lint locally, use the `docker run` command in the "Linting"
section of the root `README.md`, from the repository root. Do not copy the
command into a new file, because jscpd (`threshold: 0`) fails on the copy.

- Keep the image version and the `-e` flags in the `README.md` command the same
  as `linter.yml`. If you change `linter.yml`, change the command too.
- super-linter fails with "Neither main, nor origin/main exist" if `main` has no
  commit. Lint a committed copy of the files.

For tests, Docker build and Docker run of each action, see the module
`CLAUDE.md`. Run those commands from the action directory, because CI sets
`defaults.run.working-directory` to it.

## Architecture

- **Workflows:** one `<action>-ci.yml` for each action, one reusable
  `python-tests.yml`, and one `linter.yml` for all files. Each CI workflow has
  `paths` filters and `defaults.run.working-directory: <action>`. Steps that use
  `uses:` do not follow `working-directory`, so they give paths from the root
  (for example `uses: ./generate-jsonschema`, `context: generate-jsonschema`).
- **Shared test job:** the `Tests` job of each CI workflow calls the reusable
  workflow `python-tests.yml` with the inputs `action-directory`,
  `python-version`, `synapseclient-extras` and `test-path`. It reads the `FROM`
  line and checks the Python version. Change these shared rules in
  `python-tests.yml`, not in the caller workflows. Do not copy the test steps
  back into a caller, because jscpd fails on the copy.
- **Cross-action CI:** `register-jsonschema-ci.yml` also runs on changes to
  `generate-jsonschema/**`. Its `test-workflow` job runs the local
  `./generate-jsonschema` and gives its `schemas` output to
  `./register-jsonschema`. A change to the generate output can break the
  register CI.

## Conventions

- Release: one `vX.Y.Z` tag for the full repository, and a floating `v1` major
  tag that moves to each new 1.x release. A tag versions all actions together.
  Thus a breaking change in one action needs a new major tag for all actions.
  The `README.md` examples use `@v1`.
- To add a new action (for example the LinkML action in ADM-8603), change all of
  these:
  - a new top-level directory with `action.yml`, `Dockerfile`, `src/`, tests,
    `README.md` and `CLAUDE.md`
  - a new `.github/workflows/<action>-ci.yml`, made from an existing one
    (`paths`, `working-directory`, the `python-tests.yml` call)
  - the Dockerfile `directories` list in `.github/dependabot.yml`
  - `FILTER_REGEX_EXCLUDE` in `linter.yml` and `ignore` in `.jscpd.json` if the
    new tests have fixtures that are not valid or that repeat
- Use repository-relative paths in workflow `with:` values, for example
  `data-model-source: ./generate-jsonschema/test/data_model.csv`.

## Constraints

- Pin each action whose owner is not `actions/` to a full commit SHA with a
  `# vX.Y.Z` comment. This is the Sage repository security policy.
- Keep the `Dockerfile` `FROM` tag as the only place that sets the synapseclient
  version. Do not `pip install` anything in a `Dockerfile`. The base image has
  no pip, Dependabot changes only the `FROM` line, and the CI steps read the
  synapseclient version from it. Thus a second pin would silently downgrade the
  client after each Dependabot update (DPE-1851).
- Use only `ghcr.io/sage-bionetworks/synapsepythonclient:vX.Y.Z` release tags,
  not `develop-<sha>` tags. Dependabot cannot follow develop tags, so the
  actions did not get the conditional fixes in 4.12 and 4.14 (DPE-1851).
- Keep the `@sha256:<digest>` after the tag in each `FROM` line, and update the
  tag and the digest together. The `python-tests.yml` step "Read base image from
  Dockerfile" fails if the `FROM` line is not
  `...synapsepythonclient:vX.Y.Z@sha256:<digest>`.
- When the base image changes the Python version, update the `python-version`
  input in `<action>-ci.yml` by hand (Dependabot does not change it). The step
  "Check Python version matches base image" fails until the two values are the
  same. Do not write the current Python or synapseclient version in a
  `CLAUDE.md` file. Refer to the `Dockerfile` `FROM` tag.
- Do not change the CI Synapse org `dpetest` to a production org. The register
  CI jobs really register schemas in it (see `register-jsonschema/CLAUDE.md` for
  the concurrency rule).
- Do not put secret values in workflows. Use
  `${{ secrets.SYNAPSE_AUTH_TOKEN }}`.

## Antipatterns — Do NOT

- Do NOT reformat `.github/workflows/*.yml` or `*/action.yml` with Prettier.
  `.prettierignore` excludes them on purpose (old generate repository PR #8).
  Use the yamllint rules (`.yaml-lint.yml`) for these files.
- Do NOT let `.github/copilot-instructions.md` and the `CLAUDE.md` files become
  different. If you change a rule here, change the Copilot file too.
- Do NOT merge with lint failures. super-linter checks all files
  (`VALIDATE_ALL_CODEBASE: true`), also `CLAUDE.md` files and test code.
- Do NOT remove `FILTER_REGEX_EXCLUDE` or the `.jscpd.json` ignore entries. The
  `non_schema_dir` fixture is not valid JSON on purpose, and the test CSV/JSON
  fixtures repeat on purpose.

## Linting

- super-linter runs both black and ruff format. `.ruff.toml` sets
  `line-length = 88` to match black. Do not remove it. Without it, ruff uses 120
  and the two formatters do not agree.
- black and ruff format wrap a long `assert cond, "msg"` in different ways, and
  no setting fixes this. Keep each `assert` on one line of 88 characters or
  less. Use a local variable or a shorter message.
- Line limits: black and ruff 88, pylint 100, flake8 120, markdownlint MD013 80,
  yamllint 80 (warning only). MD013 does not check tables and code blocks.
  Prettier (`proseWrap: always`) wraps Markdown prose at 80 characters.
- textlint (`terminology` rule) rejects words such as `README`, `repo` and
  `hard-code` in plain text. It does not check code spans, so write `README.md`.
- flake8 reports E402 for an import after `sys.path.insert` in the tests, but
  ruff does not. `.ruff.toml` sets `external = ["E402"]`, so ruff RUF100 does
  not report the `# noqa: E402` as unused. Do not remove the setting or the
  `noqa`.
- black, isort, flake8, pylint and textlint have no config in the repository, so
  they use the super-linter defaults.
