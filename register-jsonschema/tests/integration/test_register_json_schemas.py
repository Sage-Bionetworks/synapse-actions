"""Integration tests for main(). They run against the real Synapse."""

# pytest fixtures are passed to tests as arguments with the same name.
# pylint: disable=redefined-outer-name

import sys
import uuid
from pathlib import Path

import pytest
from synapseclient import Synapse
from synapseclient.models import Organization

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))
from register_json_schemas import (  # noqa: E402 # pylint: disable=wrong-import-position
    main,
)

DATA_DIR = Path(__file__).parents[1] / "data"


def check_one_failure(stdout: str, github_output: str) -> None:
    """
    Check that main() printed the summary and wrote the output after a failure.

    Args:
        stdout: The captured stdout of main()
        github_output: Path to the GITHUB_OUTPUT file
    """
    assert "Registration Summary" in stdout
    assert "Total Processed: 1\nSuccessful: 0\nFailed: 1\n" in stdout
    output = Path(github_output).read_text(encoding="utf-8")
    assert output == "uris<<EOF\n\nEOF\n"


def check_success(github_output: str, org_name: str) -> None:
    """
    Check that main() wrote the URIs of the two registered schemas to the output.

    Args:
        github_output: Path to the GITHUB_OUTPUT file
        org_name: Name of the organization that the schemas are registered in
    """
    lines = Path(github_output).read_text(encoding="utf-8").splitlines()
    assert lines[0] == "uris<<EOF"
    assert lines[-1] == "EOF"
    uris = lines[1:-1]
    assert len(uris) == 2
    assert all(uri.startswith(f"{org_name}-") for uri in uris)


@pytest.fixture(scope="module")
def synapse_client() -> Synapse:
    """Create a Synapse client for testing."""
    syn = Synapse()
    syn.login()
    return syn


@pytest.fixture(scope="module")
def organization(
    request: pytest.FixtureRequest, synapse_client: Synapse
) -> Organization:
    """Create a test organization for schema registration."""
    org_name = f"test.org.id{str(uuid.uuid4())[:8]}"
    org = Organization(org_name)
    org.store(synapse_client=synapse_client)

    def cleanup() -> None:
        for schema in org.get_json_schemas(synapse_client=synapse_client):
            schema.delete(synapse_client=synapse_client)
        org.delete(synapse_client=synapse_client)

    request.addfinalizer(cleanup)
    return org


@pytest.fixture(scope="function")
def text_file_path(tmp_path: Path) -> str:
    """Give a GITHUB_OUTPUT file path in the pytest temporary directory."""
    return str(tmp_path / "text.txt")


class TestRegisterJsonSchemas:
    """Integration tests for the main function."""

    @pytest.fixture(autouse=True, scope="function")
    def init(
        self,
        monkeypatch: pytest.MonkeyPatch,
        organization: Organization,
        text_file_path: str,
    ) -> None:
        """Set the environment variables that all tests use."""
        monkeypatch.setenv("ORG_NAME", organization.name)
        monkeypatch.setenv("VERSION", "v1.0.0")
        monkeypatch.setenv("SCHEMA_DIR", str(DATA_DIR / "schema_dir"))
        monkeypatch.setenv("GITHUB_OUTPUT", text_file_path)

    def test_success(
        self,
        capsys: pytest.CaptureFixture[str],
        organization: Organization,
        text_file_path: str,
    ) -> None:
        """Integration test for registering JSON schemas from a directory."""
        # GIVEN a directory with two valid schemas and VERSION set to v1.0.0
        # WHEN I register the schemas
        result = main()

        # THEN both schemas are registered with version 1.0.0
        assert result == 0
        captured = capsys.readouterr()
        assert "Fix Schema Name: False" in captured.out
        assert "Registered: Patient version 1.0.0" in captured.out
        assert "Registered: Biospecimen version 1.0.0" in captured.out
        # AND the URIs of both schemas are written to GITHUB_OUTPUT
        check_success(text_file_path, organization.name)

    def test_success_no_version_env_var(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        organization: Organization,
        text_file_path: str,
    ) -> None:
        """Integration test for registering JSON schemas from a directory."""
        # GIVEN a directory with two valid schemas and no VERSION
        monkeypatch.delenv("VERSION", raising=False)

        # WHEN I register the schemas
        result = main()

        # THEN both schemas are registered with no version
        assert result == 0
        captured = capsys.readouterr()
        assert "Registered: Patient version None" in captured.out
        assert "Registered: Biospecimen version None" in captured.out
        # AND the URIs of both schemas are written to GITHUB_OUTPUT
        check_success(text_file_path, organization.name)

    def test_success_fix_schema_name(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        organization: Organization,
        text_file_path: str,
    ) -> None:
        """
        Integration test for registering JSON schemas from a directory.
        This test verifies that when the FIX_SCHEMA_NAME environment variable is set to "true"
        the schema names are fixed by replacing dashes and underscores with periods.
        """
        # GIVEN schemas with dashes and underscores in their names
        # AND FIX_SCHEMA_NAME set to true
        monkeypatch.setenv("FIX_SCHEMA_NAME", "true")
        monkeypatch.setenv("SCHEMA_DIR", str(DATA_DIR / "schema_dir_invalid_names"))

        # WHEN I register the schemas
        result = main()

        # THEN both schemas are registered with periods in their names
        assert result == 0
        captured = capsys.readouterr()
        assert "Fix Schema Name: True" in captured.out
        assert "Registered: Patient.Schema version 1.0.0" in captured.out
        assert "Registered: Biospecimen.Schema version 1.0.0" in captured.out
        # AND the URIs of both schemas are written to GITHUB_OUTPUT
        check_success(text_file_path, organization.name)

    def test_org_does_not_exist(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Integration test for registering JSON schemas from a directory."""
        # GIVEN an organization that does not exist in Synapse
        monkeypatch.setenv("ORG_NAME", "not_a_real_org")

        # WHEN I register the schemas
        result = main()

        # THEN registration fails with an organization not found error
        assert result == 1
        captured = capsys.readouterr()
        assert "::error:: Organization not found: not_a_real_org" in captured.err

    def test_non_json(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        text_file_path: str,
    ) -> None:
        """A file that is not JSON fails, and main() still prints the summary."""
        # GIVEN a directory with a file that is not valid JSON
        monkeypatch.setenv("SCHEMA_DIR", str(DATA_DIR / "non_schema_dir"))

        # WHEN I register the schemas
        result = main()

        # THEN registration fails with a JSON decode error
        assert result == 1
        captured = capsys.readouterr()
        json_file = DATA_DIR / "non_schema_dir" / "Patient.json"
        assert (
            f"::error:: {json_file}: Failed to register: "
            "Expecting value: line 1 column 1 (char 0)"
        ) in captured.err
        # AND the summary shows one failure and GITHUB_OUTPUT has no URIs
        check_one_failure(captured.out, text_file_path)

    def test_malformed_json(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        text_file_path: str,
    ) -> None:
        """JSON that Synapse rejects fails, and main() still prints the summary."""
        # GIVEN a directory with a JSON schema that Synapse does not accept
        monkeypatch.setenv("SCHEMA_DIR", str(DATA_DIR / "malformed_schema_dir"))

        # WHEN I register the schemas
        result = main()

        # THEN registration fails with the Synapse error
        assert result == 1
        captured = capsys.readouterr()
        json_file = DATA_DIR / "malformed_schema_dir" / "Patient.json"
        assert (
            f"::error:: {json_file}: Failed to register: "
            "400 Client Error: JSON Element in Entity is Unsupported: non_keyword"
        ) in captured.err
        # AND the summary shows one failure and GITHUB_OUTPUT has no URIs
        check_one_failure(captured.out, text_file_path)
