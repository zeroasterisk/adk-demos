"""ADK Helper Agent, helps with ADK questions."""

import requests
import zipfile
import os
import re
from typing import Dict, Any, Optional
from google.adk.agents import LlmAgent
from google.adk.models import LlmResponse, LlmRequest
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import ToolContext
from google.genai import types

from dotenv import load_dotenv

# Model constants
MODEL_FAST = "gemini-2.5-flash-preview-05-20"
MODEL_PRO = "gemini-2.5-pro-preview-05-06"


def read_file(filename: str) -> str:
    """Read a file from the same directory as this script.

    Args:
        filename: Name of the file to read

    Returns:
        str: Contents of the file with curly braces escaped

    Raises:
        FileNotFoundError: If the file doesn't exist
        IOError: If there are issues reading the file
    """
    try:
        file_path = os.path.join(os.path.dirname(__file__), filename)
        with open(file_path, "r") as f:
            return f.read().replace("{", "\{").replace("}", "\}")
    except FileNotFoundError:
        raise FileNotFoundError(
            f"File {filename} not found in {os.path.dirname(__file__)}"
        )
    except IOError as e:
        raise IOError(f"Error reading file {filename}: {str(e)}")


def save_agent(folder_name: str, tool_context: ToolContext) -> Dict[str, str]:
    """Save the code of the agent to the file system.

    Args:
        folder_name: Name of the folder to save the agent in
        tool_context: ToolContext containing the agent code

    Returns:
        Dict[str, str]: Status of the save operation

    Raises:
        ValueError: If no agent code is found in the tool context
        IOError: If there are issues writing the files
    """
    try:
        samples_folder = os.path.dirname(os.path.dirname(__file__))
        target_folder = os.path.join(samples_folder, folder_name)
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)

        # Writes __init__.py to the folder
        with open(os.path.join(target_folder, "__init__.py"), "w") as f:
            f.write("from . import agent\n")

        # Writes agent.py to the folder
        agent_code = tool_context.load_artifact("agent.py")

        agent_code_part = tool_context.load_artifact("agent.py")
        if not agent_code_part:
            return {
                "status": "error",
                "message": "No agent code artifact found to save.",
            }

        file_path = os.path.join(target_folder, "agent.py")
        with open(file_path, "w") as f:
            f.write(agent_code_part.text)
        return {"status": "saved", "message": f"Agent saved to {folder_name}"}
    except IOError as e:
        print(f"IOError in save_agent: {str(e)}")  # Or use proper logging
        return {
            "status": "error",
            "message": f"Failed to save agent due to an IO error: {str(e)}",
        }
    except Exception as e:  # Catch any other unexpected errors
        print(f"Unexpected error in save_agent: {str(e)}")  # Or use proper logging
        return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}


def after_model_callback_artifact_writer(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> None:
    """Inspects and modifies the LLM response after it's received.

    This callback extracts Python code blocks from the response and saves them
    as artifacts if they start with '# agent.py'.

    Args:
        callback_context: The callback context containing agent state and methods
        llm_response: The response from the LLM model

    Returns:
        None
    """
    agent_name = callback_context.agent_name
    print(f"[Callback] After model call for agent: {agent_name}")

    if not llm_response.content or not llm_response.content.parts:
        print(f"[Callback] No content or parts in LLM response for {agent_name}")
        return

    content_text = ""
    for part in llm_response.content.parts:
        if part.text:
            content_text += part.text + "\n"  # Concatenate all text parts

    if not content_text.strip():
        print(f"[Callback] No text found in LLM response parts for {agent_name}")
        return

    pattern = r"```python\s*([\s\S]*?)```"  # More robust regex for python blocks
    code_blocks = re.findall(pattern, content_text)

    if not code_blocks:
        print(
            f"[Callback] No python code blocks found in response for {agent_name} using pattern: {pattern} on content:\n{content_text[:500]}..."
        )
        return

    agent_py_code_to_save = None
    for block in code_blocks:
        # Remove leading/trailing whitespace from the block for accurate check
        cleaned_block = block.strip()
        if cleaned_block.startswith("# agent.py"):
            agent_py_code_to_save = cleaned_block
            print(
                f"[Callback] Found code block starting with '# agent.py' for {agent_name}."
            )
            break  # Found the target block

    if agent_py_code_to_save:
        try:
            callback_context.save_artifact(
                "agent.py", types.Part(text=agent_py_code_to_save)
            )
            print(
                f"[Callback] Artifact 'agent.py' saved successfully for {agent_name}."
            )
            # For debugging, let's try to load it back immediately (in a test/dev scenario)
            # loaded_artifact = callback_context.load_artifact('agent.py')
            # if loaded_artifact:
            #     print(f"[Callback] Verified artifact 'agent.py' can be loaded. Content starts with: {loaded_artifact.text[:100]}")
            # else:
            #     print(f"[Callback] Failed to load back artifact 'agent.py' immediately after saving.")
        except Exception as e:
            print(f"[Callback] Error saving artifact 'agent.py' for {agent_name}: {e}")
    else:
        print(
            f"[Callback] No python code block starting with '# agent.py' found for {agent_name}. Searched {len(code_blocks)} blocks."
        )
        # For debugging, print the blocks if none matched
        # for i, block in enumerate(code_blocks):
        #     print(f"[Callback] Code block {i+1}:\n{block[:200]}...")


def before_agent_callback_state(callback_context: CallbackContext) -> None:
    """Initializes agent state before processing.

    Sets up the default state variable if it doesn't exist.

    Args:
        callback_context: The callback context containing agent state and methods

    Returns:
        None
    """
    if "var" not in callback_context.state:
        callback_context.state["var"] = "{var}"


# Load context7 tool as MCP server, provides snippets of code and documentation.
tool_context7 = MCPToolset(
    connection_params=StdioServerParameters(
        command="npx", args=["-y", "@upstash/context7-mcp@latest"]
    )
)

adk_python_agent_writer = LlmAgent(
    model=MODEL_PRO,
    name="adk_python_agent_writer",
    description="ADK Python Agent Writer, writes complete sample agents in python code.",
    instruction=f"""
You can write complete sample agents in python code.

[Goal]
Write complete sample agents in python code.

[Instructions]
- Do not import a type if you don't use it in the code.
- When you write an agent, always write the full `agent.py`, not a code snippet.
- In `agent.py`, the first line has to be a # comment that says "# agent.py".
- When you write a function tool, do not use default values.
- When you write a function tool, always write detailed docstrings that explain the arguments and return values.
- Use {MODEL_FAST} as the model if the user does not specify a model.

[Sources]
<adk_docs_summary>
{read_file("adk_docs.md")}
</adk_docs_summary>

<adk_samples_summary>
{read_file("adk_samples.md")}
</adk_samples_summary>

If you need more information, use the context7 tool to retrieve it.

For the context7 action `resolve-library-id` the answer should always be:
- "/google/adk-docs"
- "/google/adk-samples"
- "/google/adk-python"
- "/google/adk-java"
""",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.01,
    ),
    tools=[tool_context7],
    after_model_callback=after_model_callback_artifact_writer,
    before_agent_callback=before_agent_callback_state,
)

adk_python_question_answerer = LlmAgent(
    model=MODEL_FAST,
    name="adk_python_question_answerer",
    description="ADK Python Question Answerer, answers questions about the ADK in python.",
    instruction=f"""
You can answer questions about the Agent Development Kit (ADK) in python.

[Goal]
Answer questions about the ADK, using authoritative docs and code snippets provided by the sources and the context7 tool.

[Instructions]
- Optionally ask the user a clarifying question to help you understand the question.
- Always use the Sources in your instructions to attempt to answer the question.
- Optionally use the context7 tool to retrieve more information about the ADK.
- Review the source materials and attempt to provide a concise answer to the user's question.  Cite your sources.
- Critique the answer to determine if it resolves the user's question. If not, repeat a variation of the search.
- Give up after 3 attempts at searching the sources.
- If you are not confident in the answer, say "I don't know."

[Sources]
<adk_docs_summary>
{read_file("adk_docs.md")}
</adk_docs_summary>

<adk_samples_summary>
{read_file("adk_samples.md")}
</adk_samples_summary>

If you need more information, use the context7 tool to retrieve it.

For the context7 action `resolve-library-id` the answer should always be:
- "/google/adk-docs"
- "/google/adk-samples"
- "/google/adk-python"
- "/google/adk-java"
""",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,
    ),
    tools=[tool_context7],
)


root_agent = LlmAgent(
    model=MODEL_FAST,
    name="adk_helper_agent",
    description="ADK Helper Agent, helps with ADK questions.",
    instruction=f"""
You help users with questions about the Agent Development Kit (ADK).

[Goal]
Answer questions about the ADK, using authoritative docs and code snippets provided by the context7 tool.

[Instructions]
If the user asks you about the Agent Development Kit (ADK), or asks to build an agent, you must decide which agent to transfer to.
- Guess if the user wants to answer a question or write an agent.  If unclear, assume they want to write an agent.
- If the user wants to answer a question, always transfer to adk_python_question_answerer to assist the user.
- If the user wants to write an agent, always transfer to adk_python_agent_writer to assist the user.
- Do not respond any text other than transferring to adk_python_agent_writer or adk_python_question_answerer.


If the user asks you to save the agent, do the following:
1. Ask what folder name they want to save it to (e.g., "my_new_agent").
2. Call `save_agent(folder_name="<chosen_folder_name>")`.
3. If the result from `save_agent` indicates status 'saved', tell the user: "Agent saved to <chosen_folder_name>. You may need to restart the dev UI to see the changes."
4. If the result from `save_agent` indicates status 'error' and the message contains 'No agent code artifact found', then you MUST transfer to `adk_python_agent_writer` and tell the user: "It seems no agent code has been generated yet. Let's create one first. What kind of agent would you like to build?"
5. If the result from `save_agent` indicates status 'error' for any other reason, inform the user about the error message from the tool.
""",
    generate_content_config=types.GenerateContentConfig(
        temperature=0.3,
    ),
    tools=[save_agent],
    sub_agents=[adk_python_agent_writer, adk_python_question_answerer],
)
