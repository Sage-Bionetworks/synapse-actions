#!/usr/bin/env python3
"""GitHub Action to generate JSON schemas from data models using synapseclient."""

import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

from synapseclient import Synapse
from synapseclient.extensions.curator import generate_jsonschema


def main() -> int:
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
    if not validate_data_model_source(data_model_source):
        return 1

    data_types = parse_data_types(os.environ.get("DATA_TYPES"))

    # An empty value (input set to '') uses the default
    data_model_labels = os.environ.get("DATA_MODEL_LABELS") or "class_label"
    if not validate_data_model_labels(data_model_labels):
        return 1

    # Create output directory relative to current working directory
    # This ensures it's created in the GitHub workspace where artifacts can be uploaded
    # An empty value (input set to '') uses the default
    output_dir_name = os.environ.get("OUTPUT_DIRECTORY") or "schemas"
    output_dir = os.path.join(os.getcwd(), output_dir_name)
    os.makedirs(output_dir, exist_ok=True)

    print_header(data_model_source, data_types, data_model_labels, output_dir)

    try:
        syn = Synapse()
        schemas, file_paths = generate_jsonschema(
            data_model_source=data_model_source,
            synapse_client=syn,
            data_types=data_types,
            output=output_dir,
            data_model_labels=data_model_labels,
        )
        write_github_output(resolve_output_path(output_dir_name, output_dir), schemas)
        print_summary(file_paths)
        return 0

    # main() must catch all errors and return an exit code
    except Exception as e:  # noqa: BLE001 # pylint: disable=broad-exception-caught
        print(f"::error::Schema generation failed: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1


def validate_data_model_source(data_model_source: str | None) -> bool:
    """
    Check that the data model source is set, and that a local file exists.

    A URL source (http:// or https://) has no file-exists check.

    Args:
        data_model_source: URL or local path to the data model file

    Returns:
        True if the source is valid. False (after an error message) if not.
    """
    if not data_model_source:
        print("::error::DATA_MODEL_SOURCE is required", file=sys.stderr)
        return False
    if data_model_source.startswith(("http://", "https://")):
        return True
    if not Path(data_model_source).exists():
        print(
            f"::error::Data model file not found: {data_model_source}",
            file=sys.stderr,
        )
        return False
    return True


def parse_data_types(data_types_str: str | None) -> list[str] | None:
    """
    Parse the comma-separated DATA_TYPES value.

    Args:
        data_types_str: Comma-separated list of data types

    Returns:
        None if the value is not set or empty (all types). Otherwise the list of
        stripped, non-empty data types. This list is empty if the value has only
        whitespace and commas.
    """
    if not data_types_str:
        return None
    return [dt.strip() for dt in data_types_str.split(",") if dt.strip()]


def validate_data_model_labels(data_model_labels: str) -> bool:
    """
    Check that the data model labels value is class_label or display_label.

    Args:
        data_model_labels: The DATA_MODEL_LABELS value

    Returns:
        True if the value is valid. False (after an error message) if not.
    """
    if data_model_labels in ("class_label", "display_label"):
        return True
    print(
        f"::error::Invalid DATA_MODEL_LABELS '{data_model_labels}'. "
        "Use 'class_label' or 'display_label'",
        file=sys.stderr,
    )
    return False


def resolve_output_path(output_dir_name: str, output_dir: str) -> str:
    """
    Get the path to write as the schemas output.

    The path is relative to the workspace, because the absolute path in the
    container (/github/workspace/...) does not exist on the runner host.

    Args:
        output_dir_name: The OUTPUT_DIRECTORY value
        output_dir: Absolute path of the output directory

    Returns:
        output_dir if output_dir_name is absolute, else the relative path of
        output_dir from the current working directory.
    """
    if os.path.isabs(output_dir_name):
        return output_dir
    return os.path.relpath(output_dir)


def print_header(
    data_model_source: str,
    data_types: list[str] | None,
    data_model_labels: str,
    output_dir: str,
) -> None:
    """
    Print a banner with the action inputs.

    Args:
        data_model_source: URL or local path to the data model file
        data_types: Data types to generate, or None for all types
        data_model_labels: class_label or display_label
        output_dir: Absolute path of the output directory
    """
    print(f"\n{'=' * 60}")
    print("JSON Schema Generation")
    print(f"{'=' * 60}")
    print(f"Data Model Source: {data_model_source}")
    print(f"Data Types: {data_types}")
    print(f"Data Model Labels: {data_model_labels}")
    print(f"Output Directory: {output_dir}")
    print(f"{'=' * 60}\n")


def write_github_output(output_dir: str, schemas: list[dict[str, Any]]) -> None:
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


def print_summary(file_paths: list[str]) -> None:
    """
    Print a notice with the number of generated schemas, and their file names.

    Args:
        file_paths: Paths of the generated schema files
    """
    print(f"::notice::Successfully generated {len(file_paths)} schema(s)")
    for path in file_paths:
        print(f"  - {Path(path).name}")


if __name__ == "__main__":
    sys.exit(main())
