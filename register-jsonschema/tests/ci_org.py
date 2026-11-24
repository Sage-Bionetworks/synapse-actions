"""
Create or delete the temporary Synapse organization of one CI run.

The register-jsonschema CI runs this script in the base image of the
Dockerfile, so it uses the same synapseclient version as the action.

Usage:
    python ci_org.py create <org-name>
    python ci_org.py delete <org-name>

The SYNAPSE_AUTH_TOKEN environment variable must have a valid token.
The delete command deletes all schemas in the organization first, because
Synapse cannot delete an organization that has schemas.
"""

import os
import sys

from synapseclient import Synapse
from synapseclient.models import Organization


def create_org(syn: Synapse, org_name: str) -> None:
    """
    Create the organization.

    Args:
        syn: Synapse client
        org_name: Organization name
    """
    Organization(name=org_name).store(synapse_client=syn)
    print(f"Created organization: {org_name}")


def delete_org(syn: Synapse, org_name: str) -> None:
    """
    Delete all schemas in the organization, then delete the organization.

    Args:
        syn: Synapse client
        org_name: Organization name
    """
    org = Organization(name=org_name)
    org.get(synapse_client=syn)
    for schema in org.get_json_schemas(synapse_client=syn):
        schema.delete(synapse_client=syn)
        print(f"Deleted schema: {schema.name}")
    org.delete(synapse_client=syn)
    print(f"Deleted organization: {org_name}")


def main(argv: list[str]) -> int:
    """
    Run the create or delete command.

    Args:
        argv: The command line arguments, without the script name

    Returns:
        0 on success, 1 on wrong arguments
    """
    commands = {"create": create_org, "delete": delete_org}
    if len(argv) != 2 or argv[0] not in commands:
        print("::error::Usage: ci_org.py create|delete <org-name>", file=sys.stderr)
        return 1
    command, org_name = argv
    syn = Synapse()
    # Give the token directly, because synapseclient reads ~/.synapseConfig
    # before the SYNAPSE_AUTH_TOKEN env var
    syn.login(authToken=os.environ["SYNAPSE_AUTH_TOKEN"], silent=True)
    commands[command](syn, org_name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
