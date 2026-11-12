"""
Register JSON schemas to Synapse organization.

This script registers JSON schemas from a directory to a Synapse organization.
The semantic version is passed as a parameter, NOT included in the schema name.
"""

import os
import sys
from pathlib import Path

from synapseclient import Synapse
from synapseclient.extensions.curator import register_jsonschema
from synapseclient.models import JSONSchema, Organization


def main() -> int:
    """
    Main function to register JSON schemas into a Synapse organization.
    Expects the following environment variables:
    - ORG_NAME: Organization name
    - SCHEMA_DIR: Directory containing JSON schemas
    - SYNAPSE_AUTH_TOKEN: Synapse Personal Access Token.
    Can use the following optional environment variables:
    - VERSION: Semantic version (e.g., '1.0.0')
    - GITHUB_OUTPUT: JSON schema URIs will be appended to this
        file in GitHub Actions output format.
    - FIX_SCHEMA_NAME: If True, fixes the schema name to meet Synapse
        requirements by replacing dashes and underscores with periods.

    Returns:
        0 if all schemas registered, 1 if an input check, the login or one or
        more registrations failed
    """
    org_name = os.environ.get("ORG_NAME")
    schema_dir = os.environ.get("SCHEMA_DIR")
    github_output = os.environ.get("GITHUB_OUTPUT", None)
    synapse_pat = os.environ.get("SYNAPSE_AUTH_TOKEN", None)
    # The action sets VERSION to "" when the input is not set
    version = os.environ.get("VERSION") or None
    fix_schema_name = os.environ.get("FIX_SCHEMA_NAME", "false").lower() == "true"

    if not org_name:
        print("::error:: ORG_NAME environment variable is required", file=sys.stderr)
        return 1

    if not schema_dir:
        print("::error:: SCHEMA_DIR environment variable is required", file=sys.stderr)
        return 1

    # Remove the "v" prefix before the header, so all log lines show one version
    if version and version.startswith("v"):
        version = version[1:]

    print_header(org_name, schema_dir, version, fix_schema_name, synapse_pat)

    schema_path = Path(schema_dir)
    if not schema_path.exists():
        print(f"::error:: Schema directory not found: {schema_path}", file=sys.stderr)
        return 1

    json_files = list(schema_path.glob("*.json"))
    if not json_files:
        print(f"::error:: No JSON files found in: {schema_path}", file=sys.stderr)
        return 1

    syn = Synapse()
    try:
        # Give the token directly, because synapseclient reads ~/.synapseConfig
        # before the SYNAPSE_AUTH_TOKEN env var
        syn.login(authToken=synapse_pat)
    except Exception as e:  # noqa: BLE001 # pylint: disable=broad-exception-caught
        print("::error:: Synapse login failed", file=sys.stderr)
        print(f"::error:: {e!s}", file=sys.stderr)
        return 1

    try:
        org = Organization(name=org_name)
        org.get(synapse_client=syn)
        print(f"✓ Organization found: {org_name}\n")
    except Exception as e:  # noqa: BLE001 # pylint: disable=broad-exception-caught
        print(f"::error:: Organization not found: {org_name}", file=sys.stderr)
        print(f"::error:: {e!s}", file=sys.stderr)
        return 1

    print(f"Found {len(json_files)} JSON schema file(s)\n")

    results = [
        register_schema(syn, json_file, org_name, version, fix_schema_name)
        for json_file in sorted(json_files)
    ]
    success_count = sum(1 for result in results if result)
    failed_count = len(results) - success_count

    if github_output:
        write_github_output(github_output, results)

    print_summary(len(json_files), success_count, failed_count)

    if failed_count > 0:
        return 1
    return 0


def print_header(
    org_name: str,
    schema_dir: str,
    version: str | None,
    fix_schema_name: bool,
    synapse_pat: str | None,
) -> None:
    """
    Print the registration settings.

    Args:
        org_name: Organization name
        schema_dir: Directory containing JSON schemas
        version: Semantic version (e.g., '1.0.0')
        fix_schema_name: If True, the schema names will be fixed
        synapse_pat: Synapse Personal Access Token, if set
    """
    print(f"\n{'=' * 60}")
    print("JSON Schema Registration")
    print(f"{'=' * 60}")
    print(f"Fix Schema Name: {fix_schema_name}")
    if synapse_pat:
        print("Synapse PAT is set")
    else:
        print("Synapse PAT is not set")
    print(f"Organization: {org_name}")
    print(f"Version: {version}")
    print(f"Schema Directory: {schema_dir}")
    print(f"{'=' * 60}\n")


def write_github_output(github_output: str, results: list[JSONSchema | None]) -> None:
    """
    Append the URIs of the registered schemas to the GitHub Actions output file.

    Args:
        github_output: Path to the GitHub Actions output file
        results: The registered schemas
    """
    uris = [schema.uri for schema in results if schema is not None]
    with open(github_output, "a", encoding="utf-8") as file:
        file.write("uris<<EOF\n")
        file.write("\n".join(uris))
        file.write("\nEOF\n")


def print_summary(total_count: int, success_count: int, failed_count: int) -> None:
    """
    Print the registration summary.

    Args:
        total_count: Number of JSON schema files processed
        success_count: Number of schemas registered
        failed_count: Number of schemas not registered
    """
    print(f"{'=' * 60}")
    print("Registration Summary")
    print(f"{'=' * 60}")
    print(f"Total Processed: {total_count}")
    print(f"Successful: {success_count}")
    print(f"Failed: {failed_count}")
    print(f"{'=' * 60}")


def register_schema(
    syn: Synapse,
    json_file: Path,
    org_name: str,
    version: str | None,
    fix_schema_name: bool = False,
) -> JSONSchema | None:
    """
    Register a single JSON schema to Synapse.
    A failure prints an error and does not stop the run, so main() can try the
    other files, print the summary and write the output.

    Args:
        syn: Synapse client
        json_file: Path to JSON schema file
        org_name: Organization name
        version: Semantic version (e.g., '1.0.0')
        fix_schema_name: If True, fixes the schema name to meet Synapse
          requirements by replacing dashes and underscores with periods.

    Returns:
        JSONSchema object if successful, None if the registration failed
    """

    print(f"Processing: {json_file.name}")

    schema_name = json_file.stem

    print(f"  Schema Name: {schema_name}")
    print(f"  Version: {version!s}")

    try:
        schema = register_jsonschema(
            schema_path=str(json_file),
            organization_name=org_name,
            schema_name=schema_name,
            schema_version=version,
            synapse_client=syn,
            fix_schema_name=fix_schema_name,
        )

        print(f"✓ Registered: {schema.name} version {version!s}")
        return schema

    except Exception as e:  # noqa: BLE001 # pylint: disable=broad-exception-caught
        print(f"::error:: {json_file}: Failed to register: {e!s}", file=sys.stderr)
        return None


if __name__ == "__main__":
    sys.exit(main())
