import requests
from requests.auth import HTTPBasicAuth
from ...app import mcp
from ...config import LINSHARE_ADMIN_URL, LINSHARE_USERNAME, LINSHARE_PASSWORD
from ...utils.logging import logger
from ...utils.common import format_file_size

@mcp.tool()
def admin_list_user_documents(user_uuid: str) -> str:
    """List all documents in a specific user's personal space (Admin only).

    Args:
        user_uuid: The user's UUID (actor whose documents to list)

    Returns:
        Formatted list of all documents owned by the user
    """
    logger.info(f"Tool called: admin_list_user_documents({user_uuid})")

    if not LINSHARE_ADMIN_URL:
        return "Error: LINSHARE_BASE_URL not configured."
    if not LINSHARE_USERNAME or not LINSHARE_PASSWORD:
        return "Error: LinShare credentials not configured."

    try:
        url = f"{LINSHARE_ADMIN_URL}/{user_uuid}/documents"

        response = requests.get(
            url,
            auth=HTTPBasicAuth(LINSHARE_USERNAME, LINSHARE_PASSWORD),
            headers={'accept': 'application/json'},
            timeout=10
        )
        response.raise_for_status()

        documents = response.json()

        if not documents:
            return "No documents found in user's personal space."

        # Format the response nicely
        result = f"Personal Documents for {user_uuid} ({len(documents)} total):\n\n"

        for i, doc in enumerate(documents, 1):
            result += f"{i}. {doc.get('name', 'Unnamed')}\n"
            result += f"   - UUID: {doc.get('uuid')}\n"
            result += f"   - Size: {doc.get('size', 0)} bytes\n"
            result += f"   - Type: {doc.get('type', 'N/A')}\n"
            result += f"   - Creation Date: {doc.get('creationDate', 'N/A')}\n"
            if doc.get('description'):
                result += f"   - Description: {doc.get('description')}\n"
            result += "\n"

        return result

    except requests.RequestException as e:
        logger.error(f"Error fetching user documents: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            return f"Error fetching user documents: {str(e)}\nResponse: {e.response.text}"
        return f"Error fetching user documents: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def admin_upload_document_to_personal_space(
    user_uuid: str,
    document_url: str,
    file_name: str,
    file_size: int | None = None,
    async_upload: bool = False
) -> str:
    """Upload a document to a user's personal space from a URL (Admin only).
    
    Args:
        user_uuid: The user's UUID (actor who will own the document)
        document_url: URL of the document to upload (must be publicly accessible)
        file_name: Name of the file (required)
        file_size: Size of the file in bytes (optional)
        async_upload: Enable asynchronous upload processing (default: False)
    
    Returns:
        JSON string with uploaded document information
    """
    logger.info(f"Tool called: admin_upload_document_to_personal_space({user_uuid}, {file_name})")
    
    if not LINSHARE_ADMIN_URL:
        return "Error: LINSHARE_BASE_URL not configured."
    if not LINSHARE_USERNAME or not LINSHARE_PASSWORD:
        return "Error: LinShare credentials not configured."
    
    try:
        url = f"{LINSHARE_ADMIN_URL}/{user_uuid}/documents"
        
        # Query parameters
        params = {
            'async': str(async_upload).lower()
        }
        
        # Build request body
        payload = {
            "url": document_url,
            "fileName": file_name
        }
        
        # Add file size only if provided
        if file_size is not None:
            payload["size"] = file_size
        
        response = requests.post(
            url,
            params=params,
            json=payload,
            auth=HTTPBasicAuth(LINSHARE_USERNAME, LINSHARE_PASSWORD),
            headers={
                'accept': 'application/json',
                'Content-Type': 'application/json'
            },
            timeout=60
        )
        
        response.raise_for_status()
        doc_data = response.json()
        
        result = f"""Document Uploaded to Personal Space Successfully:
- Name: {doc_data.get('name')}
- UUID: {doc_data.get('uuid')}
- Size: {doc_data.get('size')} bytes
- Type: {doc_data.get('type')}
"""
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error uploading document: {str(e)}")
        return f"Error uploading document: {str(e)}"
