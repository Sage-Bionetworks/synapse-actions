"""Unit tests for the pure helper functions of the action script."""

import os
import sys
from pathlib import Path

import pytest

# Add src to path for importing the action script
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from generate_jsonschema_action import (  # noqa: E402 # pylint: disable=wrong-import-position
    parse_data_types,
    resolve_output_path,
)


@pytest.mark.parametrize("value", [None, ""])
def test_parse_data_types_not_set(value: str | None) -> None:
    """Test that an unset or empty DATA_TYPES value gives None (all types)."""
    # GIVEN an unset or empty DATA_TYPES value

    # WHEN I parse it
    result = parse_data_types(value)

    # THEN the result is None
    assert result is None, "Unset or empty value should give None"


@pytest.mark.parametrize("value", [",", " , ,", "   "])
def test_parse_data_types_only_separators(value: str) -> None:
    """Test that a value with only whitespace and commas gives an empty list."""
    # GIVEN a DATA_TYPES value with only whitespace and commas

    # WHEN I parse it
    result = parse_data_types(value)

    # THEN the result is an empty list
    assert result == [], "Only whitespace and commas should give []"


def test_parse_data_types_strips_values() -> None:
    """Test that the data types are stripped and empty items are removed."""
    # GIVEN a DATA_TYPES value with spaces and an empty item
    value = " Datatype1 ,,Datatype2 "

    # WHEN I parse it
    result = parse_data_types(value)

    # THEN the result has the stripped, non-empty data types
    assert result == ["Datatype1", "Datatype2"]


def test_resolve_output_path_relative(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that a relative OUTPUT_DIRECTORY gives a relative output path."""
    # GIVEN a relative output directory name in the working directory
    monkeypatch.chdir(tmp_path)
    output_dir = os.path.join(os.getcwd(), "schemas")

    # WHEN I resolve the output path
    result = resolve_output_path("schemas", output_dir)

    # THEN the result is relative to the working directory
    assert result == "schemas", "Relative input should give a relative path"


def test_resolve_output_path_absolute(tmp_path: Path) -> None:
    """Test that an absolute OUTPUT_DIRECTORY gives the absolute output path."""
    # GIVEN an absolute output directory name
    output_dir = str(tmp_path / "schemas")

    # WHEN I resolve the output path
    result = resolve_output_path(output_dir, output_dir)

    # THEN the result is the absolute path
    assert result == output_dir, "Absolute input should give the absolute path"
