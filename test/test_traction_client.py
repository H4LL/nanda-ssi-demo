import asyncio
import json
import aiohttp
import pytest
import pytest_asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent  # Using the reactive agent for now
from langchain_ollama import ChatOllama
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from datetime import datetime

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic.v1.typing")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="ollama._types")
warnings.filterwarnings("ignore", category=pytest.PytestDeprecationWarning)
warnings.filterwarnings("ignore", message="Accessing the 'model_fields' attribute on the instance is deprecated")

import pytest

# Set up a console for logging.
console = Console()

# -----------------------------------------------------------------------------
# FIXTURES
# -----------------------------------------------------------------------------

@pytest.fixture
def persona():
    """
    Returns a string representing the 'system message' or persona.
    We treat this as a high-level role or context for the agent.
    """
    return "You are a helpful customer support assistant, always greet the user politely."

@pytest.fixture
def llama_model():
    """
    Returns a ChatOllama model with deterministic parameters.
    """
    return ChatOllama(model="llama3.2:latest", temperature=0, top_p=1)

@pytest.fixture
def qwq_model():
    """
    Returns a ChatOllama model with deterministic parameters.
    """
    return ChatOllama(model="qwq:latest", temperature=0, top_p=1)

# -----------------------------------------------------------------------------
# UTILITY FUNCTIONS
# -----------------------------------------------------------------------------
def convert_response(obj):
    """Recursively convert non-JSON-serializable objects into strings."""
    if isinstance(obj, list):
        return [convert_response(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_response(v) for k, v in obj.items()}
    else:
        try:
            json.dumps(obj)
            return obj
        except TypeError:
            return obj.text() if hasattr(obj, "text") else str(obj)

def print_tool_calls(tool_calls):
    """
    Prints a table listing all tool calls.
    """
    table = Table(title="Tools Accessed")
    table.add_column("Step", style="cyan", no_wrap=True)
    table.add_column("Tool Name", style="magenta")
    table.add_column("Timestamp", style="green")
    table.add_column("Tool Output", style="yellow")
    for idx, call in enumerate(tool_calls, start=1):
        tool_name = str(call.get("tool_name", "N/A"))
        ts = str(call.get("timestamp", "N/A"))
        output = convert_response(call.get("tool_output", ""))
        table.add_row(f"Step {idx}", tool_name, ts, output)
    console.print(table)

def print_chain_graph(cag):
    """
    Prints a tree showing the chain-of-actions (the compute graph).
    """
    tree = Tree("Compute Graph (Chain-of-Actions)")
    for idx, step in enumerate(cag, start=1):
        tool_name = str(step.get("tool_name", "N/A"))
        ts = str(step.get("timestamp", "N/A"))
        node = tree.add(f"[cyan]Step {idx}[/cyan] - [magenta]{tool_name}[/magenta] @ [green]{ts}[/green]")
        tool_out = convert_response(step.get("tool_output", ""))
        if tool_out:
            node.add(f"[yellow]Output:[/yellow] {tool_out}")
    console.print(tree)

async def process_query(
    query: str,
    agent,
    persona: str = None
) -> dict:
    """
    Processes a user query using the agent. The 'persona' is optionally
    passed in as a separate system message. The 'query' is the user message.
    """
    now = datetime.now().strftime("%H:%M:%S")
    console.rule(f"[bold green]{now} - Query: {query}")
    console.print(f"[bold blue]Human Input:[/bold blue] {query}\n")

    # Construct the message list with an optional system message if persona is provided.
    messages = []
    if persona:
        messages.append({"role": "system", "content": persona})
    messages.append({"role": "user", "content": query})

    response = await agent.ainvoke({"messages": messages})
    safe_response = convert_response(response)

    # Print full raw response.
    console.print("\n[bold underline]Raw Response:[/bold underline]")
    console.print_json(data=safe_response)

    # Log MCP agent events if available.
    if "events" in safe_response:
        console.print("\n[bold underline]MCP Agent Events:[/bold underline]")
        for event in safe_response["events"]:
            console.print(f"[blue]{event}[/blue]")

    # Print the compute graph (chain-of-actions) if available.
    if "cag" in safe_response:
        console.print("\n[bold underline]Compute Graph (Chain-of-Actions):[/bold underline]")
        print_chain_graph(safe_response["cag"])

    # Print the tools accessed if available.
    if "tool_calls" in safe_response:
        console.print("\n[bold underline]Tools Accessed:[/bold underline]")
        print_tool_calls(safe_response["tool_calls"])
    else:
        tool_msgs = [
            msg for msg in safe_response.get("messages", [])
            if isinstance(msg, dict) and msg.get("role") == "tool"
        ]
        if tool_msgs:
            console.print("\n[bold underline]Extracted Tool Calls from messages:[/bold underline]")
            print_tool_calls(tool_msgs)

    # Print the AI output (or Tool Output if applicable)
    ai_outputs = safe_response.get("messages", [])
    console.print("\n[bold blue]AI Output:[/bold blue]")
    if isinstance(ai_outputs, list):
        for idx, msg in enumerate(ai_outputs, start=1):
            title = f"AI Message {idx}"
            if isinstance(msg, str):
                stripped = msg.strip()
                if stripped.startswith("{") and stripped.endswith("}"):
                    try:
                        json.loads(stripped)
                        title = f"Tool Output {idx}"
                    except json.JSONDecodeError:
                        pass
            panel = Panel(msg, title=title, border_style="bright_blue", expand=False)
            console.print(panel)
    else:
        console.print(Panel(str(ai_outputs), title="AI Output", border_style="bright_blue", expand=False))

    return safe_response

# -----------------------------------------------------------------------------
# TESTS
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_bearer_token(llama_model, persona):
    """
    Example test that uses a separate 'persona' system message and a 'query' user message.
    """
    server_params = StdioServerParameters(command="python", args=["../mcp_tools/traction_api_tool.py"])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Step 1: Initialize the session
            await session.initialize()
            assert session is not None

            # Step 2: Load tools
            tools = await load_mcp_tools(session)
            assert isinstance(tools, list)
            assert len(tools) > 0

            # Step 3: Create the agent
            agent = create_react_agent(llama_model, tools)
            assert agent is not None

            # Step 4: Provide persona as a system message, question as user
            question = (
                "Could you please get me a bearer token?\n"
                "My tenant ID is 8f719188-a40b-43f2-bb96-56e28ba1dc53\n"
                "My API key is fd34f6365cef4ae0942e9d847bd22e96."
            )
            response = await process_query(query=question, agent=agent, persona=persona)

            # Step 5: Basic assertions
            assert isinstance(response, dict)
            assert "messages" in response
            assert len(response["messages"]) > 0


@pytest.mark.asyncio
async def test_get_tenant_status(qwq_model, persona):
    """
    Another example test that uses the separate system persona and user question.
    """
    server_params = StdioServerParameters(command="python", args=["../mcp_tools/traction_api_tool.py"])

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            assert session is not None

            tools = await load_mcp_tools(session)
            assert isinstance(tools, list)
            assert len(tools) > 0

            agent = create_react_agent(qwq_model, tools)
            assert agent is not None

            question = (
                "Could you please get me a summary of details about my tenant? \n"
                "My tenant ID is 8f719188-a40b-43f2-bb96-56e28ba1dc53\n"
                "My API key is fd34f6365cef4ae0942e9d847bd22e96."
            )
            response = await process_query(query=question, agent=agent, persona=persona)

            assert isinstance(response, dict)
            assert "messages" in response
            assert len(response["messages"]) > 0


if __name__ == "__main__":
    # Start the MCP tool server if you run this test file directly.
    from mcp.tools import start_tool_server
    start_tool_server()