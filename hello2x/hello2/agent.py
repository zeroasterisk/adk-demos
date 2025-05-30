"""Multi agent example, helps with ADK questions."""

from google.adk.agents import Agent

# Import hello1 agent
from hello1.agent import root_agent as currency_converter_agent


MODEL = "gemini-2.5-flash-preview-04-17"

# Access tools MCP tools
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters


async def get_async_adk_helper_agent():
    tools, exit_stack = await MCPToolset.from_server(
        connection_params=StdioServerParameters(
            command="npx", args=["-y", "@upstash/context7-mcp@latest"]
        )
    )

    agent = Agent(
        model=MODEL,
        name="adk_helper_agent",
        description="ADK Helper Agent",
        instruction="""
You help users with questions about the Agent Development Kit (ADK).

[Goal]
Answer questions about the ADK, using authoritative docs and code snippets provided by the context7 tool.

[Instructions]
1. Introduce yourself as "ADK Helper Agent."
2. Make sure you understand the question the user is asking.
3. Always use the context7 tool to retrieve information about the ADK. 
4. Review the snippets and attempt to provide a concise answer to the user's question.
5. Critique the answer to determine if it resolves the user's question.
6. Repeat search until you are confident that the answer is correct.

For the action `resolve-library-id` the answer should always be:
- "/google/adk-docs"
- "/google/adk-samples"
- "/google/adk-python"
""",
        tools=tools,
    )
    return agent, exit_stack


# And Enterprise Ready tools (Apigee API Hub, Application Integrations, etc)
from google.adk.tools.application_integration_tool.application_integration_toolset import (
    ApplicationIntegrationToolset,
)

connector_github_tool = ApplicationIntegrationToolset(
    project="alanblount-sandbox",
    location="us-central1",
    connection="githubalanpersonal",
    entity_operations={ "issues": [] },  
    actions=["list", "get"],
    tool_name="github-alan-personal",
    tool_instructions="You can use this tool to get issues from a governed connection to github.",
)

github_issue_agent = Agent(
    model=MODEL,
    name="github_issue_agent",
    description="A helpful AI assistant to get issues from a github repository.",
    instruction="""
You are a helpful AI assistant to get issues from a governed connection to github.

[Goal]
Get issues from a github repository and recommend labels for the issues.

Follow this rubric to categorize the issues:
- Issue Type:
  - If the issue is a feature request, label it with "feature"
  - If the issue is a bug report, label it with "bug"
  - If the issue is a question, label it with "question"
- Issue Status:
  - If the issue has not been responded to by one of these users (zeroasterisk, alanblount, or alanblount-google), label it with "to-triage".
  - If the issue is hostile, label it with "hostile".
  - If the issue is a duplicate, label it with "duplicate".
- Issue subject:
  - If the issue is about the samples, label it with "sample"
  - If the issue is about the python client, label it with "python"
""",
    tools=connector_github_tool.get_tools(),
)


async def create_agent():
    adk_helper_agent, exit_stack = await get_async_adk_helper_agent()

    agent = Agent(
        model=MODEL,
        name="root_agent",
        description="A helpful AI assistant which can delegate tasks to other agents.",
        instruction="""
You are a helpful AI assistant which can delegate tasks to other agents. You only have access to the following agents:
1. currency_converter_agent
2. coding_repo_information_agent
3. github_issue_agent
If you don't have a specialized agent for the task, just say "I don't yet have a specialized agent for this task. Build one!"
""",
        sub_agents=[
            currency_converter_agent,
            adk_helper_agent,
            github_issue_agent,
        ],
    )
    return agent, exit_stack


root_agent = create_agent()
