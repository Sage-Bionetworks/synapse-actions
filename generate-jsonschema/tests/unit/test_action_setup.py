"""Unit tests for the generate-jsonschema GitHub Action configuration.

These tests check that action.yml declares the inputs and outputs, maps each
input to an environment variable. The CI
action run does not find a lost input, because an empty value uses the default.
Tests of main() are in test_main.py.
"""

from pathlib import Path

import pytest
import yaml


@pytest.fixture(scope="module", name="action_file")
def fixture_action_file() -> Path:
    """Return the path of the action.yml file."""
    return Path(__file__).parents[2] / "action.yml"


@pytest.fixture(scope="module", name="action_config")
def fixture_action_config(action_file: Path) -> dict:
    """Load and return the action.yml file as a dict."""
    with open(action_file, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_action_yml_exists(action_file: Path) -> None:
    """Test that action.yml exists and is valid YAML."""
    # GIVEN the path of the action.yml file
    # THEN the file exists
    assert action_file.exists(), "action.yml should exist"

    # WHEN I load the action.yml file
    with open(action_file, encoding="utf-8") as f:
        action_config = yaml.safe_load(f)

    # THEN it is valid YAML with the top-level keys
    assert action_config is not None, "action.yml should be valid YAML"
    assert "name" in action_config, "action.yml should have a name"
    assert "inputs" in action_config, "action.yml should define inputs"
    assert "outputs" in action_config, "action.yml should define outputs"
    assert "runs" in action_config, "action.yml should define runs configuration"


def test_required_inputs_defined(action_config: dict) -> None:
    """Test that all required inputs are defined in action.yml."""
    # GIVEN the inputs in action.yml
    inputs = action_config["inputs"]

    # WHEN I get the list of required inputs
    required_inputs = ["data-model-source"]

    # THEN each required input is defined and is required
    for input_name in required_inputs:
        assert input_name in inputs, f"Required input '{input_name}' should be defined"
        assert inputs[input_name]["required"] is True, f"'{input_name}' not required"


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
    for output_name in expected_outputs:
        assert output_name in outputs, f"Output '{output_name}' should be defined"
        assert "description" in outputs[output_name], f"'{output_name}' no description"


def test_docker_configuration(action_config: dict) -> None:
    """Test that Docker configuration is correct."""
    # GIVEN the runs section of action.yml
    runs = action_config["runs"]

    # WHEN I get the env mapping
    env = runs.get("env", {})

    # THEN the action runs the Dockerfile
    assert runs["using"] == "docker", "Action should use Docker"
    assert runs["image"] == "Dockerfile", "Should use Dockerfile"

    # AND each input is mapped to an environment variable
    assert "DATA_MODEL_SOURCE" in env, "DATA_MODEL_SOURCE should be mapped"
    assert "DATA_TYPES" in env, "DATA_TYPES should be mapped"
    assert "DATA_MODEL_LABELS" in env, "DATA_MODEL_LABELS should be mapped"
    assert "OUTPUT_DIRECTORY" in env, "OUTPUT_DIRECTORY should be mapped"
