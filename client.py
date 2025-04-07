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
class ConversationContext:
    """
    A class to maintain conversation context.

    Attributes:
        history (list): List of conversation messages.
    """
    def __init__(self, system_prompt: str):
        self.history = [{"role": "system", "content": system_prompt}]

    def add_message(self, role: str, content: str):
        """
        Adds a message to the conversation history.

        Parameters:
            role (str): Role of the message sender ("system", "user", or "assistant").
            content (str): Content of the message.
        """
        self.history.append({"role": role, "content": content})

    def get_history(self) -> list:
        """
        Retrieves the current conversation history.

        Returns:
            list: A list of messages in the conversation history.
        """
        return self.history

async def execute_plan(plan: list, agent, context: ConversationContext) -> list:
    """
    Executes each step in the emergent plan using the agent.

    Each step in the plan should be a dict with:
      - 'tool': name of the tool to call
      - 'params': parameters for that tool call

    Parameters:
        plan (list): List of plan steps.
        agent: The reactive agent used to process queries.
        context (ConversationContext): The conversation context.

    Returns:
        list: Updated conversation history.
    """
    for step in plan:
        tool = step.get("tool")
        params = step.get("params", {})
        instruction = f"Please execute tool '{tool}' with parameters: {json.dumps(params)}."
        context.add_message("user", instruction)
        
        # Send instruction to the agent using the context's history.
        response = await agent.ainvoke({"messages": context.get_history()})
        for message in response.get("messages", []):
            resp_text = message.text()
            message.pretty_print()  # Debug output
            context.add_message("assistant", resp_text)
    return context.get_history()

async def process_query(query: str, agent, context: ConversationContext) -> list:
    """
    Processes a user query by appending it to the conversation context,
    sending it to the agent, and updating the context with the agent's responses.

    Parameters:
        query (str): The user query.
        agent: The reactive agent used to process queries.
        context (ConversationContext): The conversation context.

    Returns:
        list: A list of response texts from the agent.
    """
    context.add_message("user", query)
    response = await agent.ainvoke({"messages": context.get_history()})
    responses = []
    for message in response.get("messages", []):
        resp_text = message.text()
        message.pretty_print()  # Debug output
        context.add_message("assistant", resp_text)
        responses.append(resp_text)
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
            
            # Define the system context prompt.
            system_prompt = (
                "You are an expert assistant that understands ACA‑Py and can help manage connections, "
                "credentials, and proofs. Please provide concise, actionable responses and use the "
                "available MCP tools effectively. Remember to use connection identifiers in the API."
            )
            # Initialize conversation context with the system prompt.
            context = ConversationContext(system_prompt)
            
            summary = []
            
            # Define the test queries.
            test_queries = [
                # {
                #     "description": "Do I have any connections named Alice?",
                #     "message": "Do I have any connections named Alice?"
                # },
                {
                    "description": "Send Message.",
                    "message": "Can you say hi to my connection Alice?"
                }
            ]
            
            # Process each test query using the agent and context.
            for query in test_queries:
                print("=" * 60)
                print(f"Query: {query['description']}")
                responses = await process_query(query["message"], agent, context)
                summary.append({"question": query["message"], "responses": responses})
    
    # Write the summary of questions and responses to a file.
    with open("summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print("Summary written to summary.json")

if __name__ == "__main__":
    asyncio.run(main())