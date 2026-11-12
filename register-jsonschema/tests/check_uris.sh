#!/usr/bin/env bash
# Check the uris output of the register-jsonschema action in CI.
# Usage: URIS="<uris output>" check_uris.sh <expected-count> <org-name>
# The uris output has one URI on each line. Each URI must start with
# "<org-name>-", and the number of URIs must be <expected-count>.
set -euo pipefail

expected="$1"
org="$2"
count=0

while IFS= read -r uri; do
  if [ -z "$uri" ]; then
    continue
  fi
  count=$((count + 1))
  case "$uri" in
  "$org"-*) echo "Registered: $uri" ;;
  *)
    echo "::error::URI '$uri' does not start with '$org-'"
    exit 1
    ;;
  esac
done <<<"${URIS:-}"

if [ "$count" -ne "$expected" ]; then
  echo "::error::Expected $expected URIs, got $count"
  exit 1
fi
echo "Found $count URIs"
