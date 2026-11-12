"""Tests for main(). Most tests run against the real Synapse."""

# pytest fixtures are passed to tests as arguments with the same name.
# pylint: disable=redefined-outer-name

import sys
import uuid
from pathlib import Path

import pytest
from synapseclient import Synapse
from synapseclient.models import Organization

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from register_json_schemas import (  # noqa: E402 # pylint: disable=wrong-import-position
    main,
)

TESTS_DIR = Path(__file__).parent


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
def organization(request, synapse_client: Synapse) -> Organization:
    """Create a test organization for schema registration."""
    org_name = f"test.org.id{str(uuid.uuid4())[:8]}"
    org = Organization(org_name)
    org.store(synapse_client=synapse_client)

    def cleanup():
        for schema in org.get_json_schemas(synapse_client=synapse_client):
            schema.delete(synapse_client=synapse_client)
        org.delete(synapse_client=synapse_client)

    request.addfinalizer(cleanup)
    return org


@pytest.fixture(scope="function")
def empty_folder_path(tmp_path: Path) -> str:
    """Create an empty folder in the pytest temporary directory."""
    directory_path = tmp_path / "empty_test_dir"
    directory_path.mkdir()
    return str(directory_path)


@pytest.fixture(scope="function")
def text_file_path(tmp_path: Path) -> str:
    """Give a GITHUB_OUTPUT file path in the pytest temporary directory."""
    return str(tmp_path / "text.txt")


class TestRegisterJsonSchemas:
    """Integration tests for the main function."""

    @pytest.fixture(autouse=True, scope="function")
    def init(
        self, monkeypatch, organization: Organization, text_file_path: str
    ) -> None:
        """Set the environment variables that all tests use."""
        monkeypatch.setenv("ORG_NAME", organization.name)
        monkeypatch.setenv("VERSION", "v1.0.0")
        monkeypatch.setenv("SCHEMA_DIR", str(TESTS_DIR / "schema_dir"))
        monkeypatch.setenv("GITHUB_OUTPUT", text_file_path)

    def test_success(
        self, capsys, organization: Organization, text_file_path: str
    ) -> None:
        """Integration test for registering JSON schemas from a directory."""
        assert main() == 0
        captured = capsys.readouterr()
        assert "Fix Schema Name: False" in captured.out
        assert "Registered: Patient version 1.0.0" in captured.out
        assert "Registered: Biospecimen version 1.0.0" in captured.out
        check_success(text_file_path, organization.name)

    def test_success_no_version_env_var(
        self, monkeypatch, capsys, organization: Organization, text_file_path: str
    ) -> None:
        """Integration test for registering JSON schemas from a directory."""
        monkeypatch.delenv("VERSION", raising=False)
        assert main() == 0
        captured = capsys.readouterr()
        assert "Registered: Patient version None" in captured.out
        assert "Registered: Biospecimen version None" in captured.out
        check_success(text_file_path, organization.name)

    def test_success_fix_schema_name(
        self, monkeypatch, capsys, organization: Organization, text_file_path: str
    ) -> None:
        """
        Integration test for registering JSON schemas from a directory.
        This test verifies that when the FIX_SCHEMA_NAME environment variable is set to "true"
        the schema names are fixed by replacing dashes and underscores with periods.
        """
        monkeypatch.setenv("FIX_SCHEMA_NAME", "true")
        monkeypatch.setenv("SCHEMA_DIR", str(TESTS_DIR / "schema_dir_invalid_names"))
        assert main() == 0
        captured = capsys.readouterr()
        assert "Fix Schema Name: True" in captured.out
        assert "Registered: Patient.Schema version 1.0.0" in captured.out
        assert "Registered: Biospecimen.Schema version 1.0.0" in captured.out
        check_success(text_file_path, organization.name)

    def test_org_does_not_exist(self, monkeypatch, capsys) -> None:
        """Integration test for registering JSON schemas from a directory."""
        monkeypatch.setenv("ORG_NAME", "not_a_real_org")
        assert main() == 1
        captured = capsys.readouterr()
        assert "::error:: Organization not found: not_a_real_org" in captured.err

    def test_non_json(self, monkeypatch, capsys, text_file_path: str) -> None:
        """A file that is not JSON fails, and main() still prints the summary."""
        monkeypatch.setenv("SCHEMA_DIR", str(TESTS_DIR / "non_schema_dir"))
        assert main() == 1
        captured = capsys.readouterr()
        json_file = TESTS_DIR / "non_schema_dir" / "Patient.json"
        assert (
            f"::error:: {json_file}: Failed to register: "
            "Expecting value: line 1 column 1 (char 0)"
        ) in captured.err
        check_one_failure(captured.out, text_file_path)

    def test_malformed_json(self, monkeypatch, capsys, text_file_path: str) -> None:
        """JSON that Synapse rejects fails, and main() still prints the summary."""
        monkeypatch.setenv("SCHEMA_DIR", str(TESTS_DIR / "malformed_schema_dir"))
        assert main() == 1
        captured = capsys.readouterr()
        json_file = TESTS_DIR / "malformed_schema_dir" / "Patient.json"
        assert (
            f"::error:: {json_file}: Failed to register: "
            "400 Client Error: JSON Element in Entity is Unsupported: non_keyword"
        ) in captured.err
        check_one_failure(captured.out, text_file_path)


class TestInputChecks:
    """Tests for the input checks and the Synapse login. No token is necessary."""

    @pytest.fixture(autouse=True, scope="function")
    def init(self, monkeypatch) -> None:
        """Set valid inputs and remove the token, so a login attempt fails."""
        monkeypatch.setenv("ORG_NAME", "test.org")
        monkeypatch.setenv("SCHEMA_DIR", str(TESTS_DIR / "schema_dir"))
        monkeypatch.delenv("SYNAPSE_AUTH_TOKEN", raising=False)

    def test_no_org_env_var(self, monkeypatch, capsys) -> None:
        """A missing ORG_NAME gives an error before the login."""
        monkeypatch.delenv("ORG_NAME", raising=False)
        assert main() == 1
        captured = capsys.readouterr()
        assert "::error:: ORG_NAME environment variable is required" in captured.err

    def test_no_schema_dir_env_var(self, monkeypatch, capsys) -> None:
        """A missing SCHEMA_DIR gives an error before the login."""
        monkeypatch.delenv("SCHEMA_DIR", raising=False)
        assert main() == 1
        captured = capsys.readouterr()
        assert "::error:: SCHEMA_DIR environment variable is required" in captured.err

    def test_dir_does_not_exist(self, monkeypatch, capsys) -> None:
        """A schema directory that does not exist gives an error before the login."""
        monkeypatch.setenv("SCHEMA_DIR", str(TESTS_DIR / "not_a_real_directory"))
        assert main() == 1
        captured = capsys.readouterr()
        assert "::error:: Schema directory not found" in captured.err

    @pytest.mark.parametrize("set_empty", [True, False], ids=["empty", "unset"])
    def test_no_version(self, monkeypatch, capsys, set_empty: bool) -> None:
        """An empty VERSION, as the action gives, acts the same as no VERSION."""
        if set_empty:
            monkeypatch.setenv("VERSION", "")
        else:
            monkeypatch.delenv("VERSION", raising=False)
        # A missing directory stops main() after the header and before the login
        monkeypatch.setenv("SCHEMA_DIR", str(TESTS_DIR / "not_a_real_directory"))
        assert main() == 1
        assert "Version: None\n" in capsys.readouterr().out

    def test_empty_dir(self, monkeypatch, capsys, empty_folder_path: str) -> None:
        """A schema directory with no JSON files gives an error before the login."""
        monkeypatch.setenv("SCHEMA_DIR", empty_folder_path)
        assert main() == 1
        captured = capsys.readouterr()
        message = f"::error:: No JSON files found in: {empty_folder_path}"
        assert message in captured.err

    def test_invalid_token(self, monkeypatch, capsys) -> None:
        """A token that is not valid gives a login error, not a traceback."""
        monkeypatch.setenv("SYNAPSE_AUTH_TOKEN", "not_a_valid_token")
        assert main() == 1
        assert "::error:: Synapse login failed" in capsys.readouterr().err
