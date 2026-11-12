# Generate JSON Schema Action

[![Continuous Integration](https://github.com/Sage-Bionetworks/synapse-actions/actions/workflows/generate-jsonschema-ci.yml/badge.svg)](https://github.com/Sage-Bionetworks/synapse-actions/actions/workflows/generate-jsonschema-ci.yml)
[![Linter](https://github.com/Sage-Bionetworks/synapse-actions/actions/workflows/linter.yml/badge.svg)](https://github.com/Sage-Bionetworks/synapse-actions/actions/workflows/linter.yml)

A GitHub Action to generate JSON Schema files from data models (CSV/JSONLD)
using the Synapse Python Client curator extension.

This action is part of the DPE-1554 implementation for automated JSON Schema
management in Synapse workflows.

## Usage

### Basic Example

```yaml
name: Validate Data Model
on:
  pull_request:
    types:
      - opened # When PR is first opened
      - synchronize # When new commits are pushed
      - labeled # When labels are added (optional - useful for manual triggers)
    branches:
      - 'main' # Only for PRs targeting main branch
    paths:
      - 'models/**' # Only trigger when model files change

jobs:
  generate-schemas:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7

      - name: Generate JSON Schemas
        id: generate
        uses: Sage-Bionetworks/synapse-actions/generate-jsonschema@v1
        with:
          data-model-source: ./models/data.model.csv
          # data-types omitted = generate all types

      - name: Upload schemas as artifacts
        uses: actions/upload-artifact@v7
        with:
          name: json-schemas
          path: ${{ steps.generate.outputs.schemas }}
```

We recommend these triggers, so the action runs only when relevant files change:

- **`types`**: `opened` validates schemas when a PR is created, `synchronize`
  validates them again on new commits, and `labeled` lets you start a run
  manually by adding a label.
- **`branches`**: the workflow runs only for PRs that target your main branch.
- **`paths`**: change this to your data model directories, so changes to
  unrelated files (for example documentation or tests) do not start a run.

### Generate Specific Schemas with Custom Labels

```yaml
- name: Generate Schemas for Specific Types
  id: generate
  uses: Sage-Bionetworks/synapse-actions/generate-jsonschema@v1
  with:
    data-model-source: ./models/biospecimen.model.csv
    data-types: 'Patient,Biospecimen,Analysis'
    data-model-labels: 'display_label'
```

### With PR Comment Integration

This action can be combined with
[mshick/add-pr-comment](https://github.com/mshick/add-pr-comment) to
automatically post schema summaries to Pull Requests:

```yaml
jobs:
  generate-schemas:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write # Needed to post the comment
    steps:
      # Checkout and "Generate JSON Schemas" (id: generate) steps from the
      # Basic Example go here.

      - name: Format Schema Report
        id: format
        env:
          SCHEMAS_JSON: ${{ steps.generate.outputs.schemas-json }}
        run: |
          python - <<'PYTHON'
          import json
          import os

          schemas = json.loads(os.environ["SCHEMAS_JSON"])

          # Build markdown report with collapsible sections
          report = "## Generated JSON Schemas\n\n"

          for schema in schemas:
              schema_name = schema.get('title', 'Unnamed Schema')
              schema_id = schema.get('$id', 'N/A')

              report += f"<details>\n<summary><strong>{schema_name}</strong></summary>\n\n"
              report += f"**Schema ID:** `{schema_id}`\n\n"

              # Add properties summary
              properties = schema.get('properties', {})
              if properties:
                  report += "**Properties:**\n"
                  for prop_name, prop_def in properties.items():
                      prop_type = prop_def.get('type', 'any')
                      required = '✓' if prop_name in schema.get('required', []) else ''
                      report += f"- `{prop_name}` ({prop_type}) {required}\n"

              report += "\n</details>\n\n"

          # Write to file
          with open('schema-report.md', 'w') as f:
              f.write(report)
          PYTHON

      - name: Comment PR with Schema Summary
        uses: mshick/add-pr-comment@ec328af66588ab8f77cdeb2c264f14aba45bbf59 # v3.12.0
        with:
          message-path: schema-report.md
          message-id: schema-generation
```

The `schemas-json` output contains the full array of schema dictionaries,
allowing you to create custom formatters and reports. The `message-id` parameter
ensures the comment is "sticky" and will update on subsequent runs rather than
creating multiple comments.

Give `schemas-json` to scripts through an environment variable, as in the
example. Do not put `${{ steps.generate.outputs.schemas-json }}` directly in a
script. The schema text comes from the data model, so it can break the script or
inject code.

## Inputs

| Input               | Description                                                                      | Required | Default       |
| ------------------- | -------------------------------------------------------------------------------- | -------- | ------------- |
| `data-model-source` | Path or URL to CSV or JSONLD data model file                                     | Yes      | -             |
| `data-types`        | Comma-separated list of data types to generate schemas for (leave empty for all) | No       | `''`          |
| `data-model-labels` | Label type to use: `class_label` or `display_label`                              | No       | `class_label` |
| `output-directory`  | Directory to output generated schema files                                       | No       | `schemas`     |

### About `data-model-labels`

- `class_label` (default): Uses standard attribute names as property keys
- `display_label`: Uses display names if valid (no blacklisted characters like
  parentheses, periods, spaces, or hyphens)
- Other values fail the action with an error.

## Outputs

| Output         | Description                                                                                                                                   |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `schemas`      | Path to directory containing generated schema files, relative to the workspace (e.g., `schemas`). Absolute if `output-directory` is absolute. |
| `schemas-json` | JSON string containing array of generated schema dictionaries for use with PR comment actions or other downstream processing                  |

## Local Development and Testing

### Running Unit Tests

Install dependencies and run tests:

```bash
# Install dependencies
# Use the synapseclient version from the Dockerfile base image tag
SYN_VERSION=$(sed -n 's/^FROM .*synapsepythonclient:v\([^ @]*\).*/\1/p' Dockerfile | head -n1)
pip install "synapseclient[pandas,curator]==${SYN_VERSION}"
pip install -r requirements.txt

# Run tests
pytest test -v
```

### Building the Docker Container

```bash
docker build -t generate-jsonschema-action .
```

### Testing with Docker

#### On Unix/macOS (Bash)

```bash
docker run --rm \
  -e DATA_MODEL_SOURCE="/test/data_model.csv" \
  -v $(pwd)/test:/test \
  generate-jsonschema-action
```

#### On Windows (PowerShell)

Use backticks (`` ` ``) for line continuation, and use `${PWD}` for the current
directory. Use absolute Windows paths with forward slashes or double
backslashes.

```powershell
docker run --rm `
  -e DATA_MODEL_SOURCE="/test/data_model.csv" `
  -v "${PWD}/test:/test" `
  generate-jsonschema-action
```

### Linting

To lint the full repository locally, see "Linting" in the
[root `README.md`](../README.md#linting).

## Related Actions

This action is designed to work with:

- [register-jsonschema][register-jsonschema] - Register generated schemas to
  Synapse organizations
- [mshick/add-pr-comment](https://github.com/mshick/add-pr-comment) - Post
  schema summaries to Pull Requests

[register-jsonschema]:
  https://github.com/Sage-Bionetworks/synapse-actions/tree/main/register-jsonschema

## Documentation

- [Synapse Schema Operations Tutorial](https://python-docs.synapse.org/en/latest/tutorials/python/schema_operations/)
- [Synapse Curator Extension API Reference](https://python-docs.synapse.org/en/stable/reference/experimental/extensions/curator/)
- [Synapse Curator Extension Guide](https://python-docs.synapse.org/en/stable/guides/curator/)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the [MIT License](../LICENSE).

## Support

For issues and questions:

- Open an issue in this repository
- Check the [Synapse documentation](https://python-docs.synapse.org/)
- Visit the [Sage Bionetworks community forums](https://www.synapse.org/)
