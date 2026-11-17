# Register JSON Schema

[![Continuous Integration](https://github.com/Sage-Bionetworks/synapse-actions/actions/workflows/register-jsonschema-ci.yml/badge.svg)](https://github.com/Sage-Bionetworks/synapse-actions/actions/workflows/register-jsonschema-ci.yml)
[![Linter](https://github.com/Sage-Bionetworks/synapse-actions/actions/workflows/linter.yml/badge.svg)](https://github.com/Sage-Bionetworks/synapse-actions/actions/workflows/linter.yml)

Register JSON Schema files with Synapse using the Synapse Python client.

This action is intended to be used in conjunction with the
[Generate JSON Schemas](https://github.com/Sage-Bionetworks/synapse-actions/tree/main/generate-jsonschema)
action, which generates JSON Schema files from a data model.

## Usage

```yaml
steps:
  - name: Register Schemas
    uses: Sage-Bionetworks/synapse-actions/register-jsonschema@v1
    with:
      org-name: 'my.organization'
      schema-dir: './schemas'
      version: '1.0.0'
      synapse-auth-token: ${{ secrets.SYNAPSE_AUTH_TOKEN }}
```

## Inputs

| Input                | Description                                                                                                     | Required | Default   |
| :------------------- | :-------------------------------------------------------------------------------------------------------------- | :------- | :-------- |
| `org-name`           | Name of the Synapse organization to register schemas in.                                                        | `true`   | -         |
| `schema-dir`         | Path to directory containing JSON schema files.                                                                 | `true`   | -         |
| `version`            | Semantic version of the schemas being registered. A leading `v` is removed (`v1.0.0` becomes `1.0.0`).          | `false`  | `''`      |
| `synapse-auth-token` | Synapse Personal Access Token with permissions to register schemas in the Synapse organization.                 | `true`   | -         |
| `fix-schema-name`    | If `true`, fixes the schema name to meet Synapse requirements by replacing dashes and underscores with periods. | `false`  | `'false'` |

## Outputs

| Output | Description                                       |
| :----- | :------------------------------------------------ |
| `uris` | URIs of registered schemas, one URI on each line. |

## Failures

The action tries to register each JSON file in `schema-dir`, also if a file
before it fails. At the end, it prints a registration summary. If one or more
files fail, the step fails, but the `uris` output still has the URIs of the
schemas that registered. To use these URIs after a failure, set
`continue-on-error: true` on the step, or use `if: always()` on the next step.

Synapse cannot overwrite a schema version that is registered. Thus, if you run
the action again with the same `version`, each schema that registered before
fails.

## Example Workflow

The following example demonstrates a full workflow that generates a schema using
the companion action and then registers it to Synapse.

```yaml
name: CI

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        id: checkout
        uses: actions/checkout@v7

      - name: Generate JSON Schemas
        id: generate
        uses: Sage-Bionetworks/synapse-actions/generate-jsonschema@v1
        with:
          data-model-source: ./models/data.model.csv
          data-model-labels: 'display_label'

      - name: Register JSON Schemas
        id: register
        uses: Sage-Bionetworks/synapse-actions/register-jsonschema@v1
        with:
          org-name: my.organization
          fix-schema-name: 'true'
          schema-dir: ${{ steps.generate.outputs.schemas }}
          synapse-auth-token: ${{ secrets.SYNAPSE_AUTH_TOKEN }}
```

## License

This project is licensed under the [MIT License](../LICENSE).
