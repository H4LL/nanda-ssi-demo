import asyncio
import json
import aiohttp
from mcp.server.fastmcp import FastMCP
import logging

# Base URL for your ACA‑Py agent (adjust as needed)
TRACTION_BASE_URL = "http://localhost:8032"

# Configure a logger for this module.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    # Add a stream handler if none exists.
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s:%(name)s: %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


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
    [Reference: ACA‑Py OpenAPI Specification]
    """
    logger.info("get_status called")
    # Assume http_request is defined elsewhere in your code.
    result = await http_request("get", "/status")
    # logger.info("http_request returned: %s", result)
    output = json.dumps(result, indent=2)
    # logger.info("get_status output: %s", output)
    return output

@mcp.tool()
async def get_credential_definitions_created() -> str:
    """
    Retrieves all credential definitions that have been created by the agent.
    [Reference: ACA‑Py Admin API /credential-definitions/created]
    """
    result = await http_request("get", "/credential-definitions/created")
    return json.dumps(result, indent=2)

# === Wallet and DID Endpoints ===

@mcp.tool()
async def get_wallet_public_did() -> str:
    """
    Retrieves the agent's public DID from the wallet.
    [Reference: ACA‑Py OpenAPI Specification]
    """
    result = await http_request("get", "/wallet/did/public")
    return json.dumps(result, indent=2)

@mcp.tool()
async def get_credentials() -> str:
    """
    Retrieves all credential records stored in the agent's wallet.
    [Reference: ACA‑Py OpenAPI Specification]
    """
    result = await http_request("get", "/credentials")
    return json.dumps(result, indent=2)

# === Connection Endpoints ===


@mcp.tool()
async def query_connections() -> str:
    """
    Retrieves all connections from ACA‑Py.
    [Reference: ACA‑Py OpenAPI Specification]
    """
    result = await http_request("get", "/connections")
    return json.dumps(result, indent=2)

@mcp.tool()
async def send_basic_message(conn_id: str, content: str) -> str:
    """
    Sends a basic message over a connection.
    [Reference: ACA‑Py OpenAPI Specification]
    """
    if not conn_id.strip():
        return "Error: Connection ID is required."
    if not content.strip():
        return "Error: Message content is required."
    path = f"/connections/{conn_id}/send-message"
    payload = {"content": content}
    result = await http_request("post", path, payload)
    return json.dumps(result, indent=2)

# === Connection Endpoints for Establishing a Connection ===


@mcp.tool()
async def create_oob_invitation(payload: str) -> str:
    """
    Creates an Out-of-Band (OOB) invitation using ACA‑Py.
    Endpoint: POST /out-of-band/create-invitation
    The `payload` must be a JSON string conforming to the OOB spec, including optional attachments.
    [Reference: ACA‑Py OpenAPI Specification]
    """
    try:
        parsed_payload = json.loads(payload)
    except Exception as e:
        return f"Invalid JSON payload: {e}"

    url = ACAPY_BASE_URL.rstrip("/") + "/out-of-band/create-invitation"
    headers = {"Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, json=parsed_payload, headers=headers) as resp:
                if resp.status == 405:
                    return "Error: HTTP 405 Method Not Allowed. Please verify that the endpoint expects a POST request and that the ACA-Py instance is running with admin API enabled."
                return json.dumps(await resp.json(), indent=2)
        except Exception as e:
            return f"Request failed: {e}"

# === Credential Issuance Endpoints (v2.0) ===

@mcp.tool()
# --- Credential Issuance Endpoints ---

# Faber (Issuer) sends a credential offer
@mcp.tool()
async def send_credential_offer(payload: str) -> str:
    """
    Sends a credential offer using the issue-credential-2.0 API.
    Endpoint: POST /issue-credential-2.0/send-offer
    Expects a complete JSON payload (as a string) prepared externally.
    [Reference: OpenAPIDemo.md – Issuing a Credential]
    """
    try:
        parsed_payload = json.loads(payload)
    except Exception as e:
        return f"Invalid JSON payload: {e}"
    result = await http_request("post", "/issue-credential-2.0/send-offer", parsed_payload)
    return json.dumps(result, indent=2)

# Alice (Holder) sends a credential request based on a received offer
@mcp.tool()
async def send_credential_request(cred_ex_id: str, payload: str = "{}") -> str:
    """
    Sends a credential request.
    Endpoint: POST /issue-credential-2.0/records/{cred_ex_id}/send-request
    The payload can be an empty JSON string ("{}") or contain additional parameters.
    [Reference: OpenAPIDemo.md – Issuing a Credential]
    """
    path = f"/issue-credential-2.0/records/{cred_ex_id}/send-request"
    try:
        parsed_payload = json.loads(payload)
    except Exception as e:
        return f"Invalid JSON payload: {e}"
    result = await http_request("post", path, parsed_payload)
    return json.dumps(result, indent=2)

# Faber (Issuer) issues the credential after receiving the request
@mcp.tool()
async def issue_credential(cred_ex_id: str, payload: str = "{}") -> str:
    """
    Issues the credential.
    Endpoint: POST /issue-credential-2.0/records/{cred_ex_id}/issue
    The payload can be an empty JSON string ("{}") if no extra data is needed.
    [Reference: OpenAPIDemo.md – Issuing a Credential]
    """
    path = f"/issue-credential-2.0/records/{cred_ex_id}/issue"
    try:
        parsed_payload = json.loads(payload)
    except Exception as e:
        return f"Invalid JSON payload: {e}"
    result = await http_request("post", path, parsed_payload)
    return json.dumps(result, indent=2)

# Alice (Holder) stores the received credential
@mcp.tool()
async def store_credential(cred_ex_id: str, payload: str = "{}") -> str:
    """
    Stores the credential in the holder's wallet.
    Endpoint: POST /issue-credential-2.0/records/{cred_ex_id}/store
    The payload may include a credential_id if you wish to specify it.
    [Reference: OpenAPIDemo.md – Issuing a Credential]
    """
    path = f"/issue-credential-2.0/records/{cred_ex_id}/store"
    try:
        parsed_payload = json.loads(payload)
    except Exception as e:
        return f"Invalid JSON payload: {e}"
    result = await http_request("post", path, parsed_payload)
    return json.dumps(result, indent=2)

# === Present Proof Endpoints (v2.0) ===

@mcp.tool()
async def send_proof_request_v2(proof_request: str) -> str:
    """
    Sends a proof request using ACA‑Py's present-proof-2.0 API.
    The proof_request must be a JSON string.
    [Reference: Aries RFC 0037; ACA‑Py OpenAPI Specification]
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
    [Reference: ACA‑Py OpenAPI Specification]
    """
    path = f"/present-proof-2.0/records/{pres_ex_id}"
    result = await http_request("get", path)
    return json.dumps(result, indent=2)

# === Revocation Endpoint ===

@mcp.tool()
async def revoke_credential(cred_ex_id: str, publish: bool = True) -> str:
    """
    Revokes a credential.
    Optionally, publish the revocation immediately.
    [Reference: ACA‑Py OpenAPI Specification]
    """
    path = "/revocation/revoke"
    payload = {
        "cred_ex_id": cred_ex_id,
        "publish": publish
    }
    result = await http_request("post", path, payload)
    return json.dumps(result, indent=2)

# === Ledger Endpoints ===

@mcp.tool()
async def ledger_get_txn(txn_id: str) -> str:
    """
    Retrieves a ledger transaction by its transaction ID.
    [Reference: ACA‑Py OpenAPI Specification; OpenAPI Specification]
    """
    path = f"/ledger/transactions/{txn_id}"
    result = await http_request("get", path)
    return json.dumps(result, indent=2)

@mcp.tool()
async def ledger_register_did(did_info: str) -> str:
    """
    Registers a DID on the ledger.
    The did_info parameter must be a JSON string with the required fields.
    [Reference: ACA‑Py OpenAPI Specification; Hyperledger Aries documentation]
    """
    try:
        payload = json.loads(did_info)
    except Exception as e:
        return f"Invalid JSON for DID info: {e}"
    result = await http_request("post", "/ledger/register-nym", payload)
    return json.dumps(result, indent=2)

# === Multitenancy Endpoints (if using multitenant mode) ===

@mcp.tool()
async def get_multitenant_wallets() -> str:
    """
    Retrieves a list of tenant wallets (sub‑wallets) in multitenant mode.
    [Reference: ACA‑Py OpenAPI Specification for multitenancy]
    """
    result = await http_request("get", "/multitenancy/wallets")
    return json.dumps(result, indent=2)

if __name__ == '__main__':
    # Run the MCP server over stdio.
    mcp.run(transport="stdio")

