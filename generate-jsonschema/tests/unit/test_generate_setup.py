"""Unit tests for the generate-jsonschema GitHub Action configuration.

These tests check that action.yml declares the inputs and outputs, and maps
each input to an environment variable. The CI action run does not find a lost
optional input, because an empty value uses the default.
Tests of main() are in test_generate_functions.py.
"""

from pathlib import Path

import action_yml_checks as checks


def test_action_yml_exists(action_file: Path) -> None:
    """Test that action.yml exists and is valid YAML."""
    # GIVEN the path of the action.yml file
    # WHEN I check the file
    # THEN it exists and is valid YAML with the top-level keys
    checks.check_action_yml_file(action_file)


def test_required_inputs_defined(action_config: dict) -> None:
    """Test that all required inputs are defined in action.yml."""
    # GIVEN the inputs in action.yml
    inputs = action_config["inputs"]

    # WHEN I get the list of required inputs
    required_inputs = ["data-model-source"]

    # THEN each required input is defined and is required
    checks.check_required_inputs(inputs, required_inputs)


def test_optional_inputs_have_defaults(action_config: dict) -> None:
    """Test that optional inputs have default values."""
    # GIVEN the inputs in action.yml
    inputs = action_config["inputs"]

    # WHEN I get the list of optional inputs
    optional_inputs = ["data-types", "data-model-labels", "output-directory"]

    # THEN each optional input is defined and has a default
    for input_name in optional_inputs:
        assert input_name in inputs, f"Optional input '{input_name}' should be defined"
        assert "default" in inputs[input_name], f"Input '{input_name}' has no default"


def test_outputs_defined(action_config: dict) -> None:
    """Test that all expected outputs are defined."""
    # GIVEN the outputs in action.yml
    outputs = action_config["outputs"]

    # WHEN I get the list of expected outputs
    expected_outputs = ["schemas", "schemas-json"]

    # THEN each output is defined and has a description
    checks.check_outputs_defined(outputs, expected_outputs)


def test_docker_configuration(action_config: dict) -> None:
    """Test that Docker configuration is correct."""
    # GIVEN the runs section of action.yml
    runs = action_config["runs"]

    # WHEN I get the env mapping
    env = runs.get("env", {})

    # THEN the action runs the Dockerfile
    checks.check_docker_runs(runs)

    # AND each input is mapped to an environment variable
    assert "DATA_MODEL_SOURCE" in env, "DATA_MODEL_SOURCE should be mapped"
    assert "DATA_TYPES" in env, "DATA_TYPES should be mapped"
    assert "DATA_MODEL_LABELS" in env, "DATA_MODEL_LABELS should be mapped"
    assert "OUTPUT_DIRECTORY" in env, "OUTPUT_DIRECTORY should be mapped"
