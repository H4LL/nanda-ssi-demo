import asyncio
import json
import aiohttp
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama

# Initialize the ChatOllama model with deterministic settings.
model = ChatOllama(model="qwq:latest", temperature=0, top_p=1)

async def process_query(query: str, agent) -> list:
    """
    Processes a user query by sending it to the agent and returning the agent's responses.

    Parameters:
        query (str): The user query.
        agent: The reactive agent used to process queries.

    Returns:
        list: A list of response texts from the agent.
    """
    response = await agent.ainvoke({"messages": [{"role": "user", "content": query}]})
    responses = [message.text() for message in response.get("messages", [])]
    return responses

async def main():
    # Configure server parameters for the ACA‑Py query server.
    server_params = StdioServerParameters(
        command="python",
        args=["acapy_api_tool.py"]  # Path to your query server file.
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Load MCP tools from the ACA‑Py swagger spec.
            tools = await load_mcp_tools(session)
            # Create a reactive agent using the model and tools.
            agent = create_react_agent(model, tools)
            
            summary = []
            
            # Define the test queries.
            test_queries = [
                {
                    "description": "Send Message.",
                    "message": "Can you say hi to my connection Alice?"
                }
            ]
            
            # Process each test query using the agent.
            for query in test_queries:
                print("=" * 60)
                print(f"Query: {query['description']}")
                responses = await process_query(query["message"], agent)
                summary.append({"question": query["message"], "responses": responses})
    
    # Write the summary of questions and responses to a file.
    with open("summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("Summary written to summary.json")

if __name__ == "__main__":
    asyncio.run(main())