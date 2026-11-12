# Synapse Actions

[![Linter](https://github.com/Sage-Bionetworks/synapse-actions/actions/workflows/linter.yml/badge.svg)](https://github.com/Sage-Bionetworks/synapse-actions/actions/workflows/linter.yml)

GitHub Actions for [Synapse](https://www.synapse.org/). Each action is a Docker
container action that uses the
[Synapse Python Client](https://python-docs.synapse.org/).

## Actions

| Action                                               | Description                                                 | CI                                                                                                                                                                                                                                        |
| ---------------------------------------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [generate-jsonschema](generate-jsonschema/README.md) | Generate JSON Schema files from a CSV or JSONLD data model. | [![generate-jsonschema CI](https://github.com/Sage-Bionetworks/synapse-actions/actions/workflows/generate-jsonschema-ci.yml/badge.svg)](https://github.com/Sage-Bionetworks/synapse-actions/actions/workflows/generate-jsonschema-ci.yml) |
| [register-jsonschema](register-jsonschema/README.md) | Register JSON Schema files in a Synapse organization.       | [![register-jsonschema CI](https://github.com/Sage-Bionetworks/synapse-actions/actions/workflows/register-jsonschema-ci.yml/badge.svg)](https://github.com/Sage-Bionetworks/synapse-actions/actions/workflows/register-jsonschema-ci.yml) |

See the `README.md` of each action for its inputs, outputs and examples.

## Usage

Refer to an action with its directory name and a version tag:

```yaml
uses: Sage-Bionetworks/synapse-actions/<action>@v1
```

This example generates JSON Schemas from a data model and then registers them in
Synapse:

```yaml
jobs:
  schemas:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v7

      - name: Generate JSON Schemas from the data model
        id: generate
        uses: Sage-Bionetworks/synapse-actions/generate-jsonschema@v1
        with:
          data-model-source: ./models/data.model.csv

      - name: Register the JSON Schemas in Synapse
        uses: Sage-Bionetworks/synapse-actions/register-jsonschema@v1
        with:
          org-name: my.organization
          schema-dir: ${{ steps.generate.outputs.schemas }}
          synapse-auth-token: ${{ secrets.SYNAPSE_AUTH_TOKEN }}
```

## Versions

One `vX.Y.Z` tag versions all actions in this repository together. The `v1` tag
moves to the latest 1.x release. A breaking change in one action gives a new
major version for all actions.

## Migration

This repository replaces these repositories:

- `Sage-Bionetworks-Actions/generate-jsonschema`
- `Sage-Bionetworks-Actions/register-jsonschema`

To migrate, change each `uses:` line in your workflows:

```yaml
# Old
uses: Sage-Bionetworks-Actions/generate-jsonschema@v1.0.0
# New
uses: Sage-Bionetworks/synapse-actions/generate-jsonschema@v1
```

## Linting

CI runs [super-linter](https://github.com/super-linter/super-linter) on all
files (`.github/workflows/linter.yml`). To run the same checks locally, run this
command from the repository root. Use the same super-linter image version and
settings as the workflow:

```bash
docker run --rm \
  -e RUN_LOCAL=true \
  -e DEFAULT_BRANCH=main \
  -e FILTER_REGEX_EXCLUDE='register-jsonschema/tests/non_schema_dir/.*' \
  -e LINTER_RULES_PATH=. \
  -e CHECKOV_FILE_NAME=.checkov.yml \
  -e VALIDATE_ALL_CODEBASE=true \
  -e VALIDATE_BIOME_FORMAT=false \
  -e VALIDATE_BIOME_LINT=false \
  -e VALIDATE_GITHUB_ACTIONS_ZIZMOR=false \
  -v "$(pwd)":/tmp/lint \
  ghcr.io/super-linter/super-linter:slim-v9.0.0
```

The `non_schema_dir` test fixture is not valid JSON on purpose, so the command
excludes it.

The linter configs are in the repository root (for example `.markdown-lint.yml`,
`.prettierrc.yml`, `.ruff.toml`). Linters without a config file there use the
super-linter defaults.

## Security

To report a security issue, see [SECURITY.md](SECURITY.md).

## License

See [LICENSE](LICENSE).
