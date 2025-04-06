from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("BcovrinQueryTool")

@mcp.tool()
def query_bcovrin(query: str) -> str:
    """Queries the BCovrin test net with the provided query.
    
    This tool sends a GET request to the BCovrin test network URL with a query parameter
    and returns the raw response text. Adjust the request parameters as needed to match
    the test net's API specification.
    """
    url = "http://test.bcovrin.vonx.io/"
    try:
        response = requests.get(url, params={"query": query}, timeout=10)
        if response.status_code == 200:
            return response.text
        else:
            return f"Error: Received status code {response.status_code}"
    except Exception as e:
        return f"Exception occurred: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport="stdio")