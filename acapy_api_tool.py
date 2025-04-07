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
    # Validate that conn_id and content are non-empty strings.
    if not isinstance(conn_id, str) or not conn_id.strip():
        return "Error: A valid connection ID must be provided."
    if not isinstance(content, str) or not content.strip():
        return "Error: Message content must be a valid string."
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

@mcp.tool()
async def issue_dynamic_credential(credential_attributes) -> str:
    """
    Dynamically issues a credential using the provided credential attributes.
    
    The credential_attributes parameter can be provided as a JSON string or as a Python list of attribute objects.
    Example (as list):
      [{"name": "name", "value": "Alice"}, {"name": "degree", "value": "Bachelor of Arts"}]
    
    This tool retrieves:
      - The agent's public DID (as issuer_did)
      - The first active connection's connection_id
      - The first credential definition from get_credential_definitions
      - (Optionally, a schema_id; here we use a placeholder which can be replaced with dynamic lookup)
    
    It then constructs the credential offer payload and issues the credential.
    """
    # If input is a string, try parsing it as JSON.
    if isinstance(credential_attributes, str):
        try:
            attributes = json.loads(credential_attributes)
        except Exception as e:
            return f"Invalid JSON for credential attributes: {e}"
    elif isinstance(credential_attributes, list):
        attributes = credential_attributes
    else:
        return "Invalid input type: credential_attributes should be a JSON string or a list."
    
    # Retrieve public DID
    public_did_resp = await http_request("get", "/wallet/did/public")
    issuer_did = public_did_resp.get("result", {}).get("did", "")
    if not issuer_did:
        return "Error: Could not retrieve public DID."
    
    # Retrieve connections and select the first active connection
    connections_resp = await http_request("get", "/connections")
    connections = connections_resp.get("results", [])
    active_connections = [conn for conn in connections if conn.get("state") == "active"]
    if not active_connections:
        return "Error: No active connections found."
    connection_id = active_connections[0].get("connection_id")
    
    # Retrieve credential definitions and select the first one
    cred_defs_resp = await http_request("get", "/credential-definitions/created")
    cred_defs = cred_defs_resp.get("credential_definition_ids", [])
    if not cred_defs:
        return "Error: No credential definitions found."
    cred_def_id = cred_defs[0]
    
    # Optionally, retrieve a schema ID if available (using a placeholder here)
    schema_id = "PLACEHOLDER_SCHEMA_ID"  # Replace with dynamic lookup if needed
    
    # Construct the credential offer payload
    credential_offer_payload = {
        "connection_id": connection_id,
        "issuer_did": issuer_did,
        "schema_id": schema_id,
        "cred_def_id": cred_def_id,
        "credential_preview": {
            "@type": "https://didcomm.org/issue-credential/2.0/credential-preview",
            "attributes": attributes
        },
        "auto_issue": True
    }
    
    # Issue the credential
    issue_resp = await http_request("post", "/issue-credential-2.0/send", credential_offer_payload)
    return json.dumps(issue_resp, indent=2)

# New tool: Query connection by alias
@mcp.tool()
async def query_connection_by_alias(alias: str) -> str:
    """
    Retrieves connection details for connections where 'their_label' matches the provided alias (case-insensitive).
    """
    connections_resp = await http_request("get", "/connections")
    connections = connections_resp.get("results", [])
    matches = [conn for conn in connections if conn.get("their_label", "").lower() == alias.lower()]
    if not matches:
        return json.dumps({"error": f"No connections found with alias '{alias}'"}, indent=2)
    return json.dumps(matches, indent=2)

# New tool: Send message by alias
@mcp.tool()
async def send_message_by_alias(alias: str, content: str) -> str:
    """
    Finds all connections whose 'their_label' matches the provided alias and sends the given message to each.
    
    Returns a summary of results.
    """
    connections_resp = await http_request("get", "/connections")
    connections = connections_resp.get("results", [])
    matches = [conn for conn in connections if conn.get("their_label", "").lower() == alias.lower()]
    if not matches:
        return json.dumps({"error": f"No connections found with alias '{alias}'"}, indent=2)
    
    results = []
    for conn in matches:
        conn_id = conn.get("connection_id")
        if not conn_id:
            results.append({"error": "Missing connection ID", "connection": conn})
            continue
        # Use our send_message tool: note that we call http_request directly to avoid revalidation.
        message_payload = {"content": content}
        send_resp = await http_request("post", f"/connections/{conn_id}/send-message", message_payload)
        results.append({"connection_id": conn_id, "result": send_resp})
    return json.dumps(results, indent=2)

if __name__ == '__main__':
    # Run the MCP server over stdio.
    mcp.run(transport="stdio")