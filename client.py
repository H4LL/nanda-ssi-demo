import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_ollama import ChatOllama

# Initialize the ChatOllama model (adjust model name/version as needed)
model = ChatOllama(model="llama3.2")

async def main():
    # Configure the server parameters to launch your query server.
    server_params = StdioServerParameters(
        command="python",
        args=["acapy_api_tool.py"]  # Path to your query server file.
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            # Load MCP tools generated from the ACA‑Py swagger spec.
            tools = await load_mcp_tools(session)
            # Create a reactive agent with the model and tools.
            agent = create_react_agent(model, tools)
            
            # Structured conversation history (for context) and summary for clean output.
            conversation_history = []
            summary = []  # each item will hold only the current question and its responses
            
            # Define a list of test queries.
            test_queries = [
                {"description": "Query Public DID", "message": "What is my public DID?"},
                {"description": "List Connections", "message": "How many connections do I have?"},
                {"description": "Query Connection for Alice", "message": "Am I currently connected to someone named Alice?"},
                {"description": "Send Message to Alice", "message": "Could you say hi to Alice for me?"}
            ]
            
            # Process each query.
            for query in test_queries:
                # Create a turn summary for the current query.
                current_turn = {
                    "question": query["message"],
                    "responses": []
                }
                # Append the user's query to the conversation history.
                conversation_history.append({"role": "user", "content": query["message"]})
                # Build the payload.
                msg = {"messages": conversation_history}
                response = await agent.ainvoke(msg)
                # Process each assistant response.
                for message in response.get('messages', []):
                    resp_text = message.text()
                    message.pretty_print()  # prints the current response for debugging
                    conversation_history.append({"role": "assistant", "content": resp_text})
                    current_turn["responses"].append(resp_text)
                # Add the current turn to the summary.
                summary.append(current_turn)
                print("=" * 60)
    
    # Write the clean summary to a file.
    with open("summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("Summary written to summary.json")

if __name__ == "__main__":
    asyncio.run(main())