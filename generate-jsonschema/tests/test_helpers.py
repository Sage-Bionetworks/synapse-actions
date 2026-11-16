"""Unit tests for the helper functions of the action script."""

import json
import os
import sys
from pathlib import Path

import pytest

# Add src to path for importing the action script
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from generate_jsonschema_action import (  # noqa: E402 # pylint: disable=wrong-import-position
    parse_data_types,
    print_header,
    print_summary,
    resolve_output_path,
    validate_data_model_labels,
    validate_data_model_source,
    write_github_output,
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

    @pytest.mark.parametrize("value", [None, ""])
    def test_not_set(self, value: str | None) -> None:
        """Test that an unset or empty DATA_TYPES value gives None (all types)."""
        # GIVEN an unset or empty DATA_TYPES value

        # WHEN I parse it
        result = parse_data_types(value)

        # THEN the result is None
        assert result is None, "Unset or empty value should give None"

    @pytest.mark.parametrize("value", [",", " , ,", "   "])
    def test_only_separators(self, value: str) -> None:
        """Test that a value with only whitespace and commas gives an empty list."""
        # GIVEN a DATA_TYPES value with only whitespace and commas

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


class TestResolveOutputPath:
    """Tests for resolve_output_path."""

    def test_relative(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that a relative OUTPUT_DIRECTORY gives a relative output path."""
        # GIVEN a relative output directory name in the working directory
        monkeypatch.chdir(tmp_path)
        output_dir = os.path.join(os.getcwd(), "schemas")

        # WHEN I resolve the output path
        result = resolve_output_path("schemas", output_dir)

        # THEN the result is relative to the working directory
        assert result == "schemas", "Relative input should give a relative path"

    def test_nested_relative(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that a nested relative OUTPUT_DIRECTORY keeps its subdirectories."""
        # GIVEN a nested relative output directory name
        monkeypatch.chdir(tmp_path)
        output_dir = os.path.join(os.getcwd(), "out", "schemas")

        # WHEN I resolve the output path
        result = resolve_output_path(os.path.join("out", "schemas"), output_dir)

        # THEN the result is the nested relative path
        assert result == os.path.join("out", "schemas")

    def test_absolute(self, tmp_path: Path) -> None:
        """Test that an absolute OUTPUT_DIRECTORY gives the absolute output path."""
        # GIVEN an absolute output directory name
        output_dir = str(tmp_path / "schemas")

        # WHEN I resolve the output path
        result = resolve_output_path(output_dir, output_dir)

        # THEN the result is the absolute path
        assert result == output_dir, "Absolute input should give the absolute path"


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
