# /Users/alanblount/Code/adk-demos/adk_helper/tests/test_agent.py
import sys
import os

# Add the parent directory of 'adk_helper' to sys.path
# This allows 'from adk_helper...' imports to work
# test_agent.py -> tests -> adk_helper -> adk-demos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import pytest
import os
import shutil
from unittest.mock import MagicMock
import uuid  # For generating session IDs

from google.adk.sessions import (
    Session,
    State,
)  # Keep State for type hinting if needed, but not for Session construction
from google.adk.tools import ToolContext
from google.genai import types as genai_types

# Adjust the import path according to your project structure
from adk_helper.adk_agent.agent import save_agent, after_model_callback_artifact_writer

# Assuming adk_helper is the root package or accessible in PYTHONPATH

# --- Fixtures ---


@pytest.fixture
def mock_tool_context(mocker):
    """Creates a mock ToolContext with a session."""
    session_id = str(uuid.uuid4())
    # Pass a plain dict for state, and provide a session id
    mock_session = Session(
        app_name="test_app", user_id="test_user", id=session_id, state={}
    )

    context = mocker.MagicMock(spec=ToolContext)
    context.session = mock_session

    # Simulate how artifacts might be stored in session state (e.g., under a specific key)
    # The actual ADK might handle this differently, this is a simplified mock.
    if not hasattr(mock_session, "_artifacts_storage"):
        mock_session._artifacts_storage = (
            {}
        )  # Use a different attribute to avoid collision with actual state

    def _save_artifact_impl(name: str, artifact: genai_types.Part):
        mock_session._artifacts_storage[name] = artifact

    def _load_artifact_impl(name: str) -> genai_types.Part | None:
        return mock_session._artifacts_storage.get(name)

    context.save_artifact = mocker.MagicMock(side_effect=_save_artifact_impl)
    context.load_artifact = mocker.MagicMock(side_effect=_load_artifact_impl)

    return context


@pytest.fixture
def mock_callback_context(mocker):
    """Creates a mock CallbackContext with a session."""
    session_id = str(uuid.uuid4())
    mock_session = Session(
        app_name="test_app", user_id="test_user", id=session_id, state={}
    )
    context = mocker.MagicMock()
    context.session = mock_session
    context.agent_name = "test_agent"

    if not hasattr(mock_session, "_artifacts_storage"):
        mock_session._artifacts_storage = {}

    def _save_artifact_impl(name: str, artifact: genai_types.Part):
        mock_session._artifacts_storage[name] = artifact

    context.save_artifact = mocker.MagicMock(side_effect=_save_artifact_impl)

    # Add load_artifact mock for consistency if any callback tries to load
    def _load_artifact_impl(name: str) -> genai_types.Part | None:
        return mock_session._artifacts_storage.get(name)

    context.load_artifact = mocker.MagicMock(side_effect=_load_artifact_impl)

    return context


@pytest.fixture(scope="function")
def test_output_dir():
    """Creates and cleans up a temporary directory for test outputs."""
    dir_name = "temp_test_agent_output"
    current_file_dir = os.path.dirname(__file__)
    project_root_for_test = os.path.dirname(current_file_dir)

    full_dir_path = os.path.join(project_root_for_test, dir_name)

    if os.path.exists(full_dir_path):
        shutil.rmtree(full_dir_path)
    os.makedirs(full_dir_path, exist_ok=True)

    yield full_dir_path

    shutil.rmtree(full_dir_path)


# --- Test Cases ---


def test_save_agent_artifact_exists(mock_tool_context, test_output_dir):
    """Tests save_agent when the agent.py artifact exists."""
    agent_code_content = "# agent.py\nprint('Hello Test')"
    # Use the mocked save_artifact on the context, which stores it in session._artifacts_storage
    mock_tool_context.save_artifact(
        "agent.py", genai_types.Part(text=agent_code_content)
    )

    relative_test_folder_name = os.path.basename(test_output_dir)

    result = save_agent(
        folder_name=relative_test_folder_name, tool_context=mock_tool_context
    )

    assert result["status"] == "saved"
    assert relative_test_folder_name in result["message"]

    expected_agent_file = os.path.join(test_output_dir, "agent.py")
    expected_init_file = os.path.join(test_output_dir, "__init__.py")

    assert os.path.exists(test_output_dir)
    assert os.path.isfile(expected_agent_file)
    assert os.path.isfile(expected_init_file)

    with open(expected_agent_file, "r") as f:
        assert f.read() == agent_code_content
    with open(expected_init_file, "r") as f:
        assert f.read() == "from . import agent\n"


def test_save_agent_artifact_missing(mock_tool_context, test_output_dir):
    """Tests save_agent when the agent.py artifact is missing."""
    # Ensure no "agent.py" artifact is present by clearing the mock storage
    mock_tool_context.session._artifacts_storage.clear()

    relative_test_folder_name = os.path.basename(test_output_dir)
    result = save_agent(
        folder_name=relative_test_folder_name, tool_context=mock_tool_context
    )

    assert result["status"] == "error"
    assert "No agent code artifact found" in result["message"]


def test_after_model_callback_artifact_writer_saves_agent_code(mock_callback_context):
    """Tests that the callback saves agent.py artifact correctly."""
    code_content = "# agent.py\nprint('Generated by callback')"
    llm_response_content = (
        f"Some preamble\n```python\n{code_content}\n```\nSome postamble"
    )

    mock_llm_response = MagicMock()
    mock_llm_response.content = genai_types.Content(
        parts=[genai_types.Part(text=llm_response_content)]
    )

    after_model_callback_artifact_writer(mock_callback_context, mock_llm_response)

    mock_callback_context.save_artifact.assert_called_once_with(
        "agent.py", genai_types.Part(text=code_content)
    )

    # Additionally, check if it's in the session's mock artifact storage
    saved_artifact = mock_callback_context.session._artifacts_storage.get("agent.py")
    assert saved_artifact is not None
    assert saved_artifact.text == code_content


def test_after_model_callback_artifact_writer_no_python_block(mock_callback_context):
    """Tests callback when no python block is in LLM response."""
    llm_response_content = "This is a response without any python code blocks."
    mock_llm_response = MagicMock()
    mock_llm_response.content = genai_types.Content(
        parts=[genai_types.Part(text=llm_response_content)]
    )

    after_model_callback_artifact_writer(mock_callback_context, mock_llm_response)
    mock_callback_context.save_artifact.assert_not_called()


def test_after_model_callback_artifact_writer_no_agent_comment(mock_callback_context):
    """Tests callback when python block is present but no '# agent.py' comment."""
    code_content = "print('Just some python code')"
    llm_response_content = f"```python\n{code_content}\n```"
    mock_llm_response = MagicMock()
    mock_llm_response.content = genai_types.Content(
        parts=[genai_types.Part(text=llm_response_content)]
    )

    after_model_callback_artifact_writer(mock_callback_context, mock_llm_response)
    mock_callback_context.save_artifact.assert_not_called()
