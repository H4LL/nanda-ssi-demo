import asyncio
import json
import aiohttp
from mcp.server.fastmcp import FastMCP

# Base URL for your ACA‑Py agent (adjust as needed)
ACAPY_BASE_URL = "http://localhost:8021"

# Create an MCP server instance
mcp = FastMCP("AcaPyMCPTools")

async def http_request(method: str, path: str, payload: dict = None) -> dict:
    """
    Helper function to call ACA‑Py endpoints.
    """
    url = ACAPY_BASE_URL.rstrip("/") + path
    async with aiohttp.ClientSession() as session:
        if method.lower() == "get":
            async with session.get(url, params=payload) as resp:
                return await resp.json()
        elif method.lower() == "post":
            async with session.post(url, json=payload) as resp:
                return await resp.json()
        elif method.lower() == "put":
            async with session.put(url, json=payload) as resp:
                return await resp.json()
        elif method.lower() == "delete":
            async with session.delete(url, json=payload) as resp:
                return await resp.json()
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

@mcp.tool()
async def query_connections() -> str:
    """
    Retrieves all connections from ACA‑Py.
    """
    result = await http_request("get", "/connections")
    return json.dumps(result, indent=2)

@mcp.tool()
async def create_invitation(alias: str = "") -> str:
    """
    Creates a new connection invitation.
    
    Optionally, an alias can be provided.
    """
    payload = {}
    if alias:
        payload["alias"] = alias
    result = await http_request("post", "/connections/create-invitation", payload)
    return json.dumps(result, indent=2)

@mcp.tool()
async def receive_invitation(invitation: str) -> str:
    """
    Receives an invitation.
    
    The invitation must be a JSON string representing the invitation object.
    """
    try:
        invitation_obj = json.loads(invitation)
    except Exception as e:
        return f"Invalid JSON for invitation: {e}"
    result = await http_request("post", "/connections/receive-invitation", invitation_obj)
    return json.dumps(result, indent=2)

@mcp.tool()
async def accept_invitation(conn_id: str) -> str:
    """
    Accepts an invitation for the given connection ID.
    """
    path = f"/connections/{conn_id}/accept-invitation"
    result = await http_request("post", path, {})
    return json.dumps(result, indent=2)

@mcp.tool()
async def accept_request(conn_id: str) -> str:
    """
    Accepts a connection request for the given connection ID.
    """
    path = f"/connections/{conn_id}/accept-request"
    result = await http_request("post", path, {})
    return json.dumps(result, indent=2)

@mcp.tool()
async def send_message(conn_id: str, content: str) -> str:
    """
    Sends a basic message over the connection with the specified ID.
    """
    path = f"/connections/{conn_id}/send-message"
    payload = {"content": content}
    result = await http_request("post", path, payload)
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_public_did() -> str:
    """
    Retrieves the public DID of the agent.
    """
    result = await http_request("get", "/wallet/did/public")
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_schemas() -> str:
    """
    Retrieves the schemas created by the agent.
    """
    result = await http_request("get", "/schemas/created")
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_credential_definitions() -> str:
    """
    Retrieves the credential definitions created by the agent.
    """
    result = await http_request("get", "/credential-definitions/created")
    return json.dumps(result, indent=2)

@mcp.tool()
async def issue_credential(credential_offer: str) -> str:
    """
    Issues a credential using a credential offer payload.
    
    The credential_offer parameter must be a JSON string representing the credential offer.
    """
    try:
        payload = json.loads(credential_offer)
    except Exception as e:
        return f"Invalid JSON for credential offer: {e}"
    result = await http_request("post", "/issue-credential-2.0/send", payload)
    return json.dumps(result, indent=2)

@mcp.tool()
async def store_credential(cred_ex_id: str, credential_id: str = "") -> str:
    """
    Stores a received credential in the wallet.
    
    Optionally, a credential_id can be provided.
    """
    path = f"/issue-credential-2.0/records/{cred_ex_id}/store"
    payload = {}
    if credential_id:
        payload["credential_id"] = credential_id
    result = await http_request("post", path, payload)
    return json.dumps(result, indent=2)

@mcp.tool()
async def send_proof_request(proof_request: str) -> str:
    """
    Sends a proof request.
    
    The proof_request parameter must be a JSON string representing the proof request payload.
    """
    try:
        payload = json.loads(proof_request)
    except Exception as e:
        return f"Invalid JSON for proof request: {e}"
    result = await http_request("post", "/present-proof-2.0/send-request", payload)
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_proof_record(pres_ex_id: str) -> str:
    """
    Retrieves a proof record by its presentation exchange ID.
    """
    path = f"/present-proof-2.0/records/{pres_ex_id}"
    result = await http_request("get", path)
    return json.dumps(result, indent=2)

if __name__ == '__main__':
    # Run the MCP server over stdio.
    mcp.run(transport="stdio")