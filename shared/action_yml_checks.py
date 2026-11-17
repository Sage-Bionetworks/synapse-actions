"""Shared fixtures and checks of the action.yml file for the action tests.

The pytest.ini file of each action loads this module as a pytest plugin, so
the fixtures are available in all tests of the action. The setup test file of
each action (test_<action>_setup.py) imports the checks. The lists of inputs,
outputs and environment variables stay in each test file.
"""

from pathlib import Path

import pytest
import yaml

TOP_LEVEL_KEYS = ["name", "inputs", "outputs", "runs"]


def load_action_config(action_file: Path) -> dict:
    """Load the action.yml file and return it as a dict.

    Arguments:
        action_file: The path of the action.yml file.

    Returns:
        The content of the action.yml file.
    """
    with open(action_file, encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module", name="action_file")
def fixture_action_file(request: pytest.FixtureRequest) -> Path:
    """Return the path of the action.yml file of the action under test.

    The test file is in <action>/tests/<dir>/, so action.yml is two
    directories above the directory of the test file.
    """
    return request.path.parents[2] / "action.yml"


@pytest.fixture(scope="module", name="action_config")
def fixture_action_config(action_file: Path) -> dict:
    """Load and return the action.yml file as a dict."""
    return load_action_config(action_file)


def check_action_yml_file(action_file: Path) -> None:
    """Check that action.yml exists, is valid YAML and has the top-level keys.

    Arguments:
        action_file: The path of the action.yml file.
    """
    assert action_file.exists(), "action.yml should exist"
    action_config = load_action_config(action_file)
    assert action_config is not None, "action.yml should be valid YAML"
    for key in TOP_LEVEL_KEYS:
        assert key in action_config, f"action.yml should have '{key}'"


def check_required_inputs(inputs: dict, required_inputs: list[str]) -> None:
    """Check that each required input is defined and is required.

    Arguments:
        inputs: The inputs section of action.yml.
        required_inputs: The names of the inputs that must be required.
    """
    for input_name in required_inputs:
        assert input_name in inputs, f"Required input '{input_name}' should be defined"
        assert inputs[input_name]["required"] is True, f"'{input_name}' not required"


def check_outputs_defined(outputs: dict, expected_outputs: list[str]) -> None:
    """Check that each expected output is defined and has a description.

    Arguments:
        outputs: The outputs section of action.yml.
        expected_outputs: The names of the outputs that must be defined.
    """
    for output_name in expected_outputs:
        assert output_name in outputs, f"Output '{output_name}' should be defined"
        assert "description" in outputs[output_name], f"'{output_name}' no description"


def check_docker_runs(runs: dict) -> None:
    """Check that the action runs the Dockerfile of the action directory.

    Arguments:
        runs: The runs section of action.yml.
    """
    assert runs["using"] == "docker", "Action should use Docker"
    assert runs["image"] == "Dockerfile", "Should use Dockerfile"
