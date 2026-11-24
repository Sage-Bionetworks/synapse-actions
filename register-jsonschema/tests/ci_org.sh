#!/usr/bin/env bash
# Create or delete the temporary Synapse org of one register-jsonschema CI run.
# Usage: SYNAPSE_AUTH_TOKEN=... ci_org.sh create|delete <org-name>
# Run from register-jsonschema/. The script runs tests/ci_org.py in the base
# image of the Dockerfile, so it uses the same synapseclient version as the
# action.
set -euo pipefail

base_image=$(sed -n 's/^FROM \([^ ]*\).*/\1/p' Dockerfile | head -n1)
if [ -z "$base_image" ]; then
	echo "::error::No FROM line in Dockerfile"
	exit 1
fi

docker run --rm -e SYNAPSE_AUTH_TOKEN \
	-v "$PWD/tests/ci_org.py:/ci_org.py:ro" \
	--entrypoint python "$base_image" /ci_org.py "$@"
