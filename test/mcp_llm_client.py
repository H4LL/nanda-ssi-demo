import asyncio
import json
import aiohttp
import pytest
import pytest_asyncio
import re  # For regex operations
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.text import Text
from datetime import datetime
import warnings

# Suppress specific deprecation warnings cite_python_warnings_doc, cite_pydantic_doc
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic.v1.typing")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="ollama._types")
warnings.filterwarnings("ignore", category=pytest.PytestDeprecationWarning)
warnings.filterwarnings("ignore", message="Accessing the 'model_fields' attribute on the instance is deprecated")

console = Console()

@pytest.fixture
def persona():
    """
    Provide a helpful customer support assistant persona.
    
    cite_pytest_fixtures_doc
    """
    return (
        "You are a helpful customer support assistant, always greet the user politely. "
        "Explain everything like you are speaking to a 3 year old. "
        "You may have to perform multi-stage tasks to complete the user's requests."
    )

@pytest.fixture
def llama_model():
    """
    Returns an instance of ChatOllama for the llama model.
    
    cite_langchain_ollama_doc
    """
    return ChatOllama(model="llama3.2:latest", temperature=0, top_p=1)

@pytest.fixture
def qwq_model():
    """
    Returns an instance of ChatOllama for the qwq model.
    
    cite_langchain_ollama_doc
    """
    return ChatOllama(model="qwq:latest", temperature=0, top_p=1)

def convert_response(obj):
    """
    Recursively convert an object into a JSON-serializable structure.
    If an item is not serializable, attempt to use its text() method or
    fall back to a string representation.
    
    cite_python_json_doc, cite_stackoverflow_json_serialization
    """
    if isinstance(obj, list):
        return [convert_response(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_response(v) for k, v in obj.items()}
    else:
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return obj.text() if hasattr(obj, "text") else str(obj)

def print_tool_calls(tool_calls):
    """
    Print a table detailing the tool calls using the Rich library.
    
    cite_rich_tables_doc
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
    Print the compute graph (chain-of-actions) in a tree format using Rich.
    
    cite_rich_tree_doc
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

async def process_query(query: str, agent, persona: str = None) -> dict:
    """
    Process the query by invoking the agent with proper messages and 
    display the raw response, events, compute graph, and AI messages.
    
    cite_asyncio_doc, cite_langchain_docs
    """
    now = datetime.now().strftime("%H:%M:%S")
    console.rule(f"[bold green]{now} - Query: {query}")
    console.print(f"[bold blue]Human Input:[/bold blue] {query}\n")

    messages = []
    if persona:
        messages.append({"role": "system", "content": persona})
    messages.append({"role": "user", "content": query})

    try:
        response = await agent.ainvoke({"messages": messages})
    except Exception as e:
        console.print(f"[red]Error invoking agent: {e}[/red]")
        return {}

    safe_response = convert_response(response)

    console.print("\n[bold underline]Raw Response:[/bold underline]")
    console.print_json(data=safe_response)

    if "events" in safe_response:
        console.print("\n[bold underline]MCP Agent Events:[/bold underline]")
        for event in safe_response["events"]:
            console.print(f"[blue]{event}[/blue]")

    if "cag" in safe_response:
        console.print("\n[bold underline]Compute Graph (Chain-of-Actions):[/bold underline]")
        print_chain_graph(safe_response["cag"])

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

    ai_outputs = safe_response.get("messages", [])
    console.print("\n[bold blue]AI Output:[/bold blue]")
    assistant_count = 0
    # Process each message in raw order.
    for msg in ai_outputs:
        # When message is a dict, extract its role and content.
        if isinstance(msg, dict):
            role = msg.get("role", "assistant")
            content = msg.get("content", "")
        else:
            content = msg.strip()
            # Filter out messages that exactly match the persona or the query or are empty.
            if not content or (persona and content == persona.strip()) or content == query.strip():
                continue
            role = "assistant"
        
        # Check if the plain string is valid JSON; if so reclassify as tool output.
        content_stripped = content.strip()
        if ((content_stripped.startswith("{") and content_stripped.endswith("}")) or
            (content_stripped.startswith("[") and content_stripped.endswith("]"))):
            try:
                json.loads(content_stripped)
                role = "tool"
            except Exception:
                pass

        # Extract and print any <think> blocks, then remove them from content.
        if content:
            think_blocks = re.findall(r"<think>(.*?)</think>", content, flags=re.DOTALL)
            if think_blocks:
                for think_block in think_blocks:
                    think_block = think_block.strip()
                    if think_block:
                        console.print(
                            Panel.fit(f"[italic dim]{think_block}[/]",
                                      title="🧠 Think", border_style="")
                        )
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

        # Now print the message using appropriate styling.
        if role == "tool":
            console.print(Panel.fit(content, title="🛠️ Tool Output", border_style="magenta"))
        elif content:
            assistant_count += 1
            console.print(Panel.fit(Text.from_markup(content),
                                      title=f"AI Message {assistant_count}", border_style="bright_blue"))

    return safe_response

# ----------------------------
# Asynchronous Tests using pytest
# ----------------------------

@pytest.mark.asyncio
async def test_get_tenant_status(qwq_model, persona):
    """
    Test to verify that a summary of tenant details can be retrieved.
    
    cite_pytest_asyncio_doc
    """
    server_params = StdioServerParameters(command="python", args=["../tools/traction_api.py"])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            agent = create_react_agent(qwq_model, tools)
            question = "Could you please get me a summary of details about my tenant? \n"
            response = await process_query(query=question, agent=agent, persona=persona)
            assert isinstance(response, dict)
            assert "messages" in response
            assert len(response["messages"]) > 0

@pytest.mark.asyncio
async def test_list_connections(qwq_model, persona):
    """
    Test to verify that active connections are listed.
    
    cite_pytest_asyncio_doc
    """
    server_params = StdioServerParameters(command="python", args=["../tools/traction_api.py"])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            agent = create_react_agent(qwq_model, tools)
            question = "Could you please list my active connections?\n"
            response = await process_query(query=question, agent=agent, persona=persona)
            assert isinstance(response, dict)
            assert "messages" in response
            assert len(response["messages"]) > 0

@pytest.mark.asyncio
async def test_oob_invitation(qwq_model, persona):
    """
    Test to verify the creation of an out-of-band SSI agent invitation.
    
    cite_pytest_asyncio_doc
    """
    server_params = StdioServerParameters(command="python", args=["../tools/traction_api.py"])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            agent = create_react_agent(qwq_model, tools)
            question = "Could you create an out of band SSI agent invitation for my friend Bob?\n"
            response = await process_query(query=question, agent=agent, persona=persona)
            assert isinstance(response, dict)
            assert "messages" in response
            assert len(response["messages"]) > 0

@pytest.mark.asyncio
async def test_scheme_creation(qwq_model, persona):
    """
    Test to verify the creation of a new NANDA scheme.
    
    cite_pytest_asyncio_doc
    """
    server_params = StdioServerParameters(command="python", args=["../tools/traction_api.py"])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            agent = create_react_agent(qwq_model, tools)
            question = (
                "I'd like to create a new NANDA scheme with a single binary field which will allow "
                "people to verify that they were at the hackathon. The scheme version is '1.0' and "
                "the exact attribute name that I want is 'hackathon_attendance'. If the scheme already exists then that's fine, mission accomplished. \n"
            )
            response = await process_query(query=question, agent=agent, persona=persona)
            assert isinstance(response, dict)
            assert "messages" in response
            assert len(response["messages"]) > 0

if __name__ == "__main__":
    from mcp.tools import start_tool_server
    start_tool_server()