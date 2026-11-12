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
- **Input rules in `main()`:** If `DATA_TYPES` is not set or empty, it becomes
  `None`. If it has only whitespace and commas, it becomes `[]`. synapseclient
  makes all types for the two values (`test_main_with_empty_data_type`). A
  source that starts with `http://`/`https://` has no file-exists check. An
  empty `DATA_MODEL_LABELS` value becomes `class_label`. Other values that are
  not `class_label` or `display_label` give `::error::` and return 1
  (`test_main_invalid_labels`). An empty `OUTPUT_DIRECTORY` value becomes
  `schemas` (`test_main_with_empty_output_directory`). Use
  `os.environ.get(KEY) or default` for these inputs, not
  `os.environ.get(KEY, default)`, because `action.yml` always sets the env var.
- **Outputs** go to `$GITHUB_OUTPUT`: `schemas` is a path relative to the
  workspace (`os.path.relpath` of `OUTPUT_DIRECTORY`), or the absolute path if
  `OUTPUT_DIRECTORY` is absolute. Do not write the container path
  (`/github/workspace/...`), because it does not exist on the runner host.
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
  Inputs/Outputs tables, and the lists in `tests/test_action_setup.py`. (Revert
  `8cc401a` in the old `Sage-Bionetworks-Actions/generate-jsonschema` repository
  restored an `output-directory` input that was lost from `action.yml` in a
  linter fix.)
- `tests/test_action_setup.py` does string checks on the source: the script must
  contain `from synapseclient import Synapse`,
  `from synapseclient.extensions.curator import generate_jsonschema`,
  `def main():`, and `if __name__ == "__main__":`. The `README.md` must contain
  `# Generate JSON Schema Action`, `data-model-source`, and `schemas-json`. If
  you refactor imports or rename the title, the tests fail.

## Constraints

- For the base image rules (`FROM` tag, digest, release tags, no `pip install`,
  `python-version` in `generate-jsonschema-ci.yml`), see "Constraints" in the
  root `CLAUDE.md`.
- Create `Synapse()` with no login. Schema generation does not need auth, and
  the action has no token input (SYNPY-1762).

## Testing

- `tests/test_integration.py` calls `main()` for real against the installed
  synapseclient. It does not mock anything. Set inputs with
  `monkeypatch.setenv`/`delenv`. An autouse fixture does `chdir` to `tmp_path`,
  so the output goes there.
- To test a new behavior, add a fixture CSV next to `data_model.csv` (for
  example, for conditionals; the current fixture has none). Do not edit the
  shared fixture, because many tests use its counts.

## Related Systems

- `register-jsonschema` (sibling action): uses the same base image and the same
  rule (one version source).
- Behavior changes in schema output come from synapseclient releases, for
  example SYNPY-1769 (property order). Before you change the image tag, compare
  the output for `tests/data_model.csv` from the old and new images.
