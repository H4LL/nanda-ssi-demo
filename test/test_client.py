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
# Filter warnings from accessing 'model_fields'
warnings.filterwarnings("ignore", message="Accessing the 'model_fields' attribute on the instance is deprecated")

# Initialize the ChatOllama model with deterministic settings.
# (Change the model name as needed.)
model = ChatOllama(model="llama3.2:latest", temperature=0, top_p=1)

import pytest
# Set up the console for logging.
console = Console()

def convert_response(obj):
    """
    Recursively convert non-JSON-serializable objects (like HumanMessage) to strings.
    """
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

async def process_query(query: str, agent) -> dict:
    """
    Processes a user query using the agent. Logs the human input,
    prints out the raw response, any MCP agent events, the compute graph, 
    tool calls, and the final AI output.
    """
    now = datetime.now().strftime("%H:%M:%S")
    console.rule(f"[bold green]{now} - Query: {query}")
    console.print(f"[bold blue]Human Input:[/bold blue] {query}\n")
    
    response = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})
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
            # Check if the message appears to be JSON representing a tool output.
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

@pytest.mark.asyncio
async def test_query_agent_status(model=ChatOllama(model="llama3.2:latest", temperature=0, top_p=1)):
    server_params = StdioServerParameters(command="python", args=["../mcp_tools/acapy_api_tool.py"])
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Step 1: Assert the successful initialization of the session.
            await session.initialize()
            assert session is not None

            # Step 2: Assert that tools have loaded correctly and contain expected elements.
            tools = await load_mcp_tools(session)
            assert isinstance(tools, list)
            assert len(tools) > 0  # Assuming at least one tool should be loaded

            # Step 3: Assert the successful creation of the agent instance.
            agent = create_react_agent(model, tools)
            assert agent is not None

            # Step 4: Assert the response to the query contains the expected keys and structure.
            response = await process_query("Can you tell me some stats about my agent?", agent)
            assert isinstance(response, dict)
            assert "messages" in response
            assert len(response["messages"]) > 0

@pytest.mark.asyncio
async def test_query_agent_credentials(model=ChatOllama(model="llama3.2:latest", temperature=0, top_p=1), query: str = "Can you tell me who I'm connected to?"):
    server_params = StdioServerParameters(command="python", args=["../mcp_tools/acapy_api_tool.py"])
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Step 1: Assert the successful initialization of the session.
            await session.initialize()
            assert session is not None

            # Step 2: Assert that tools have loaded correctly and contain expected elements.
            tools = await load_mcp_tools(session)
            assert isinstance(tools, list)
            assert len(tools) > 0  # Assuming at least one tool should be loaded

            # Step 3: Assert the successful creation of the agent instance.
            agent = create_react_agent(model, tools)
            assert agent is not None

            # Step 4: Assert the response to the query contains the expected keys and structure.
            response = await process_query(query, agent)
            assert isinstance(response, dict)
            assert "messages" in response
            assert len(response["messages"]) > 0

@pytest.mark.asyncio
async def test_query_agent_wallet_credentials(model=ChatOllama(model="llama3.2:latest", temperature=0, top_p=1), query: str = "Do I have any credentials in my wallet?"):
    server_params = StdioServerParameters(command="python", args=["../mcp_tools/acapy_api_tool.py"])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Step 1: Assert the successful initialization of the session.
            await session.initialize()
            assert session is not None

            # Step 2: Assert that tools have loaded correctly and contain expected elements.
            tools = await load_mcp_tools(session)
            assert isinstance(tools, list)
            assert len(tools) > 0  # Assuming at least one tool should be loaded

            # Step 3: Assert the successful creation of the agent instance.
            agent = create_react_agent(model, tools)
            assert agent is not None

            # Step 4: Use the parameterized query to check for credentials in the wallet.
            response = await process_query(query, agent)
            assert isinstance(response, dict)
            assert "messages" in response
            assert len(response["messages"]) > 0


# @pytest.mark.asyncio
# async def test_query_agent_wallet_credentials(model=ChatOllama(model="deepscaler:latest", temperature=0, top_p=1), query: str = "Tell me all of the people I know and all of the credentials I own."):
#     server_params = StdioServerParameters(command="python", args=["../mcp_tools/acapy_api_tool.py"])
#     async with stdio_client(server_params) as (read, write):
#         async with ClientSession(read, write) as session:
#             # Step 1: Assert the successful initialization of the session.
#             await session.initialize()
#             assert session is not None

#             # Step 2: Assert that tools have loaded correctly and contain expected elements.
#             tools = await load_mcp_tools(session)
#             assert isinstance(tools, list)
#             assert len(tools) > 0  # Assuming at least one tool should be loaded

#             # Step 3: Assert the successful creation of the agent instance.
#             agent = create_react_agent(model, tools)
#             assert agent is not None

#             # Step 4: Use the parameterized query to check for credentials in the wallet.
#             response = await process_query(query, agent)
#             assert isinstance(response, dict)
#             assert "messages" in response
#             assert len(response["messages"]) > 0


# @pytest.mark.asyncio
# async def test_query_agent_wallet_credentials(model=ChatOllama(model="qwq:latest", temperature=0, top_p=1), query: str = "Can you create me an out of band connection request?"):
#     server_params = StdioServerParameters(command="python", args=["../mcp_tools/acapy_api_tool.py"])
#     async with stdio_client(server_params) as (read, write):
#         async with ClientSession(read, write) as session:
#             # Step 1: Assert the successful initialization of the session.
#             await session.initialize()
#             assert session is not None

#             # Step 2: Assert that tools have loaded correctly and contain expected elements.
#             tools = await load_mcp_tools(session)
#             assert isinstance(tools, list)
#             assert len(tools) > 0  # Assuming at least one tool should be loaded

#             # Step 3: Assert the successful creation of the agent instance.
#             agent = create_react_agent(model, tools)
#             assert agent is not None

#             # Step 4: Use the parameterized query to check for credentials in the wallet.
#             response = await process_query(query, agent)
#             assert isinstance(response, dict)
#             assert "messages" in response
#             assert len(response["messages"]) > 0


# if __name__ == "__main__":
#     async def run():
#         server_params = StdioServerParameters(
#             command="python",
#             args=["../mcp_tools/acapy_api_tool.py"]  # Ensure this path is correct.
#         )
#         async with stdio_client(server_params) as (read, write):
#             async with ClientSession(read, write) as session:
#                 await session.initialize()
#                 tools = await load_mcp_tools(session)
#                 agent = create_react_agent(model, tools)
#                 await process_query("Say hi to Alice for me.", agent)
#     asyncio.run(run())