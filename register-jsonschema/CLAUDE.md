# CLAUDE.md

## Project

A Docker container GitHub Action. It wraps
`synapseclient.extensions.curator.register_jsonschema` to register each `*.json`
file in a directory as a JSON Schema in a Synapse organization. It is part of
DPE-1554 (automated JSON Schema management). It runs after the sibling action
`generate-jsonschema`, which makes the schema files. ELITE and ADKP data-model
repos use the two actions together.

## Stack

- The base image `ghcr.io/sage-bionetworks/synapsepythonclient:vX.Y.Z` gives
  Python and synapseclient with the curator extras. Its tag in the `FROM` line
  of the `Dockerfile` is the version.
- `requirements.txt` has only the test dependencies, pytest and PyYAML (for
  `tests/unit/test_register_setup.py`).

## Commands

```bash
SYN_VERSION=$(sed -n 's/^FROM .*synapsepythonclient:v\([^ @]*\).*/\1/p' Dockerfile | head -n1)
pip install "synapseclient[curator]==${SYN_VERSION}"   # same as CI
pip install -r requirements.txt
SYNAPSE_AUTH_TOKEN=... python -m pytest tests -v       # run from register-jsonschema/
docker build -t register-jsonschema-action .
docker run --rm -v $(pwd)/tests/data/schema_dir:/schema_dir -e ORG_NAME=dpetest \
  -e SCHEMA_DIR=/schema_dir -e FIX_SCHEMA_NAME=true \
  -e SYNAPSE_AUTH_TOKEN="$SYNAPSE_AUTH_TOKEN" register-jsonschema-action
```

Run these commands from `register-jsonschema/`. CI
(`.github/workflows/register-jsonschema-ci.yml`) has 2 jobs. Both call the real
Synapse with the `SYNAPSE_AUTH_TOKEN` secret.

- `test-code` runs pytest. The pytest fixture makes its own random org.
- `test-register` runs the local action (`uses: ./register-jsonschema`), then a
  full workflow (`uses: ./generate-jsonschema`, then
  `uses: ./register-jsonschema`). There is no separate `docker run` job, because
  this job builds and runs the same image.
- `test-register` first makes a temporary org for the run attempt
  (`dpetest.ci.r<run_id>a<attempt>`). Its last step (`if: always()`) deletes the
  schemas and the org. All these steps are in one job, so "Re-run failed jobs"
  makes a new org. In a separate setup job, a re-run gets the output of the
  first attempt, whose org is already deleted.
- `tests/ci_org.sh create|delete <org-name>` runs `tests/ci_org.py` in the base
  image from the `FROM` line, so there is no second synapseclient pin.
- Runs do not share an org, so the workflow has no `concurrency` group.

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
- To add or rename an input or output, change all 5 places: `action.yml`
  `inputs`/`outputs`, `action.yml` `runs.env`, the script, the `README.md`
  Inputs/Outputs tables, and the lists in `tests/unit/test_register_setup.py`.

## Constraints

- For the base image rules (`FROM` tag, digest, release tags, no `pip install`,
  `python-version` in `register-jsonschema-ci.yml`), see "Constraints" in the
  root `CLAUDE.md`.

## Antipatterns — Do NOT

- Do NOT use a fixed org name in `test-register`. Use `$ORG_NAME` (or
  `${{ env.ORG_NAME }}` in `with:`). A shared org makes two runs at the same
  time fail on the same schema.
- Do NOT give the action test and the workflow test the same schema names. They
  register in the same org. Now they use `Biospecimen` and `Patient`
  (`schema_dir`) and `Datatype1` to `Datatype3` (`data_model.csv`).
- Do NOT move the org create or delete steps to a separate job, and do NOT
  remove `if: always()` from the delete step. Without them, a failed or
  cancelled run leaves its org in Synapse, or a re-run uses a deleted org.
- Do NOT expect a re-run with the same `VERSION` to pass. Synapse cannot
  overwrite a registered schema version, so each schema that registered before
  fails on the re-run.
- Do NOT call `sys.exit()` in `register_schema`. On failure it prints
  `::error::` and returns `None`. `main()` then tries the other files, prints
  the "Registration Summary", writes the `uris` of the schemas that registered
  to `GITHUB_OUTPUT`, and returns 1 if one or more files failed (DPE-1790).
  `test_non_json` and `test_malformed_json` check the summary and the output.
- Do NOT move the call to `connect_to_synapse()` (the login and the organization
  check) above the input checks in `main()` (`ORG_NAME`, `SCHEMA_DIR`, directory
  exists, `*.json` files present). These checks run before the login, so a
  missing input gives its own error and not a login error. The `TestInputChecks`
  tests remove `SYNAPSE_AUTH_TOKEN` and fail if the login runs first.
- Do NOT change `syn.login(authToken=synapse_pat)` in `connect_to_synapse()`
  back to `syn.login()`. synapseclient reads `~/.synapseConfig` before the
  `SYNAPSE_AUTH_TOKEN` env var. Thus, without the argument, a local config file
  hides the action input, and `TestInputChecks.test_invalid_token` passes the
  login.

## Testing

- The tests of the script are in two files. They do not mock anything. Set
  inputs with `monkeypatch.setenv`/`delenv`. Each file imports the script by
  putting `src/` on `sys.path`. All test files must have different names,
  because the test directories have no `__init__.py`.
  - `tests/integration/test_register_json_schemas.py`: the class
    `TestRegisterJsonSchemas` calls `main()` against the real Synapse. These
    tests need a valid `SYNAPSE_AUTH_TOKEN`.
  - `tests/unit/test_register_functions.py`: one class for each function in the
    script. `TestInputChecks` tests the input checks of `main()` and the login
    error. The other classes are `Test<FunctionName>` (for example
    `TestWriteGithubOutput`). If you add a function to the script, add a class
    for it. These tests do not use the Synapse fixtures and do not need a token
    (`python -m pytest tests/unit`). `TestRegisterSchema` uses only files that
    fail before the call to Synapse. The organization check of
    `connect_to_synapse()` needs a valid login, so only the integration tests
    test it.
- `tests/unit/test_register_setup.py` checks only `action.yml`: the inputs, the
  defaults, the `uris` output and the `runs.env` mapping. It does not import the
  script and does not need a token. Its fixtures and shared checks come from
  `shared/action_yml_checks.py` (see "Shared test helper" in the root
  `CLAUDE.md`).
- A module-scoped fixture makes a random org (`test.org.id<8 hex>`) and deletes
  its schemas and the org at the end. All `TestRegisterJsonSchemas` tests share
  it, so two tests must not register the same schema name and version.
- The tests do not depend on the current directory. Fixture directories use
  `DATA_DIR` (`Path(__file__).parents[1] / "data"`). The `GITHUB_OUTPUT` file
  and the empty directory are in `tmp_path`. Expected error text that has a path
  must use the same `DATA_DIR` path, because `main()` prints the path that it
  gets.
- `test_non_json` and `test_malformed_json` check exact synapseclient and
  Synapse error text. They can break when the base image version changes. Run
  the tests before you merge a Dependabot `FROM` update.
- Fixture dirs in `tests/data/`: `schema_dir` (2 valid schemas),
  `schema_dir_invalid_names` (`-` and `_` names for `FIX_SCHEMA_NAME`),
  `non_schema_dir` (not JSON), `malformed_schema_dir` (JSON that Synapse
  rejects). `data_model.csv` is the input for the CI `generate-jsonschema` job,
  not for pytest.
- `tests/check_uris.sh`, `tests/ci_org.sh` and `tests/ci_org.py` are for CI, not
  for pytest. pytest does not collect `ci_org.py`, because its name does not
  start with `test_`.
- `tests/check_uris.sh`: the `test-register` job calls it 2 times, with the
  expected URI count and the org. It reads the `uris` output from the `URIS` env
  var. If you add or remove a fixture schema or a data type in `data_model.csv`,
  change the count in `register-jsonschema-ci.yml`.

## Related Systems

- `generate-jsonschema` (sibling action): its `schemas` output is this action's
  `schema-dir` input. It uses the same base image and the same version rule. A
  change to it can break this CI (see "Cross-action CI" in the root
  `CLAUDE.md`).
- Promotion of a prerelease to a release does not trigger `release: published`.
  Thus caller workflows can skip registration (DPE-1650).
