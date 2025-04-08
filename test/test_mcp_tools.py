import pytest
import json
import logging
import pytest_asyncio
from mcp_tools.traction_api_tool import get_bearer_token, get_tenant_details, create_out_of_band_invitation, list_connections, get_created_schemas, create_schema, get_schema_by_id, create_credential_definition
import base64

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Global configuration for the tenant credentials.
TENANT_ID = "8f719188-a40b-43f2-bb96-56e28ba1dc53"
API_KEY = "fd34f6365cef4ae0942e9d847bd22e96"

# SESSION-SCOPED FIXTURE: Use pytest_asyncio.fixture so that the token is properly awaited.
@pytest_asyncio.fixture
async def bearer_token():
    """
    Retrieves and caches the bearer token for each test function.
    """
    token = await get_bearer_token(TENANT_ID, API_KEY)
    if token.startswith("Error"):
        pytest.skip("Bearer token not available. Provide valid credentials.")
    return token

@pytest.mark.asyncio
async def test_get_tenant_details_valid(bearer_token):
    """
    Test retrieving tenant details using the bearer token.
    """
    # Use the already awaited bearer_token fixture directly.
    token = bearer_token  
    details_str = await get_tenant_details(token)
    logger.info(f"Retrieved tenant details: {details_str}")

    # Check that the output is a string.
    assert isinstance(details_str, str), "Returned tenant details is not a string."
    
    # If there's an error, skip the test.
    if "Error" in details_str:
        pytest.skip(
            "Tenant details not available with the provided token. Please provide a valid token for full integration testing."
        )
    
    # Parse the response.
    try:
        details = json.loads(details_str)
    except json.JSONDecodeError as e:
        pytest.fail(f"Returned tenant details is not valid JSON: {e}")
    
    # Verify that the parsed details are a dictionary.
    assert isinstance(details, dict), "Tenant details are not a dictionary."
    print("Parsed tenant details:", details)



@pytest.mark.asyncio
async def test_create_out_of_band_invitation(bearer_token):
    """
    Test creating an out-of-band invitation with the expected output being a connection URL.
    
    The output should be a URL string starting with the ngrok base URL (https://92ce-80-40-22-48.ngrok-free.app)
    and containing the 'oob' query parameter, whose value is a URL-safe Base64 encoded invitation.
    """
    token = bearer_token
    
    # Call the MCP tool. With the new implementation, if no ngrok_base_url parameter is passed,
    # the tool uses the default, and returns the connection URL.
    connection_url = await create_out_of_band_invitation(
        auth_token=token,
        alias="Unit Test Invitation",
        handshake=True,
        metadata={"test_meta": "example"},
        use_public_did=True,
        my_label="Unit Test Label"
    )
    
    print("\n\nReceived connection URL: %s \n\n", connection_url)
    logger.info("\n\nReceived connection URL: %s \n\n", connection_url)
    assert isinstance(connection_url, str), "Output is not a string"
    
    # Define expected base URL.
    base_url = "https://92ce-80-40-22-48.ngrok-free.app"
    
    # Validate that the connection URL starts with the expected base URL.
    assert connection_url.startswith(base_url), "Connection URL doesn't start with expected base URL"
    
    # Validate the presence of the 'oob' query parameter.
    query_split = connection_url.split("?oob=")
    assert len(query_split) == 2, "Connection URL missing '?oob=' query parameter"
    encoded_invitation = query_split[1]
    
    # Base64 strings may have padding stripped; add it back before decoding.
    padding = "=" * ((4 - len(encoded_invitation) % 4) % 4)
    encoded_invitation_padded = encoded_invitation + padding
    try:
        decoded_bytes = base64.urlsafe_b64decode(encoded_invitation_padded)
        invitation_json = decoded_bytes.decode("utf-8")
        invitation = json.loads(invitation_json)
    except Exception as e:
        pytest.fail("Failed to decode and parse invitation from the connection URL: " + str(e))
    
    # Optionally, verify that the decoded invitation contains expected keys.
    assert "handshake_protocols" in invitation or "services" in invitation, (
        "Decoded invitation doesn't contain expected keys"
    )
    print("Decoded invitation:", json.dumps(invitation, indent=2))


@pytest.mark.asyncio
async def test_list_connections_valid(bearer_token):
    """
    Test retrieving agent connections using the bearer token.
    Fails if the response has an HTTP error or lacks expected structure.
    """
    token = bearer_token

    # Run the tool with default arguments
    response_str = await list_connections(auth_token=token, limit=10)

    logger.info("Received list_connections response: %s", response_str)
    assert isinstance(response_str, str), "Response is not a string."

    try:
        response_json = json.loads(response_str)
    except json.JSONDecodeError as e:
        pytest.fail(f"Response is not valid JSON: {e}")

    # Handle failure structure returned by http_request
    if "status" in response_json and response_json["status"] != 200:
        pytest.fail(f"API call failed with status {response_json['status']}: {response_json.get('error', 'Unknown error')}")

    assert "results" in response_json, "Missing 'results' key in response."
    assert isinstance(response_json["results"], list), "'results' is not a list."
    print("Connection results:", response_json["results"])

if __name__ == '__main__':
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("AcaPyMCPToolsEnriched")
    mcp.run(transport="stdio")


@pytest.mark.asyncio
async def test_get_created_schemas_valid(bearer_token):
    """
    Test retrieving schemas created by this agent.
    Fails if the response contains an HTTP error or unexpected format.
    """
    token = bearer_token

    response_str = await get_created_schemas(auth_token=token)

    logger.info("Received created schemas response: %s", response_str)
    assert isinstance(response_str, str), "Response is not a string."

    try:
        response_json = json.loads(response_str)
    except json.JSONDecodeError as e:
        pytest.fail(f"Response is not valid JSON: {e}")

    # Error handling
    if "status" in response_json and response_json["status"] != 200:
        pytest.fail(f"Request failed with status {response_json['status']}: {response_json.get('error', 'Unknown error')}")

    assert "schema_ids" in response_json, "Missing 'schema_ids' in response."
    assert isinstance(response_json["schema_ids"], list), "'schema_ids' is not a list."
    print("Created schema IDs:", response_json["schema_ids"])

@pytest.mark.asyncio
async def test_create_schema_valid(bearer_token):
    """
    Test creating a schema and sending it to the ledger.
    """
    token = bearer_token

    response_str = await create_schema(
        auth_token=token,
        attributes=["score"],
        schema_name="PREFIS",
        schema_version="1.0"
    )

    logger.info("Received schema creation response: %s", response_str)
    assert isinstance(response_str, str), "Response is not a string."

    try:
        response_json = json.loads(response_str)
    except json.JSONDecodeError as e:
        pytest.fail(f"Response is not valid JSON: {e}")

    # Handle failure cases returned from http_request
    if "status" in response_json and response_json["status"] != 200:
        pytest.fail(f"Schema creation failed with status {response_json['status']}: {response_json.get('error', 'Unknown error')}")

    assert "sent" in response_json or "schema_id" in response_json, "No schema ID or 'sent' key in response."
    print("Schema creation response keys:", list(response_json.keys()))

@pytest.mark.asyncio
async def test_get_schema_by_id_valid(bearer_token):
    """
    Test retrieving a schema definition from the ledger using a known schema_id.
    """
    token = bearer_token
    schema_id = "GeLsnrSj8Xofy6B9T5MMTi:2:PREFIS:1.0"  # Replace with a valid schema_id for your environment

    response_str = await get_schema_by_id(auth_token=token, schema_id=schema_id)

    logger.info("Received schema by ID response: %s", response_str)
    assert isinstance(response_str, str), "Response is not a string."

    try:
        response_json = json.loads(response_str)
    except json.JSONDecodeError as e:
        pytest.fail(f"Response is not valid JSON: {e}")

    if "status" in response_json and response_json["status"] != 200:
        pytest.fail(f"Schema fetch failed with status {response_json['status']}: {response_json.get('error', 'Unknown error')}")

    assert "schema" in response_json, "Missing 'schema' in response."
    schema = response_json["schema"]
    assert "id" in schema and "attrNames" in schema, "Schema lacks 'id' or 'attrNames'."
    print("Fetched schema ID:", schema["id"])

@pytest.mark.asyncio
async def test_create_credential_definition_valid(bearer_token):
    """
    Test creating a credential definition based on an existing schema.
    """
    token = bearer_token
    schema_id = "GeLsnrSj8Xofy6B9T5MMTi:2:PREFIS:1.0"  # Replace with actual schema ID

    response_str = await create_credential_definition(
        auth_token=token,
        schema_id=schema_id,
        support_revocation=True,
        tag="bingo"
    )

    logger.info("Received credential definition response: %s", response_str)
    assert isinstance(response_str, str), "Response is not a string."

    try:
        response_json = json.loads(response_str)
    except json.JSONDecodeError as e:
        pytest.fail(f"Response is not valid JSON: {e}")

    if "status" in response_json and response_json["status"] != 200:
        pytest.fail(f"Credential definition creation failed with status {response_json['status']}: {response_json.get('error', 'Unknown error')}")

    assert "sent" in response_json, "Missing 'sent' in response."
    sent = response_json["sent"]
    assert "credential_definition_id" in sent, "Missing 'credential_definition_id' in response."
    print("Created credential definition ID:", sent["credential_definition_id"])


    TEST_INVITATION_URL = (
    "ps://92ce-80-40-22-48.ngrok-free.app"
    "?oob=eyJAdHlwZSI6Imh0dHBzOi8vZGlkY29tbS5vcmcvb3V0LW9mLWJhbmQvMS4xL2ludml0YXRpb24iLCJAaWQiOiIzMWRjMDRkNC00MGE5LTQzYzMtYmMyZi02NTMxMmI0OWYzN2UiLCJsYWJlbCI6IlVuaXQgVGVzdCBMYWJlbCIsImhhbmRzaGFrZV9wcm90b2NvbHMiOlsiaHR0cHM6Ly9kaWRjb21tLm9yZy9kaWRleGNoYW5nZS8xLjAiXSwic2VydmljZXMiOlsiZGlkOnNvdjpHZUxzbnJTajhYb2Z5NkI5VDVNTVRpIl19"
)


