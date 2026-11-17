"""Unit tests for the action functions."""

import json
import os
import sys
from pathlib import Path

import pytest

# Add src to path for importing the action script
sys.path.insert(0, str(Path(__file__).parents[2] / "src"))
from generate_jsonschema_action import (  # noqa: E402 # pylint: disable=wrong-import-position
    main,
    parse_data_types,
    print_header,
    print_summary,
    resolve_output_path,
    validate_data_model_labels,
    validate_data_model_source,
    validate_output_directory,
    write_github_output,
)

DATA_MODEL_FILE = "data_model.csv"
DATA_MODEL_PATH = Path(__file__).parent.parent / DATA_MODEL_FILE
TOTAL_SCHEMAS_IN_TEST_MODEL = 3
ENV_VARS = (
    "DATA_MODEL_SOURCE",
    "DATA_TYPES",
    "DATA_MODEL_LABELS",
    "OUTPUT_DIRECTORY",
    "GITHUB_OUTPUT",
)


class TestValidateDataModelSource:
    """Tests for validate_data_model_source."""

    @pytest.mark.parametrize("value", [None, ""])
    def test_not_set(
        self, value: str | None, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that an unset or empty source is not valid."""
        # GIVEN an unset or empty data model source

        # WHEN I validate it
        result = validate_data_model_source(value)
        captured = capsys.readouterr()

        # THEN it is not valid
        assert result is False, "Unset or empty source should not be valid"
        # AND an error goes to stderr
        assert "::error::DATA_MODEL_SOURCE is required" in captured.err

    @pytest.mark.parametrize(
        "value",
        ["http://example.com/model.csv", "https://example.com/model.jsonld"],
    )
    def test_url(self, value: str, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that a URL source is valid without a file-exists check."""
        # GIVEN a URL data model source

        # WHEN I validate it
        result = validate_data_model_source(value)
        captured = capsys.readouterr()

        # THEN it is valid
        assert result is True, "URL source should be valid"
        # AND there is no error
        assert captured.err == ""

    def test_existing_file(self, tmp_path: Path) -> None:
        """Test that a local file that exists is valid."""
        # GIVEN a local data model file that exists
        model_file = tmp_path / "model.csv"
        model_file.write_text("Attribute\n", encoding="utf-8")

        # WHEN I validate it
        result = validate_data_model_source(str(model_file))

        # THEN it is valid
        assert result is True, "Existing file should be valid"

    def test_missing_file(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that a local file that does not exist is not valid."""
        # GIVEN a local data model path that does not exist
        missing = str(tmp_path / "missing.csv")

        # WHEN I validate it
        result = validate_data_model_source(missing)
        captured = capsys.readouterr()

        # THEN it is not valid
        assert result is False, "Missing file should not be valid"
        # AND an error with the path goes to stderr
        assert f"::error::Data model file not found: {missing}" in captured.err


class TestParseDataTypes:
    """Tests for parse_data_types."""

    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_not_set(self, value: str | None) -> None:
        """Test that an unset, empty or whitespace DATA_TYPES value gives None."""
        # GIVEN an unset, empty or whitespace-only DATA_TYPES value

        # WHEN I parse it
        result = parse_data_types(value)

        # THEN the result is None
        assert result is None, "Unset or empty value should give None"

    @pytest.mark.parametrize("value", [",", " , ,"])
    def test_only_separators(self, value: str) -> None:
        """Test that a value with only whitespace and commas gives an empty list."""
        # GIVEN a DATA_TYPES value with commas and no data type names

        # WHEN I parse it
        result = parse_data_types(value)

        # THEN the result is an empty list
        assert result == [], "Only whitespace and commas should give []"

    def test_strips_values(self) -> None:
        """Test that the data types are stripped and empty items are removed."""
        # GIVEN a DATA_TYPES value with spaces and an empty item
        value = " Datatype1 ,,Datatype2 "

        # WHEN I parse it
        result = parse_data_types(value)

        # THEN the result has the stripped, non-empty data types
        assert result == ["Datatype1", "Datatype2"]


class TestValidateDataModelLabels:
    """Tests for validate_data_model_labels."""

    @pytest.mark.parametrize("value", ["class_label", "display_label"])
    def test_valid(self, value: str, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that class_label and display_label are valid."""
        # GIVEN a supported DATA_MODEL_LABELS value

        # WHEN I validate it
        result = validate_data_model_labels(value)
        captured = capsys.readouterr()

        # THEN it is valid
        assert result is True, "Supported label value should be valid"
        # AND there is no error
        assert captured.err == ""

    @pytest.mark.parametrize("value", ["invalid_label", "", "Class_Label"])
    def test_invalid(self, value: str, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that other values are not valid."""
        # GIVEN an unsupported DATA_MODEL_LABELS value

        # WHEN I validate it
        result = validate_data_model_labels(value)
        captured = capsys.readouterr()

        # THEN it is not valid
        assert result is False, "Unsupported label value should not be valid"
        # AND an error with the value goes to stderr
        assert f"::error::Invalid DATA_MODEL_LABELS '{value}'" in captured.err
        # AND the error gives the valid values
        assert "Use 'class_label' or 'display_label'" in captured.err


class TestValidateOutputDirectory:
    """Tests for validate_output_directory."""

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            ("schemas", "schemas"),
            ("./out/schemas/", "out/schemas"),
            ("out/../schemas", "schemas"),
            (".", ""),
        ],
    )
    def test_in_workspace(
        self,
        value: str,
        expected: str,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that a relative path in the workspace gives the resolved path."""
        # GIVEN a working directory
        monkeypatch.chdir(tmp_path)

        # WHEN I validate an output directory in the workspace
        result = validate_output_directory(value)

        # THEN the result is the resolved absolute path in the workspace
        assert result == str((tmp_path / expected).resolve())

    def test_absolute_in_workspace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that an absolute path in the workspace is valid."""
        # GIVEN a working directory
        monkeypatch.chdir(tmp_path)
        # AND an absolute output directory in the workspace
        value = str(tmp_path.resolve() / "schemas")

        # WHEN I validate the output directory
        result = validate_output_directory(value)

        # THEN the result is the same absolute path
        assert result == value

    @pytest.mark.parametrize("value", ["../schemas", "out/../../schemas", "/tmp/x"])
    def test_outside_workspace(
        self,
        value: str,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Test that a path outside the workspace gives an error."""
        # GIVEN a working directory
        monkeypatch.chdir(tmp_path)

        # WHEN I validate an output directory outside the workspace
        result = validate_output_directory(value)
        captured = capsys.readouterr()

        # THEN the result is None
        assert result is None
        # AND an error with the value goes to stderr
        assert f"::error::OUTPUT_DIRECTORY '{value}' is not in the workspace" in (
            captured.err
        )


class TestResolveOutputPath:
    """Tests for resolve_output_path."""

    def test_relative(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that the output path is relative to the working directory."""
        # GIVEN an output directory in the working directory
        monkeypatch.chdir(tmp_path)
        output_dir = str(tmp_path.resolve() / "schemas")

        # WHEN I resolve the output path
        result = resolve_output_path(output_dir)

        # THEN the result is relative to the working directory
        assert result == "schemas", "The output path should be relative"

    def test_nested_relative(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a nested output directory keeps its subdirectories."""
        # GIVEN a nested output directory in the working directory
        monkeypatch.chdir(tmp_path)
        output_dir = str(tmp_path.resolve() / "out" / "schemas")

        # WHEN I resolve the output path
        result = resolve_output_path(output_dir)

        # THEN the result is the nested relative path
        assert result == os.path.join("out", "schemas")


class TestPrintHeader:
    """Tests for print_header."""

    def test_prints_inputs(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that the header shows all the inputs on stdout."""
        # GIVEN a set of action inputs
        source = "model.csv"
        data_types = ["Datatype1", "Datatype2"]

        # WHEN I print the header
        print_header(source, data_types, "display_label", "/tmp/schemas")
        captured = capsys.readouterr()

        # THEN the title goes to stdout
        assert "JSON Schema Generation" in captured.out
        # AND each input goes to stdout
        assert "Data Model Source: model.csv" in captured.out
        assert "Data Types: ['Datatype1', 'Datatype2']" in captured.out
        assert "Data Model Labels: display_label" in captured.out
        assert "Output Directory: /tmp/schemas" in captured.out
        # AND nothing goes to stderr
        assert captured.err == ""

    def test_all_data_types(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that the header shows None when all data types are generated."""
        # GIVEN no data types (all types)

        # WHEN I print the header
        print_header("model.csv", None, "class_label", "/tmp/schemas")
        captured = capsys.readouterr()

        # THEN the data types show as None
        assert "Data Types: None" in captured.out


class TestWriteGithubOutput:
    """Tests for write_github_output."""

    def test_writes_outputs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that the schemas and schemas-json outputs are written."""
        # GIVEN a GITHUB_OUTPUT file
        output_file = tmp_path / "github_output"
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
        # AND a list of schemas
        schemas = [{"title": "Datatype1"}, {"title": "Datatype2"}]

        # WHEN I write the outputs
        write_github_output("schemas", schemas)

        # THEN the file has the schemas path and the schemas-json heredoc
        expected = f"schemas=schemas\nschemas-json<<EOF\n{json.dumps(schemas)}\nEOF\n"
        assert output_file.read_text(encoding="utf-8") == expected

    def test_appends_to_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that the outputs are added after the existing file content."""
        # GIVEN a GITHUB_OUTPUT file with existing content
        output_file = tmp_path / "github_output"
        output_file.write_text("other=value\n", encoding="utf-8")
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

        # WHEN I write the outputs
        write_github_output("schemas", [])

        # THEN the existing content is kept
        content = output_file.read_text(encoding="utf-8")
        assert content.startswith("other=value\nschemas=schemas\n")
        # AND the empty schema list is written as JSON
        assert "schemas-json<<EOF\n[]\nEOF\n" in content

    @pytest.mark.parametrize("value", [None, ""])
    def test_not_set(
        self,
        value: str | None,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that nothing is written if GITHUB_OUTPUT is not set or empty."""
        # GIVEN an unset or empty GITHUB_OUTPUT
        if value is None:
            monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        else:
            monkeypatch.setenv("GITHUB_OUTPUT", value)
        monkeypatch.chdir(tmp_path)

        # WHEN I write the outputs
        write_github_output("schemas", [{"title": "Datatype1"}])

        # THEN no file is created
        assert not any(tmp_path.iterdir()), "No output file should be created"


class TestPrintSummary:
    """Tests for print_summary."""

    def test_lists_file_names(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that the summary gives the count and the file names."""
        # GIVEN the paths of two generated schema files
        file_paths = ["/tmp/schemas/Datatype1.json", "/tmp/schemas/Datatype2.json"]

        # WHEN I print the summary
        print_summary(file_paths)
        captured = capsys.readouterr()

        # THEN a notice with the count goes to stdout
        assert "::notice::Successfully generated 2 schema(s)" in captured.out
        # AND each file name (without the directory) goes to stdout
        assert "  - Datatype1.json\n" in captured.out
        assert "  - Datatype2.json\n" in captured.out
        assert "/tmp/schemas" not in captured.out

    def test_no_files(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that the summary gives a count of 0 for no files."""
        # GIVEN no generated schema files

        # WHEN I print the summary
        print_summary([])
        captured = capsys.readouterr()

        # THEN the notice has a count of 0 and no file names
        expected = "::notice::Successfully generated 0 schema(s)\n"
        assert captured.out == expected


class TestMain:
    """Tests that run main()."""

    @pytest.fixture(autouse=True)
    def run_in_temp_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Run tests in a temporary directory with no action env vars set.

        The CI runner sets GITHUB_OUTPUT, so remove it. Then main() does not
        write to the output file of the CI step.
        """
        monkeypatch.chdir(tmp_path)
        for name in ENV_VARS:
            monkeypatch.delenv(name, raising=False)

    def test_no_data_model_source(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that main returns an error when DATA_MODEL_SOURCE is missing."""
        # GIVEN no DATA_MODEL_SOURCE

        # WHEN I generate the schemas
        res = main()
        captured = capsys.readouterr()

        # THEN it fails with a DATA_MODEL_SOURCE is required error
        assert res == 1, "Main should return 1 when DATA_MODEL_SOURCE is missing"
        assert "::error::DATA_MODEL_SOURCE is required" in captured.err

    def test_with_invalid_data_type(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that the main function returns error when DATA_TYPES are invalid."""
        # GIVEN a valid data model
        # AND a data type that is not in the data model
        monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))
        monkeypatch.setenv("DATA_TYPES", "InvalidType")

        # WHEN I generate the schemas
        res = main()
        captured = capsys.readouterr()

        # THEN it fails with a data type not valid error
        assert res == 1, "Main function should return 1 when DATA_TYPES are invalid"
        expected = (
            "::error::Schema generation failed: "
            "'InvalidType' is not a valid datatype in the data model"
        )
        assert expected in captured.err

    def test_with_empty_data_type(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that the main function works with empty DATA_TYPES."""
        # GIVEN a valid data model
        # AND DATA_TYPES that has only a space
        monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))
        monkeypatch.setenv("DATA_TYPES", " ")

        # WHEN I generate the schemas
        res = main()
        captured = capsys.readouterr()

        # THEN a schema is generated for each of the 3 data types
        assert res == 0, "Main function should return 0 when DATA_TYPES is empty"
        assert "::notice::Successfully generated 3 schema(s)" in captured.out

    @pytest.mark.parametrize("value", [",", " , ,"])
    def test_with_only_commas_data_types(
        self,
        value: str,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that main fails when DATA_TYPES has commas and no names."""
        # GIVEN a valid data model
        # AND DATA_TYPES that has commas and no data type names
        monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))
        monkeypatch.setenv("DATA_TYPES", value)

        # WHEN I generate the schemas
        res = main()
        captured = capsys.readouterr()

        # THEN it fails with a no valid data type names error
        assert res == 1, "Main should return 1 when DATA_TYPES has no names"
        expected = f"::error::DATA_TYPES has no valid data type names: '{value}'"
        assert expected in captured.err
        # AND no schemas are generated
        assert not Path("schemas").exists(), "No output directory should be made"

    def test_with_no_data_types(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that the main function works with no DATA_TYPES."""
        # GIVEN a valid data model
        # AND no DATA_TYPES
        monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))

        # WHEN I generate the schemas
        res = main()
        captured = capsys.readouterr()

        # THEN a schema is generated for each of the 3 data types
        assert res == 0, "Main function should return 0 when DATA_MODEL_SOURCE is valid"
        assert "::notice::Successfully generated 3 schema(s)" in captured.out

    def test_with_1_data_type(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that the main function works with valid DATA_TYPES."""
        # GIVEN a valid data model
        # AND one data type
        monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))
        monkeypatch.setenv("DATA_TYPES", "Datatype1")

        # WHEN I generate the schemas
        res = main()
        captured = capsys.readouterr()

        # THEN one schema is generated
        assert res == 0, "Main function should return 0 when DATA_MODEL_SOURCE is valid"
        assert "::notice::Successfully generated 1 schema(s)" in captured.out

    def test_with_2_data_types(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that the main function works with valid DATA_TYPES."""
        # GIVEN a valid data model
        # AND two data types
        monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))
        monkeypatch.setenv("DATA_TYPES", "Datatype1,Datatype2")

        # WHEN I generate the schemas
        res = main()
        captured = capsys.readouterr()

        # THEN two schemas are generated
        assert res == 0, "Main function should return 0 when DATA_MODEL_SOURCE is valid"
        assert "::notice::Successfully generated 2 schema(s)" in captured.out

    def test_file_not_found(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that main returns error when local data model file does not exist."""
        # GIVEN a DATA_MODEL_SOURCE file that does not exist
        monkeypatch.setenv("DATA_MODEL_SOURCE", "non_existent_file.csv")

        # WHEN I generate the schemas
        res = main()
        captured = capsys.readouterr()

        # THEN it fails with a data model file not found error
        assert res == 1, "Main should return 1 when file not found"
        assert "::error::Data model file not found" in captured.err

    def test_invalid_labels(
        self, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that main fails when DATA_MODEL_LABELS is invalid."""
        # GIVEN a valid data model
        # AND DATA_MODEL_LABELS that is not valid
        monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))
        monkeypatch.setenv("DATA_MODEL_LABELS", "invalid_label")

        # WHEN I generate the schemas
        res = main()
        captured = capsys.readouterr()

        # THEN it fails with an invalid DATA_MODEL_LABELS error
        assert res == 1
        assert "::error::Invalid DATA_MODEL_LABELS 'invalid_label'" in captured.err

    def test_github_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that main writes to GITHUB_OUTPUT correctly."""
        # GIVEN a valid data model
        # AND a GITHUB_OUTPUT file
        output_file = tmp_path / "github_output.txt"
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
        monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))

        # WHEN I generate the schemas
        res = main()

        # THEN GITHUB_OUTPUT has the schemas and schemas-json outputs
        assert res == 0
        assert output_file.exists()
        content = output_file.read_text()
        assert "schemas=schemas\n" in content
        assert "schemas-json<<EOF" in content

    def test_github_output_custom_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that the schemas output is relative to the workspace."""
        # GIVEN a valid data model
        # AND a GITHUB_OUTPUT file
        # AND an OUTPUT_DIRECTORY in the workspace
        output_file = tmp_path / "github_output.txt"
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
        monkeypatch.setenv("OUTPUT_DIRECTORY", "./out/schemas/")
        monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))

        # WHEN I generate the schemas
        res = main()

        # THEN the schemas output is the path relative to the workspace
        assert res == 0
        content = output_file.read_text()
        assert "schemas=out/schemas\n" in content

    def test_with_empty_output_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that an empty OUTPUT_DIRECTORY uses the default schemas directory."""
        # GIVEN a valid data model
        # AND an empty OUTPUT_DIRECTORY
        output_file = tmp_path / "github_output.txt"
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
        monkeypatch.setenv("OUTPUT_DIRECTORY", "")
        monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))

        # WHEN I generate the schemas
        res = main()

        # THEN all schemas are in the default schemas directory
        assert res == 0
        assert "schemas=schemas\n" in output_file.read_text()
        schema_count = len(list((tmp_path / "schemas").glob("*.json")))
        assert schema_count == TOTAL_SCHEMAS_IN_TEST_MODEL
        assert not list(tmp_path.glob("*.json")), "No schemas should be in the root"

    @pytest.mark.parametrize("value", ["../schemas", "/tmp/schemas"])
    def test_output_directory_outside_workspace(
        self,
        value: str,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Test that main fails when OUTPUT_DIRECTORY is outside the workspace."""
        # GIVEN a valid data model
        # AND a GITHUB_OUTPUT file
        # AND an OUTPUT_DIRECTORY outside the workspace
        output_file = tmp_path / "github_output.txt"
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
        monkeypatch.setenv("OUTPUT_DIRECTORY", value)
        monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))

        # WHEN I generate the schemas
        res = main()
        captured = capsys.readouterr()

        # THEN it fails with an output directory error
        assert res == 1
        assert f"::error::OUTPUT_DIRECTORY '{value}' is not in the workspace" in (
            captured.err
        )
        # AND no outputs are written
        assert not output_file.exists()

    def test_github_output_absolute_in_workspace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that an absolute OUTPUT_DIRECTORY gives a relative schemas output."""
        # GIVEN a valid data model
        # AND a GITHUB_OUTPUT file
        # AND an absolute OUTPUT_DIRECTORY in the workspace
        output_file = tmp_path / "github_output.txt"
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
        monkeypatch.setenv("OUTPUT_DIRECTORY", str(tmp_path.resolve() / "schemas"))
        monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))

        # WHEN I generate the schemas
        res = main()

        # THEN the schemas output is the path relative to the workspace
        assert res == 0
        assert "schemas=schemas\n" in output_file.read_text()

    def test_with_output_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Tests main function using a custom output directory."""
        # GIVEN a valid data model
        # AND a custom OUTPUT_DIRECTORY
        output_dir = "output_dir"
        monkeypatch.setenv("OUTPUT_DIRECTORY", output_dir)
        monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))

        # WHEN I generate the schemas
        res = main()

        # THEN all schemas are in the custom directory
        assert res == 0
        output_path = tmp_path / output_dir
        assert output_path.exists()
        assert output_path.is_dir()
        # AND the custom directory has all the schemas
        assert len(list(output_path.glob("*.json"))) == TOTAL_SCHEMAS_IN_TEST_MODEL
