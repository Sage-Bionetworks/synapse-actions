# CLAUDE.md

## Project

A Docker container GitHub Action. It wraps
`synapseclient.extensions.curator.register_jsonschema` to register each `*.json`
file in a directory as a JSON Schema in a Synapse organization. It is part of
DPE-1554 (automated JSON Schema management). It runs after the sibling action
`generate-jsonschema`, which makes the schema files. ELITE and ADKP data-model
repos use the two actions together.

## Stack

- Python and synapseclient (with curator extras), both from the base image
  `ghcr.io/sage-bionetworks/synapsepythonclient:vX.Y.Z`. The `Dockerfile` `FROM`
  tag sets the version.
- pytest (tests only, from `requirements.txt`).

## Commands

```bash
SYN_VERSION=$(sed -n 's/^FROM .*synapsepythonclient:v\([^ @]*\).*/\1/p' Dockerfile | head -n1)
pip install "synapseclient[curator]==${SYN_VERSION}"   # same as CI
pip install -r requirements.txt
SYNAPSE_AUTH_TOKEN=... python -m pytest tests -v       # run from register-jsonschema/
docker build -t register-jsonschema-action .
docker run --rm -v $(pwd)/tests/schema_dir:/schema_dir -e ORG_NAME=dpetest \
  -e SCHEMA_DIR=/schema_dir -e FIX_SCHEMA_NAME=true \
  -e SYNAPSE_AUTH_TOKEN="$SYNAPSE_AUTH_TOKEN" register-jsonschema-action
```

Run these commands from `register-jsonschema/`. CI
(`.github/workflows/register-jsonschema-ci.yml`) has 4 jobs: pytest, a Docker
run, a run of the local action (`uses: ./register-jsonschema`), and a full
workflow with `uses: ./generate-jsonschema` followed by
`uses: ./register-jsonschema`. All 4 jobs call the real Synapse with the
`SYNAPSE_AUTH_TOKEN` secret.

## Data Models

- **Inputs:** `action.yml` `inputs` → `runs.env` (`ORG_NAME`, `SCHEMA_DIR`,
  `VERSION`, `SYNAPSE_AUTH_TOKEN`, `FIX_SCHEMA_NAME`) → `os.environ` in
  `main()`. The script reads only env vars, not CLI args.
- **Input rules in `main()`:**
  - A leading `v` is removed from `VERSION` (`v1.0.0` becomes `1.0.0`).
  - `FIX_SCHEMA_NAME` is true only for the case-insensitive string `"true"`.
  - When the user does not set an input, `action.yml` gives an empty string, not
    an unset variable. `main()` changes an empty `VERSION` to `None`, so `""`
    and unset give the same result (`TestInputChecks.test_no_version`).
- **Schema name:** the filename without `.json`. Synapse names must have parts
  (separated by periods) that start with a letter and contain only letters and
  numbers. `FIX_SCHEMA_NAME` changes `-` and `_` to `.` (SYNPY-1777), so
  `Patient-Schema.json` becomes `Patient.Schema`.
- **Output:** `uris` goes to `$GITHUB_OUTPUT` as a multiline heredoc with the
  delimiter `EOF`, one URI on each line. Downstream workflows split it by lines
  (see DPE-1790), so do not change its shape.

## Conventions

- Use GitHub workflow commands for messages: `::error::` to stderr, normal
  progress to stdout. The tests check the stream (`captured.err` or
  `captured.out`) and the exact text, for example
  `"::error:: ORG_NAME environment variable is required"` (one space after
  `::error::`) and `"Registered: Patient version 1.0.0"`.
- To add or rename an input or output, change all 4 places: `action.yml`
  `inputs`/`outputs`, `action.yml` `runs.env`, the script, and the `README.md`
  Inputs/Outputs tables.

## Constraints

- Keep the `Dockerfile` `FROM` tag as the only place that sets the synapseclient
  version. Do not `pip install` anything in the `Dockerfile`. The base image has
  no pip, and Dependabot changes only the `FROM` line, so a second pin would
  silently downgrade the client (DPE-1851).
- Update the image tag and the `@sha256` digest in the `FROM` line together. The
  step "Read base image from Dockerfile" in `python-tests.yml` accepts only
  `...synapsepythonclient:vX.Y.Z@sha256:<digest>`.
- Use only release image tags, not `develop-<sha>` tags. Dependabot cannot
  follow develop tags, so the action did not get the conditional fixes in 4.12
  and 4.14 (DPE-1851).
- When the base image changes the Python version, update the `python-version`
  input in `register-jsonschema-ci.yml` by hand. The step "Check Python version
  matches base image" fails until the two values are the same. Do not write the
  current Python or synapseclient version in this file.

## Antipatterns — Do NOT

- Do NOT expect a re-run with the same `VERSION` to pass. Synapse cannot
  overwrite a registered schema version, so each schema that registered before
  fails on the re-run.
- Do NOT call `sys.exit()` in `register_schema`. On failure it prints
  `::error::` and returns `None`. `main()` then tries the other files, prints
  the "Registration Summary", writes the `uris` of the schemas that registered
  to `GITHUB_OUTPUT`, and exits with 1 if one or more files failed (DPE-1790).
  `test_non_json` and `test_malformed_json` check the summary and the output.
- Do NOT move `syn.login()` above the input checks (`ORG_NAME`, `SCHEMA_DIR`,
  directory exists, `*.json` files present). These checks run before the login,
  so a missing input gives its own error and not a login error. The
  `TestInputChecks` tests remove `SYNAPSE_AUTH_TOKEN` and fail if the login runs
  first.
- Do NOT change `syn.login(authToken=synapse_pat)` back to `syn.login()`.
  synapseclient reads `~/.synapseConfig` before the `SYNAPSE_AUTH_TOKEN` env
  var. Thus, without the argument, a local config file hides the action input,
  and `TestInputChecks.test_invalid_token` passes the login.

## Testing

- `tests/test_register_json_schemas.py` has two classes. The tests do not mock
  anything. Set inputs with `monkeypatch.setenv`/`delenv`. The module imports
  the script by putting `src/` on `sys.path`.
  - `TestRegisterJsonSchemas`: integration tests that call `main()` against the
    real Synapse. They need a valid `SYNAPSE_AUTH_TOKEN`.
  - `TestInputChecks`: tests for the input checks and the login error. They do
    not use the Synapse fixtures and do not need a token
    (`python -m pytest tests -k TestInputChecks`).
- A module-scoped fixture makes a random org (`test.org.id<8 hex>`) and deletes
  its schemas and the org at the end. All `TestRegisterJsonSchemas` tests share
  it, so two tests must not register the same schema name and version.
- The tests do not depend on the current directory. Fixture directories use
  `TESTS_DIR` (`Path(__file__).parent`). The `GITHUB_OUTPUT` file and the empty
  directory are in `tmp_path`. Expected error text that has a path must use the
  same `TESTS_DIR` path, because `main()` prints the path that it gets.
- `test_non_json` and `test_malformed_json` check exact synapseclient and
  Synapse error text. They can break when the base image version changes. Run
  the tests before you merge a Dependabot `FROM` update.
- Fixture dirs: `schema_dir` (2 valid schemas), `schema_dir_invalid_names` (`-`
  and `_` names for `FIX_SCHEMA_NAME`), `non_schema_dir` (not JSON),
  `malformed_schema_dir` (JSON that Synapse rejects). `data_model.csv` is the
  input for the CI `generate-jsonschema` job, not for pytest.

## Related Systems

- `generate-jsonschema` (sibling action): its `schemas` output is this action's
  `schema-dir` input. It uses the same base image and the same version rule. The
  CI `test-workflow` job runs the local `./generate-jsonschema`, so a change
  there can break this CI.
- Promotion of a prerelease to a release does not trigger `release: published`.
  Thus caller workflows can skip registration (DPE-1650).
