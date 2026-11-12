"""Unit tests for the generate-jsonschema GitHub Action setup.

These tests verify the action configuration and script setup without making
actual API calls to Synapse. Integration tests are handled by the underlying
synapseclient library.
"""

import sys
from pathlib import Path

import yaml

# Add src to path for importing the action script
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_action_yml_exists() -> None:
    """Test that action.yml exists and is valid YAML."""
    # GIVEN the path of the action.yml file
    action_file = Path(__file__).parent.parent / "action.yml"

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


def test_required_inputs_defined() -> None:
    """Test that all required inputs are defined in action.yml."""
    # GIVEN the action.yml file
    action_file = Path(__file__).parent.parent / "action.yml"

    # WHEN I load the action.yml file
    with open(action_file, encoding="utf-8") as f:
        action_config = yaml.safe_load(f)

    # THEN each required input is defined and is required
    inputs = action_config["inputs"]
    required_inputs = ["data-model-source"]
    for input_name in required_inputs:
        assert input_name in inputs, f"Required input '{input_name}' should be defined"
        assert inputs[input_name]["required"] is True, f"'{input_name}' not required"


def test_optional_inputs_have_defaults() -> None:
    """Test that optional inputs have default values."""
    # GIVEN the action.yml file
    action_file = Path(__file__).parent.parent / "action.yml"

    # WHEN I load the action.yml file
    with open(action_file, encoding="utf-8") as f:
        action_config = yaml.safe_load(f)

    # THEN each optional input is defined and has a default
    inputs = action_config["inputs"]
    optional_inputs = ["data-types", "data-model-labels", "output-directory"]
    for input_name in optional_inputs:
        assert input_name in inputs, f"Optional input '{input_name}' should be defined"
        assert "default" in inputs[input_name], f"Input '{input_name}' has no default"


def test_outputs_defined() -> None:
    """Test that all expected outputs are defined."""
    # GIVEN the action.yml file
    action_file = Path(__file__).parent.parent / "action.yml"

    # WHEN I load the action.yml file
    with open(action_file, encoding="utf-8") as f:
        action_config = yaml.safe_load(f)

    # THEN each output is defined and has a description
    outputs = action_config["outputs"]
    expected_outputs = ["schemas", "schemas-json"]
    for output_name in expected_outputs:
        assert output_name in outputs, f"Output '{output_name}' should be defined"
        assert "description" in outputs[output_name], f"'{output_name}' no description"


def test_docker_configuration() -> None:
    """Test that Docker configuration is correct."""
    # GIVEN the action.yml file
    action_file = Path(__file__).parent.parent / "action.yml"

    # WHEN I load the action.yml file
    with open(action_file, encoding="utf-8") as f:
        action_config = yaml.safe_load(f)

    # THEN the action runs the Dockerfile
    assert action_config["runs"]["using"] == "docker", "Action should use Docker"
    assert action_config["runs"]["image"] == "Dockerfile", "Should use Dockerfile"

    # AND each input is mapped to an environment variable
    env = action_config["runs"].get("env", {})
    assert "DATA_MODEL_SOURCE" in env, "DATA_MODEL_SOURCE should be mapped"
    assert "DATA_TYPES" in env, "DATA_TYPES should be mapped"
    assert "DATA_MODEL_LABELS" in env, "DATA_MODEL_LABELS should be mapped"
    assert "OUTPUT_DIRECTORY" in env, "OUTPUT_DIRECTORY should be mapped"


def test_dockerfile_exists() -> None:
    """Test that Dockerfile exists and has correct base image."""
    # GIVEN the path of the Dockerfile
    dockerfile = Path(__file__).parent.parent / "Dockerfile"

    # THEN the file exists
    assert dockerfile.exists(), "Dockerfile should exist"

    # WHEN I read the Dockerfile
    content = dockerfile.read_text()

    # THEN its ENTRYPOINT runs the action script
    assert "ENTRYPOINT" in content, "Dockerfile should define ENTRYPOINT"
    assert "generate_jsonschema_action.py" in content, "Should run the script"


def test_action_script_exists() -> None:
    """Test that the Python action script exists and is executable."""
    # GIVEN the path of the action script
    script_file = Path(__file__).parent.parent / "src" / "generate_jsonschema_action.py"

    # THEN the file exists
    assert script_file.exists(), "Action script should exist"

    # WHEN I read the action script
    content = script_file.read_text()

    # THEN it has the imports, main() and the __main__ block
    assert "from synapseclient import Synapse" in content, "Should import Synapse"
    assert "from synapseclient.extensions.curator import generate_jsonschema" in content
    assert "def main():" in content, "Script should have main() function"
    assert 'if __name__ == "__main__":' in content, "Script should have __main__ block"


def test_action_script_imports() -> None:
    """Test that the action script can be imported without errors."""
    # GIVEN the action script on sys.path
    # WHEN I import the action script
    # An ImportError must fail the test, because CI installs synapseclient
    import generate_jsonschema_action  # pylint: disable=import-outside-toplevel

    # THEN it has a main function
    assert hasattr(generate_jsonschema_action, "main"), "Script should have main"


def test_readme_exists() -> None:
    """Test that README exists and contains key information."""
    # GIVEN the path of the README.md file
    readme = Path(__file__).parent.parent / "README.md"

    # THEN the file exists
    assert readme.exists(), "README.md should exist"

    # WHEN I read the README.md file
    content = readme.read_text()

    # THEN it has the title and documents the inputs and outputs
    assert "# Generate JSON Schema Action" in content, "README should have title"
    assert "data-model-source" in content, "README should document data-model-source"
    assert "schemas" in content, "README should document schemas output"
    assert "schemas-json" in content, "README should document schemas-json output"
