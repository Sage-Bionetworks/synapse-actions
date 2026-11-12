"""Integration tests that run main() against the installed synapseclient."""

import sys
from pathlib import Path

import pytest

# Add src to path for importing the action script
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from generate_jsonschema_action import (  # noqa: E402 # pylint: disable=wrong-import-position
    main,
)

DATA_MODEL_FILE = "data_model.csv"
DATA_MODEL_PATH = Path(__file__).parent / DATA_MODEL_FILE
TOTAL_SCHEMAS_IN_TEST_MODEL = 3


@pytest.fixture(autouse=True)
def run_in_temp_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run tests in a temporary directory to clean up generated files."""
    monkeypatch.chdir(tmp_path)


def test_main_no_data_model_source(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that the main function needs DATA_MODEL_SOURCE and returns error when it's missing."""
    # GIVEN no DATA_MODEL_SOURCE
    monkeypatch.delenv("DATA_MODEL_SOURCE", raising=False)

    # WHEN I generate the schemas
    res = main()
    captured = capsys.readouterr()

    # THEN it fails with a DATA_MODEL_SOURCE is required error
    assert res == 1, "Main function should return 1 when DATA_MODEL_SOURCE is missing"
    assert "::error::DATA_MODEL_SOURCE is required" in captured.err


def test_main_with_invalid_data_type(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
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
    assert (
        "::error::Schema generation failed: 'InvalidType' is not a valid datatype in the data model"
        in captured.err
    )


def test_main_with_empty_data_type(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
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


def test_main_with_no_data_types(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that the main function works with no DATA_TYPES."""
    # GIVEN a valid data model
    # AND no DATA_TYPES
    monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))
    monkeypatch.delenv("DATA_TYPES", raising=False)

    # WHEN I generate the schemas
    res = main()
    captured = capsys.readouterr()

    # THEN a schema is generated for each of the 3 data types
    assert res == 0, "Main function should return 0 when DATA_MODEL_SOURCE is valid"
    assert "::notice::Successfully generated 3 schema(s)" in captured.out


def test_main_with_1_data_type(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
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


def test_main_with_2_data_types(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
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


def test_main_file_not_found(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
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


def test_main_invalid_labels(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that main fails when DATA_MODEL_LABELS is invalid."""
    # GIVEN a valid data model
    # AND DATA_MODEL_LABELS that is not valid
    monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))
    monkeypatch.setenv("DATA_MODEL_LABELS", "invalid_label")
    monkeypatch.delenv("DATA_TYPES", raising=False)

    # WHEN I generate the schemas
    res = main()
    captured = capsys.readouterr()

    # THEN it fails with an invalid DATA_MODEL_LABELS error
    assert res == 1
    assert "::error::Invalid DATA_MODEL_LABELS 'invalid_label'" in captured.err


def test_main_github_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that main writes to GITHUB_OUTPUT correctly."""
    # GIVEN a valid data model
    # AND a GITHUB_OUTPUT file
    output_file = tmp_path / "github_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))
    monkeypatch.delenv("DATA_TYPES", raising=False)

    # WHEN I generate the schemas
    res = main()

    # THEN GITHUB_OUTPUT has the schemas and schemas-json outputs
    assert res == 0
    assert output_file.exists()
    content = output_file.read_text()
    assert "schemas=schemas\n" in content
    assert "schemas-json<<EOF" in content


def test_main_github_output_custom_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that the schemas output is relative to the workspace."""
    # GIVEN a valid data model
    # AND a GITHUB_OUTPUT file
    # AND an OUTPUT_DIRECTORY in the workspace
    output_file = tmp_path / "github_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    monkeypatch.setenv("OUTPUT_DIRECTORY", "./out/schemas/")
    monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))
    monkeypatch.delenv("DATA_TYPES", raising=False)

    # WHEN I generate the schemas
    res = main()

    # THEN the schemas output is the path relative to the workspace
    assert res == 0
    content = output_file.read_text()
    assert "schemas=out/schemas\n" in content
    assert str(tmp_path) not in content.splitlines()[0]


def test_main_with_empty_output_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that an empty OUTPUT_DIRECTORY uses the default schemas directory."""
    # GIVEN a valid data model
    # AND an empty OUTPUT_DIRECTORY
    output_file = tmp_path / "github_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    monkeypatch.setenv("OUTPUT_DIRECTORY", "")
    monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))
    monkeypatch.delenv("DATA_TYPES", raising=False)

    # WHEN I generate the schemas
    res = main()

    # THEN all schemas are in the default schemas directory
    assert res == 0
    assert "schemas=schemas\n" in output_file.read_text()
    schema_count = len(list((tmp_path / "schemas").glob("*.json")))
    assert schema_count == TOTAL_SCHEMAS_IN_TEST_MODEL
    assert not list(tmp_path.glob("*.json")), "No schemas should be in the root"


def test_main_with_output_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tests main function using a custom output directory."""
    # GIVEN a valid data model
    # AND a custom OUTPUT_DIRECTORY
    output_dir = "output_dir"
    monkeypatch.setenv("OUTPUT_DIRECTORY", output_dir)
    monkeypatch.setenv("DATA_MODEL_SOURCE", str(DATA_MODEL_PATH))
    monkeypatch.delenv("DATA_TYPES", raising=False)

    # WHEN I generate the schemas
    res = main()

    # THEN all schemas are in the custom directory
    assert res == 0
    output_path = tmp_path / output_dir
    assert output_path.exists()
    assert output_path.is_dir()
    # Check if schemas were generated in the custom directory
    assert len(list(output_path.glob("*.json"))) == TOTAL_SCHEMAS_IN_TEST_MODEL
