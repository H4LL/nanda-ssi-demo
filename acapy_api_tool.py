import asyncio
import json
import aiohttp
from mcp.server.fastmcp import FastMCP

# Base URL for your ACA‑Py agent (adjust as needed)
ACAPY_BASE_URL = "http://localhost:8021"

# Create an enriched MCP server instance
mcp = FastMCP("AcaPyMCPToolsEnriched")

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

# === Status and Metrics Endpoints ===

@mcp.tool()
async def get_status() -> str:
    """
    Retrieves agent status information.
    [Reference: Hyperledger Aries Cloud Agent Python Swagger, OpenAPI Specification]
    """
    result = await http_request("get", "/status")
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_metrics() -> str:
    """
    Retrieves agent metrics.
    [Reference: aiohttp documentation; Hyperledger Aries Cloud Agent Python Swagger]
    """
    result = await http_request("get", "/metrics")
    return json.dumps(result, indent=2)

# === Wallet and DID Endpoints ===

@mcp.tool()
async def get_wallet_public_did() -> str:
    """
    Retrieves the agent's public DID from the wallet.
    [Reference: ACA‑Py Swagger, Python JSON module documentation]
    """
    result = await http_request("get", "/wallet/did/public")
    return json.dumps(result, indent=2)

# === Connection Endpoints ===

@mcp.tool()
async def query_connections() -> str:
    """
    Retrieves all connections from ACA-PY.
    [Reference: ACA‑Py Swagger]
    """
    result = await http_request("get", "/connections")
    return json.dumps(result, indent=2)


@mcp.tool()
async def send_basic_message(conn_id: str, content: str) -> str:
    """
    Sends a basic message over a connection.
    [Reference: ACA‑Py Swagger]
    """
    if not conn_id.strip():
        return "Error: Connection ID is required."
    if not content.strip():
        return "Error: Message content is required."
    path = f"/connections/{conn_id}/send-message"
    payload = {"content": content}
    result = await http_request("post", path, payload)
    return json.dumps(result, indent=2)


# === Credential Issuance Endpoints (v2.0) ===

@mcp.tool()
async def issue_credential_v2(credential_offer: str) -> str:
    """
    Issues a credential using ACA‑Py's issue-credential-2.0 API.
    The credential_offer must be a JSON string.
    [Reference: Aries RFC 0037 – Issue Credential Protocol; ACA‑Py Swagger]
    """
    try:
        payload = json.loads(credential_offer)
    except Exception as e:
        return f"Invalid JSON for credential offer: {e}"
    result = await http_request("post", "/issue-credential-2.0/send", payload)
    return json.dumps(result, indent=2)


@mcp.tool()
async def send_proof_request_v2(proof_request: str) -> str:
    """
    Sends a proof request using ACA‑Py's present-proof-2.0 API.
    The proof_request must be a JSON string.
    [Reference: Aries RFC 0037 – Present Proof Protocol; ACA‑Py Swagger]
    """
    try:
        payload = json.loads(proof_request)
    except Exception as e:
        return f"Invalid JSON for proof request: {e}"
    result = await http_request("post", "/present-proof-2.0/send-request", payload)
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_proof_record_v2(pres_ex_id: str) -> str:
    """
    Retrieves a proof record by its presentation exchange ID.
    [Reference: ACA‑Py Swagger; Aries RFC 0037]
    """
    path = f"/present-proof-2.0/records/{pres_ex_id}"
    result = await http_request("get", path)
    return json.dumps(result, indent=2)

# === Revocation and Ledger Endpoints ===

@mcp.tool()
async def revoke_credential(cred_ex_id: str, publish: bool = True) -> str:
    """
    Revokes a credential.
    Optionally, publish the revocation immediately.
    [Reference: ACA‑Py Swagger]
    """
    path = "/revocation/revoke"
    payload = {
        "cred_ex_id": cred_ex_id,
        "publish": publish
    }
    result = await http_request("post", path, payload)
    return json.dumps(result, indent=2)

@mcp.tool()
async def ledger_get_txn(txn_id: str) -> str:
    """
    Retrieves a ledger transaction by its transaction ID.
    [Reference: ACA‑Py Swagger; OpenAPI Specification]
    """
    path = f"/ledger/transactions/{txn_id}"
    result = await http_request("get", path)
    return json.dumps(result, indent=2)

@mcp.tool()
async def ledger_register_did(did_info: str) -> str:
    """
    Registers a DID on the ledger.
    The did_info parameter must be a JSON string with the required fields.
    [Reference: ACA‑Py Swagger; Hyperledger Aries documentation]
    """
    try:
        payload = json.loads(did_info)
    except Exception as e:
        return f"Invalid JSON for DID info: {e}"
    result = await http_request("post", "/ledger/register-nym", payload)
    return json.dumps(result, indent=2)

# === Additional Tools ===
# Tools such as dynamic credential issuance based on attributes or sending messages
# by connection alias can be added following the same pattern.
# (See the original code for examples of such helper functions.)

if __name__ == '__main__':
    # Run the MCP server over stdio.
    mcp.run(transport="stdio")