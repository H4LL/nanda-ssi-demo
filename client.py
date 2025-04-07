import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama

# Initialize the ChatOllama model (adjust model name/version as needed)
model = ChatOllama(model="llama3.2")

async def main():
    # Configure the server parameters to launch your query server.
    # Ensure that "bcovrin_query_server.py" is implemented to process ACA‑Py queries.
    server_params = StdioServerParameters(
        command="python",
        args=["bcovrin_query_server.py"]  # Path to your query server file.
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Load MCP tools that were generated based on the ACA‑Py swagger spec.
            tools = await load_mcp_tools(session)
            # Create a reactive agent that uses your language model (ChatOllama) and the loaded tools.
            agent = create_react_agent(model, tools)
            
            # Define a test query to retrieve the agent's public DID.
            test_queries = [
                {
                    "description": "Query Public DID",
                    "message": "Query public did"  # This instructs the agent to call GET /wallet/did/public.
                },
            ]
            
            # Loop through the test queries and process the responses.
            for query in test_queries:
                print(f"Executing: {query['description']}")
                msg = {"messages": query["message"]}
                response = await agent.ainvoke(msg)
                for message in response.get('messages', []):
                    message.pretty_print()
                print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())