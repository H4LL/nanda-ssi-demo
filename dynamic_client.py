import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama
from rich.console import Console
from rich.panel import Panel

console = Console()

# Initialize the ChatOllama model with deterministic settings.
model = ChatOllama(model="qwq:latest", temperature=0, top_p=1)

async def interactive_chat():
    # Configure MCP server parameters.
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_tools/traction_api_tool.py"]  # Adjust this path as necessary.
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Load the MCP tools.
            tools = await load_mcp_tools(session)
            # Create a reactive agent using the loaded tools.
            agent = create_react_agent(model, tools)
            # Initialize conversation history as an empty list.
            conversation_history = []
            
            console.print("[bold green]Interactive Chat Session. Type 'exit' to quit.[/bold green]")
            
            while True:
                # Read user input.
                user_message = input("You: ").strip()
                if user_message.lower() in ("exit", "quit"):
                    console.print("[bold red]Exiting chat...[/bold red]")
                    break
                
                # Append user's message to the conversation history.
                conversation_history.append(("user", user_message))
                
                # Invoke the agent with the full conversation history.
                response = await agent.ainvoke({"messages": conversation_history})
                ai_messages = response.get("messages", [])
                
                if ai_messages:
                    # Get the latest agent message.
                    latest_msg = ai_messages[-1]
                    # Convert to a string by accessing its 'content' attribute if available.
                    if not isinstance(latest_msg, str):
                        try:
                            latest_msg_str = latest_msg.content
                        except AttributeError:
                            latest_msg_str = str(latest_msg)
                    else:
                        latest_msg_str = latest_msg
                    
                    # Print the agent's response in a Rich panel.
                    console.print(Panel(latest_msg_str, title="Assistant", border_style="bright_blue"))
                    # Append the agent's response to the conversation history with an acceptable role.
                    conversation_history.append(("assistant", latest_msg_str))
                else:
                    console.print("[bold yellow]No response from agent.[/bold yellow]")

if __name__ == "__main__":
    asyncio.run(interactive_chat())