import asyncio
import json
import aiohttp
import pytest
import pytest_asyncio
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
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic.v1.typing")
warnings.filterwarnings("ignore", category=DeprecationWarning, module="ollama._types")
warnings.filterwarnings("ignore", category=pytest.PytestDeprecationWarning)
warnings.filterwarnings("ignore", message="Accessing the 'model_fields' attribute on the instance is deprecated")

console = Console()

@pytest.fixture
def persona():
    return "You are a helpful customer support assistant, always greet the user politely. Explain everything like you are speaking to a 3 year old. You may have to perform multi-stage tasks to complete the users requests."

@pytest.fixture
def llama_model():
    return ChatOllama(model="llama3.2:latest", temperature=0, top_p=1)

@pytest.fixture
def qwq_model():
    return ChatOllama(model="qwq:latest", temperature=0, top_p=1)

def convert_response(obj):
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
    now = datetime.now().strftime("%H:%M:%S")
    console.rule(f"[bold green]{now} - Query: {query}")
    console.print(f"[bold blue]Human Input:[/bold blue] {query}\n")

    messages = []
    if persona:
        messages.append({"role": "system", "content": persona})
    messages.append({"role": "user", "content": query})

    response = await agent.ainvoke({"messages": messages})
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
        tool_msgs = [msg for msg in safe_response.get("messages", []) if isinstance(msg, dict) and msg.get("role") == "tool"]
        if tool_msgs:
            console.print("\n[bold underline]Extracted Tool Calls from messages:[/bold underline]")
            print_tool_calls(tool_msgs)

    ai_outputs = safe_response.get("messages", [])
    console.print("\n[bold blue]AI Output:[/bold blue]")
    if isinstance(ai_outputs, list):
        for idx, msg in enumerate(ai_outputs, start=1):
            if isinstance(msg, dict):
                role = msg.get("role", "assistant")
                content = msg.get("content", "")
            else:
                role = "assistant"
                content = msg

            if "<think>" in content and "</think>" in content:
                think_content = content.split("<think>")[1].split("</think>")[0].strip()
                rest = content.replace(f"<think>{think_content}</think>", "").strip()

                if think_content:
                    console.print(Panel.fit(f"[italic dim]{think_content}[/]", title="🧠 Think", border_style="bright_black"))

                if rest:
                    rich_response = Text.from_markup(rest)
                    console.print(Panel.fit(rich_response, title=f"AI Message {idx}", border_style="bright_blue"))
            elif role == "user":
                console.print(Panel.fit(content, title=f"👤 User Message", border_style="blue"))
            elif role == "tool":
                console.print(Panel.fit(content, title=f"🛠️ Tool Output", border_style="magenta"))
            elif content.strip():
                console.print(Panel.fit(Text.from_markup(content), title=f"AI Message {idx}", border_style="bright_blue"))
    else:
        console.print(Panel(str(ai_outputs), title="AI Output", border_style="bright_blue", expand=False))

    return safe_response

# Tests

@pytest.mark.asyncio
async def test_get_tenant_status(qwq_model, persona):
    server_params = StdioServerParameters(command="python", args=["../mcp_tools/traction_api_tool.py"])
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
    server_params = StdioServerParameters(command="python", args=["../mcp_tools/traction_api_tool.py"])
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
    server_params = StdioServerParameters(command="python", args=["../mcp_tools/traction_api_tool.py"])
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
    server_params = StdioServerParameters(command="python", args=["../mcp_tools/traction_api_tool.py"])
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            agent = create_react_agent(qwq_model, tools)
            question = "I'd like to create a new NANDA scheme with a single binary field which will allow people to verify that they were at the hackathon. The scheme version is '1.0' and the exact attribute name that I want is 'hackathon_attendance'. \n"
            response = await process_query(query=question, agent=agent, persona=persona)
            assert isinstance(response, dict)
            assert "messages" in response
            assert len(response["messages"]) > 0

if __name__ == "__main__":
    from mcp.tools import start_tool_server
    start_tool_server()
