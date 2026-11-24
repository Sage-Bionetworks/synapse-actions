"""Unit tests for each function of the script. No token is necessary."""

# pytest fixtures are passed to tests as arguments with the same name.
# pylint: disable=redefined-outer-name
# Some test classes have only one test.
# pylint: disable=too-few-public-methods

import sys
from pathlib import Path

import pytest
from synapseclient import Synapse
from synapseclient.models import JSONSchema

sys.path.insert(0, str(Path(__file__).parents[2] / "src"))
from register_json_schemas import (  # noqa: E402 # pylint: disable=wrong-import-position
    main,
    print_header,
    print_summary,
    register_schema,
    write_github_output,
)

DATA_DIR = Path(__file__).parents[1] / "data"


@pytest.fixture(scope="function")
def empty_folder_path(tmp_path: Path) -> str:
    """Create an empty folder in the pytest temporary directory."""
    directory_path = tmp_path / "empty_test_dir"
    directory_path.mkdir()
    return str(directory_path)


class TestInputChecks:
    """Tests for the input checks and the Synapse login. No token is necessary."""

    @pytest.fixture(autouse=True, scope="function")
    def init(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Set valid inputs and remove the token, so a login attempt fails."""
        monkeypatch.setenv("ORG_NAME", "test.org")
        monkeypatch.setenv("SCHEMA_DIR", str(DATA_DIR / "schema_dir"))
        monkeypatch.delenv("SYNAPSE_AUTH_TOKEN", raising=False)

    def test_no_org_env_var(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A missing ORG_NAME gives an error before the login."""
        # GIVEN no ORG_NAME
        monkeypatch.delenv("ORG_NAME", raising=False)

        # WHEN I register the schemas
        result = main()

        # THEN it fails with an ORG_NAME is required error
        assert result == 1
        captured = capsys.readouterr()
        assert "::error:: ORG_NAME environment variable is required" in captured.err

    def test_no_schema_dir_env_var(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A missing SCHEMA_DIR gives an error before the login."""
        # GIVEN no SCHEMA_DIR
        monkeypatch.delenv("SCHEMA_DIR", raising=False)

        # WHEN I register the schemas
        result = main()

        # THEN it fails with a SCHEMA_DIR is required error
        assert result == 1
        captured = capsys.readouterr()
        assert "::error:: SCHEMA_DIR environment variable is required" in captured.err

    def test_dir_does_not_exist(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A schema directory that does not exist gives an error before the login."""
        # GIVEN a SCHEMA_DIR that does not exist
        monkeypatch.setenv("SCHEMA_DIR", str(DATA_DIR / "not_a_real_directory"))

        # WHEN I register the schemas
        result = main()

        # THEN it fails with a schema directory not found error
        assert result == 1
        captured = capsys.readouterr()
        assert "::error:: Schema directory not found" in captured.err

    @pytest.mark.parametrize("set_empty", [True, False], ids=["empty", "unset"])
    def test_no_version(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        set_empty: bool,
    ) -> None:
        """An empty VERSION, as the action gives, acts the same as no VERSION."""
        # GIVEN an empty VERSION or no VERSION
        if set_empty:
            monkeypatch.setenv("VERSION", "")
        else:
            monkeypatch.delenv("VERSION", raising=False)
        # AND a missing directory, which stops main() before the login
        monkeypatch.setenv("SCHEMA_DIR", str(DATA_DIR / "not_a_real_directory"))

        # WHEN I register the schemas
        result = main()

        # THEN the header shows no version
        assert result == 1
        assert "Version: None\n" in capsys.readouterr().out

    def test_empty_dir(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
        empty_folder_path: str,
    ) -> None:
        """A schema directory with no JSON files gives an error before the login."""
        # GIVEN a SCHEMA_DIR with no JSON files
        monkeypatch.setenv("SCHEMA_DIR", empty_folder_path)

        # WHEN I register the schemas
        result = main()

        # THEN it fails with a no JSON files found error
        assert result == 1
        captured = capsys.readouterr()
        message = f"::error:: No JSON files found in: {empty_folder_path}"
        assert message in captured.err

    def test_invalid_token(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A token that is not valid gives a login error, not a traceback."""
        # GIVEN a SYNAPSE_AUTH_TOKEN that is not valid
        monkeypatch.setenv("SYNAPSE_AUTH_TOKEN", "not_a_valid_token")

        # WHEN I register the schemas
        result = main()

        # THEN it fails with a Synapse login error
        assert result == 1
        assert "::error:: Synapse login failed" in capsys.readouterr().err


class TestPrintHeader:
    """Tests for print_header()."""

    def test_all_settings(self, capsys: pytest.CaptureFixture[str]) -> None:
        """The header shows each setting."""
        # GIVEN all settings and a token

        # WHEN I print the header
        print_header("test.org", "schema_dir", "1.0.0", True, "a_token")

        # THEN the header shows each setting
        out = capsys.readouterr().out
        assert "JSON Schema Registration\n" in out
        assert "Fix Schema Name: True\n" in out
        assert "Synapse PAT is set\n" in out
        assert "Organization: test.org\n" in out
        assert "Version: 1.0.0\n" in out
        assert "Schema Directory: schema_dir\n" in out

    def test_does_not_show_token(self, capsys: pytest.CaptureFixture[str]) -> None:
        """The header does not show the token value."""
        # GIVEN a token
        token = "secret_token_value"

        # WHEN I print the header
        print_header("test.org", "schema_dir", "1.0.0", False, token)

        # THEN the token value is not in the output
        captured = capsys.readouterr()
        assert token not in captured.out + captured.err

    def test_no_token_no_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        """The header shows that no token and no version are set."""
        # GIVEN no token and no version

        # WHEN I print the header
        print_header("test.org", "schema_dir", None, False, None)

        # THEN the header shows that the token is not set
        out = capsys.readouterr().out
        assert "Synapse PAT is not set\n" in out
        # AND it shows no version
        assert "Version: None\n" in out


class TestWriteGithubOutput:
    """Tests for write_github_output()."""

    def test_writes_uris(self, tmp_path: Path) -> None:
        """The URIs of the registered schemas go to the file, one on each line."""
        # GIVEN two registered schemas and one failed registration
        results = [
            JSONSchema(name="Biospecimen", organization_name="test.org"),
            None,
            JSONSchema(name="Patient", organization_name="test.org"),
        ]
        output_file = tmp_path / "github_output.txt"

        # WHEN I write the output
        write_github_output(str(output_file), results)

        # THEN the file has a uris heredoc with only the registered schemas
        expected = "uris<<EOF\ntest.org-Biospecimen\ntest.org-Patient\nEOF\n"
        assert output_file.read_text(encoding="utf-8") == expected

    def test_no_registered_schemas(self, tmp_path: Path) -> None:
        """No registered schemas gives an empty uris heredoc."""
        # GIVEN only failed registrations
        output_file = tmp_path / "github_output.txt"

        # WHEN I write the output
        write_github_output(str(output_file), [None, None])

        # THEN the file has an empty uris heredoc
        assert output_file.read_text(encoding="utf-8") == "uris<<EOF\n\nEOF\n"

    def test_appends_to_file(self, tmp_path: Path) -> None:
        """The output is added after the text that is in the file."""
        # GIVEN an output file with another output
        output_file = tmp_path / "github_output.txt"
        output_file.write_text("other=value\n", encoding="utf-8")
        results = [JSONSchema(name="Patient", organization_name="test.org")]

        # WHEN I write the output
        write_github_output(str(output_file), results)

        # THEN the other output is kept
        expected = "other=value\nuris<<EOF\ntest.org-Patient\nEOF\n"
        assert output_file.read_text(encoding="utf-8") == expected


class TestPrintSummary:
    """Tests for print_summary()."""

    def test_counts(self, capsys: pytest.CaptureFixture[str]) -> None:
        """The summary shows each count."""
        # GIVEN 3 files, 2 registered and 1 failed

        # WHEN I print the summary
        print_summary(3, 2, 1)

        # THEN the summary shows each count
        out = capsys.readouterr().out
        assert "Registration Summary\n" in out
        assert "Total Processed: 3\n" in out
        assert "Successful: 2\n" in out
        assert "Failed: 1\n" in out


class TestRegisterSchema:
    """
    Tests for register_schema(). No token is necessary, because the file
    fails before the call to Synapse.
    """

    @pytest.fixture(scope="function")
    def syn(self) -> Synapse:
        """A Synapse client that is not logged in."""
        return Synapse(skip_checks=True)

    def test_not_json(self, syn: Synapse, capsys: pytest.CaptureFixture[str]) -> None:
        """A file that is not JSON gives None and an error, not an exception."""
        # GIVEN a file that is not JSON
        json_file = DATA_DIR / "non_schema_dir" / "Patient.json"

        # WHEN I register the schema
        result = register_schema(syn, json_file, "test.org", "1.0.0")

        # THEN it gives no schema
        assert result is None
        # AND it prints the file name and the version
        captured = capsys.readouterr()
        assert "Processing: Patient.json\n" in captured.out
        assert "Schema Name: Patient\n" in captured.out
        assert "Version: 1.0.0\n" in captured.out
        # AND it prints a registration error with the file path
        assert f"::error:: {json_file}: Failed to register" in captured.err

    def test_file_does_not_exist(
        self, syn: Synapse, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A file that does not exist gives None and an error, not an exception."""
        # GIVEN a file that does not exist
        json_file = DATA_DIR / "schema_dir" / "not_a_real_file.json"

        # WHEN I register the schema
        result = register_schema(syn, json_file, "test.org", None)

        # THEN it gives no schema
        assert result is None
        # AND it prints no version
        captured = capsys.readouterr()
        assert "Version: None\n" in captured.out
        # AND it prints a registration error with the file path
        assert f"::error:: {json_file}: Failed to register" in captured.err
