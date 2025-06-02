"""ADK Helper Agent, helps with ADK questions."""

from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
import requests
import zipfile
import os

MODEL = "gemini-2.5-flash-preview-04-17"



async def get_async_adk_helper_agent():

    # Download the llms.txt file from the url.
    url = "https://raw.githubusercontent.com/google/adk-docs/refs/heads/main/llms.txt"
    response = requests.get(url)
    with open("llms.txt", "w") as file:
        file.write(response.text)
    # Load the llms.txt file.
    with open("llms.txt", "r") as file:
        context_window_sources_text = file.read()

    # # (optionally) Download the whole adk-docs repo.
    # url = "https://github.com/google/adk-docs/archive/refs/heads/main.zip"
    # response = requests.get(url)
    # with open("adk-docs.zip", "wb") as file:
    #     file.write(response.content)
    # with zipfile.ZipFile("adk-docs.zip", "r") as zip_ref:
    #     zip_ref.extractall("adk-docs")
    # # Use code2prompt to convert the adk-docs repo to a large markdown file.
    # # brew install code2prompt
    # print("code2prompt --output-file adk-docs.md --include '*.py,*.md' adk-docs")
    # os.system("code2prompt --output-file adk-docs.md --include '*.py,*.md' adk-docs")
    # with open("adk-docs.md", "r") as file:
    #     context_window_sources_text += file.read()

    # # Load context7 tool as MCP server, provides snippets of code and documentation.
    # tools, exit_stack = await MCPToolset.from_server(
    #     connection_params=StdioServerParameters(
    #         command="npx", args=["-y", "@upstash/context7-mcp@latest"]
    #     )
    # )

    agent = Agent(
        model=MODEL,
        name="adk_helper_agent",
        description="ADK Helper Agent, helps with ADK questions.",
        instruction="""
You help users with questions about the Agent Development Kit (ADK).

[Goal]
Answer questions about the ADK, using authoritative docs and code snippets provided by the context7 tool.

[Instructions]
1. Introduce yourself as "ADK Helper Agent."
2. Make sure you understand the question the user is asking.
3. Always use the context7 tool and context window sources to retrieve information about the ADK. 
4. Review the snippets and attempt to provide a concise answer to the user's question.  Cite your sources.
5. Critique the answer to determine if it resolves the user's question. If not, repeat the search.
6. Repeat search until you are confident that the answer is correct.
7. If you are not confident in the answer, say "I don't know."

<context_window_sources>
{context_window_sources_text}
</context_window_sources>

If you need more information, use the context7 tool to retrieve it.

For the context7 action `resolve-library-id` the answer should always be:
- "/google/adk-docs"
- "/google/adk-samples"
- "/google/adk-python"
- "/google/adk-java"
""",
        tools=tools,
    )
    return agent, exit_stack



async def create_agent():
    adk_helper_agent, exit_stack = await get_async_adk_helper_agent()

    # NOTE you could have other agents here, and ADK Helper Agent could be one of them.

    return adk_helper_agent, exit_stack


root_agent = create_agent()
