# CLAUDE.md

## Project

A Docker container GitHub Action. It wraps
`synapseclient.extensions.curator.generate_jsonschema` to turn a CSV/JSONLD data
model into JSON Schema files for Synapse. It is part of DPE-1554 (automated JSON
Schema management). Its sibling action `register-jsonschema` registers the
generated schemas. ELITE and ADKP data-model repos use this action.

## Stack

- Python and synapseclient (with curator extras), both from the base image
  `ghcr.io/sage-bionetworks/synapsepythonclient:vX.Y.Z`. The `Dockerfile` `FROM`
  tag sets the version.
- pytest, PyYAML (tests only, from `requirements.txt`)

## Commands

```bash
SYN_VERSION=$(sed -n 's/^FROM .*synapsepythonclient:v\([^ @]*\).*/\1/p' Dockerfile | head -n1)
pip install "synapseclient[pandas,curator]==${SYN_VERSION}"   # same as CI
pip install -r requirements.txt   # test-only deps (PyYAML, pytest)
python -m pytest tests -v
docker build -t generate-jsonschema-action .
docker run --rm -e DATA_MODEL_SOURCE="/tests/data_model.csv" -v $(pwd)/tests:/tests generate-jsonschema-action
```

Run these commands from `generate-jsonschema/`. CI
(`.github/workflows/generate-jsonschema-ci.yml`) has 3 jobs: pytest, a Docker
build, and a run of the local action (`uses: ./generate-jsonschema`) on
`tests/data_model.csv`. The register CI also runs this action (see the root
`CLAUDE.md`).

## Data Models

- **Inputs:** `action.yml` `inputs` → `runs.env` (`DATA_MODEL_SOURCE`,
  `DATA_TYPES`, `DATA_MODEL_LABELS`, `OUTPUT_DIRECTORY`) → `os.environ` in
  `main()`. The script reads only env vars, not CLI args.
- **Input rules:** `main()` reads the env vars and gives them to helper
  functions. `parse_data_types()`: if `DATA_TYPES` is not set, empty or only
  whitespace, it becomes `None` (all types,
  `TestMain.test_with_empty_data_type`). If it has commas and no names (for
  example `" , ,"`), it becomes `[]`. Then `main()` gives `::error::` and
  returns 1 (`TestMain.test_with_only_commas_data_types`). Do not give `[]` to
  synapseclient, because its meaning is not documented.
  `validate_data_model_source()`: a
  source that starts with `http://`/`https://` has no file-exists check. An
  empty `DATA_MODEL_LABELS` value becomes `class_label`.
  `validate_data_model_labels()`: other values that are not `class_label` or
  `display_label` give `::error::`, and `main()` returns 1
  (`TestMain.test_invalid_labels`). An empty `OUTPUT_DIRECTORY` value becomes
  `schemas` (`TestMain.test_with_empty_output_directory`). Use
  `os.environ.get(KEY) or default` for these inputs, not
  `os.environ.get(KEY, default)`, because `action.yml` always sets the env var.
- **Outputs** go to `$GITHUB_OUTPUT`: `schemas` is a path relative to the
  workspace (`resolve_output_path()`), also if `OUTPUT_DIRECTORY` is absolute.
  Do not write the container path (`/github/workspace/...`), because it does
  not exist on the runner host. `validate_output_directory()` resolves
  `OUTPUT_DIRECTORY` and gives `::error::` if the result is not in the
  workspace (for example `../schemas` or `/tmp/schemas`). Only the workspace is
  mounted from the runner, so files in other locations are lost.
  `schemas-json` is `json.dumps` of the schema list, written as a multiline
  heredoc with the delimiter `EOF`. Users parse `schemas-json` (see the
  `README.md` PR-comment example), so do not change its shape.
- **Test fixture `tests/data_model.csv`:** 3 template rows (`IsTemplate=TRUE`:
  Datatype1–3), each with one required property. The tests hardcode the counts
  (`TOTAL_SCHEMAS_IN_TEST_MODEL = 3`, "generated 1/2/3 schema(s)"). If you
  change the fixture, update these counts. The `IsTemplate` column needs
  synapseclient ≥ 4.15.0 (older releases needed a develop image).

## Conventions

- `main()` returns an exit code (0/1) and catches all exceptions. Do not raise
  or call `sys.exit` inside it. The `except Exception` has a
  `# noqa: BLE001 # pylint: disable=broad-exception-caught` comment. If you
  remove it, ruff and pylint fail. `write_github_output()` writes the outputs.
  Keep `main()` at 15 local variables or fewer (pylint `too-many-locals`).
- Use GitHub workflow commands for messages: `::error::` to **stderr**,
  `::warning::` and `::notice::` to **stdout**. The tests check the stream
  (`captured.err` vs `captured.out`) and the exact text, for example:

  ```text
  ::error::Schema generation failed: 'InvalidType' is not a valid datatype in the data model
  ```

- To add or rename an input or output, change all 5 places: `action.yml`
  `inputs`/`outputs`, `action.yml` `runs.env`, the script, the `README.md`
  Inputs/Outputs tables, and the lists in `tests/unit/test_generate_setup.py`.
  (Revert `8cc401a` in the old `Sage-Bionetworks-Actions/generate-jsonschema`
  repository restored an `output-directory` input that was lost from
  `action.yml` in a linter fix.)
- `tests/unit/test_generate_setup.py` checks only `action.yml`. Do not add
  checks for the `Dockerfile` or the script source here. The Docker CI jobs and
  the `TestMain` class in `tests/unit/test_generate_functions.py` already find
  those problems. Its fixtures and shared checks come from
  `shared/action_yml_checks.py` (see "Shared test helper" in the root
  `CLAUDE.md`).

## Constraints

- For the base image rules (`FROM` tag, digest, release tags, no `pip install`,
  `python-version` in `generate-jsonschema-ci.yml`), see "Constraints" in the
  root `CLAUDE.md`.
- Create `Synapse()` with no login. Schema generation does not need auth, and
  the action has no token input (SYNPY-1762).

## Testing

- The tests are in `tests/unit/`. The fixture `data_model.csv` stays in `tests/`
  because CI and the `README.md` use that path.
  `tests/unit/test_generate_functions.py` tests each helper function in one
  pytest class.
- The `TestMain` class in `tests/unit/test_generate_functions.py` calls `main()`
  for real against the installed synapseclient. It does not mock anything. Set
  inputs with `monkeypatch.setenv`/`delenv`. An autouse fixture in the class
  does `chdir` to `tmp_path`, so the output goes there. The fixture also removes
  all the input env vars and `GITHUB_OUTPUT`, because the CI runner sets
  `GITHUB_OUTPUT`.
- To test a new behavior, add a fixture CSV next to `data_model.csv` (for
  example, for conditionals; the current fixture has none). Do not edit the
  shared fixture, because many tests use its counts.

## Related Systems

- `register-jsonschema` (sibling action): uses the same base image and the same
  rule (one version source).
- Behavior changes in schema output come from synapseclient releases, for
  example SYNPY-1769 (property order). Before you change the image tag, compare
  the output for `tests/data_model.csv` from the old and new images.
