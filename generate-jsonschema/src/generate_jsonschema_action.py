#!/usr/bin/env python3
"""GitHub Action to generate JSON schemas from data models using synapseclient."""

import json
import os
import sys
import traceback
from pathlib import Path

from synapseclient import Synapse
from synapseclient.extensions.curator import generate_jsonschema


def write_github_output(output_dir, schemas):
    """
    Write the action outputs to the GITHUB_OUTPUT file, if it is set.

    Args:
        output_dir: Path of the directory with the generated schemas, relative to
            the workspace (or absolute if OUTPUT_DIRECTORY is absolute)
        schemas: List of the generated JSON schemas
    """
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        return
    with open(github_output, "a", encoding="utf-8") as f:
        f.write(f"schemas={output_dir}\n")
        # Output schemas as JSON for PR comment actions
        # GitHub Actions multiline output format
        f.write("schemas-json<<EOF\n")
        f.write(json.dumps(schemas))
        f.write("\nEOF\n")


def main():
    """
    Main function to generate JSON schemas from data models.

    Expects the following environment variables:
    - DATA_MODEL_SOURCE: URL or local path to the data model file (required)
    - DATA_TYPES: Comma-separated list of data types to include
      (optional, defaults to all)
    - DATA_MODEL_LABELS: 'class_label' or 'display_label' for schema
    - OUTPUT_DIRECTORY: Directory to output generated schema files
      (optional, defaults to 'schemas')
    - GITHUB_OUTPUT: Path to GitHub Actions output file
      (automatically provided in GitHub Actions environment)
    """
    data_model_source = os.environ.get("DATA_MODEL_SOURCE")
    if not data_model_source:
        print("::error::DATA_MODEL_SOURCE is required", file=sys.stderr)
        return 1

    # Validate data model file exists (if local path)
    if not data_model_source.startswith(("http://", "https://")):
        data_model_path = Path(data_model_source)
        if not data_model_path.exists():
            print(
                f"::error::Data model file not found: {data_model_source}",
                file=sys.stderr,
            )
            return 1

    # Parse data_types: empty string means all types (None)
    data_types_str = os.environ.get("DATA_TYPES", None)
    data_types = (
        [dt.strip() for dt in data_types_str.split(",") if dt.strip()]
        if data_types_str
        else None
    )

    # Validate data_model_labels
    data_model_labels = os.environ.get("DATA_MODEL_LABELS", "class_label")
    if data_model_labels not in ["class_label", "display_label"]:
        print(
            f"::warning::Invalid data_model_labels '{data_model_labels}', "
            f"using 'class_label'"
        )
        data_model_labels = "class_label"

    # Create output directory relative to current working directory
    # This ensures it's created in the GitHub workspace where artifacts can be uploaded
    output_dir_name = os.environ.get("OUTPUT_DIRECTORY", "schemas")
    output_dir = os.path.join(os.getcwd(), output_dir_name)
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'=' * 60}")
    print("JSON Schema Generation")
    print(f"{'=' * 60}")
    print(f"Data Model Source: {data_model_source}")
    print(f"Data Types: {data_types}")
    print(f"Data Model Labels: {data_model_labels}")
    print(f"Output Directory: {output_dir}")
    print(f"{'=' * 60}\n")

    try:
        syn = Synapse()
        schemas, file_paths = generate_jsonschema(
            data_model_source=data_model_source,
            synapse_client=syn,
            data_types=data_types,
            output=output_dir,
            data_model_labels=data_model_labels,
        )

        # Write a path relative to the workspace. The absolute path in the
        # container (/github/workspace/...) does not exist on the runner host.
        if os.path.isabs(output_dir_name):
            output_path = output_dir
        else:
            output_path = os.path.relpath(output_dir)
        write_github_output(output_path, schemas)

        # Print success summary
        print(f"::notice::Successfully generated {len(file_paths)} schema(s)")
        for path in file_paths:
            # Get just the filename for cleaner output
            print(f"  - {Path(path).name}")

        return 0

    # main() must catch all errors and return an exit code
    except Exception as e:  # noqa: BLE001 # pylint: disable=broad-exception-caught
        print(f"::error::Schema generation failed: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
