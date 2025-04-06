import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama

# Initialize a ChatOllama model available via Ollama
model = ChatOllama(model="llama3.2")

async def main():
    server_params = StdioServerParameters(
        command="python",
        args=["bcovrin_query_server.py"],  # Ensure this path points to your server file
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            agent = create_react_agent(model, tools)
            # Instruct the agent to use the bcovrin query tool.
            msg = {"messages": "Query the bcovrin test net for the current ledger status"}
            res = await agent.ainvoke(msg)
            for m in res['messages']:
                m.pretty_print()

if __name__ == "__main__":
    asyncio.run(main())