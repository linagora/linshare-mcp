import requests
from ...app import mcp
from ...config import LINSHARE_ADMIN_URL as LINSHARE_BASE_URL
from ...utils.logging import logger
from ...utils.common import format_file_size
from ...utils.auth import auth_manager

@mcp.tool()
def list_user_documents(user_uuid: str) -> str:
    """List all documents in a user's personal space.

    Args:
        user_uuid: The user's UUID (actor whose documents to list)

    Returns:
        Formatted list of all documents owned by the user
    """
    logger.info(f"Tool called: list_user_documents({user_uuid})")

    if not LINSHARE_BASE_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."

    try:
        url = f"{LINSHARE_BASE_URL}/{user_uuid}/documents"
        admin_auth = auth_manager.get_admin_auth()

        response = requests.get(
            url,
            auth=admin_auth,
            headers={'accept': 'application/json'},
            timeout=10
        )
        response.raise_for_status()

        documents = response.json()

        if not documents:
            return "No documents found in user's personal space."

        result = f"Personal Documents ({len(documents)} total):\n\n"

        for i, doc in enumerate(documents, 1):
            result += f"{i}. {doc.get('name', 'Unnamed')}\n"
            result += f"   - UUID: {doc.get('uuid')}\n"
            result += f"   - Size: {doc.get('size', 0)} bytes\n"
            result += f"   - Type: {doc.get('type', 'N/A')}\n\n"

        return result

    except requests.RequestException as e:
        logger.error(f"Error fetching user documents: {str(e)}")
        return f"Error: {str(e)}"

@mcp.tool()
def share_documents(
    user_uuid: str,
    document_uuids: list,
    recipient_emails: list = None,
    mailing_list_uuid: str = None,
    subject: str = None,
    message: str = None,
    expiration_date: str = None,
    secured: bool = False,
    creation_acknowledgement: bool = False
) -> str:
    """Share documents from user's personal space with other users.
    
    Args:
        user_uuid: The user's UUID (actor sharing the documents)
        document_uuids: List of document UUIDs to share (required)
        recipient_emails: List of recipient email addresses (at least one of recipient_emails or mailing_list_uuid required)
        mailing_list_uuid: UUID of mailing list to share with (alternative to recipient_emails)
        subject: Subject line for the share notification
        message: Custom message to include with the share
        expiration_date: Expiration date in ISO format (e.g., "2025-12-31T23:59:59Z")
        secured: Whether to require password protection (default: False)
        creation_acknowledgement: Send acknowledgement to sender (default: False)
    
    Returns:
        JSON string with share creation result
    """
    logger.info(f"Tool called: share_documents({user_uuid}, {len(document_uuids)} documents)")
    
    if not LINSHARE_BASE_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    
    if not LINSHARE_USERNAME or not LINSHARE_PASSWORD:
        return "Error: LinShare credentials not configured."
    
    if not recipient_emails and not mailing_list_uuid:
        return "Error: Either recipient_emails or mailing_list_uuid must be provided."
    
    try:
        url = f"{LINSHARE_BASE_URL}/{user_uuid}/shares"
        
        payload = {
            "documents": document_uuids,
            "secured": secured,
            "creationAcknowledgement": creation_acknowledgement
        }
        
        if recipient_emails:
            payload["recipients"] = [{"mail": email} for email in recipient_emails]
        
        if mailing_list_uuid:
            payload["mailingListUuid"] = mailing_list_uuid
        
        if subject: payload["subject"] = subject
        if message: payload["message"] = message
        if expiration_date: payload["expirationDate"] = expiration_date
        
        admin_auth = auth_manager.get_admin_auth()

        response = requests.post(
            url,
            json=payload,
            auth=admin_auth,
            headers={
                'accept': 'application/json',
                'Content-Type': 'application/json'
            },
            timeout=30
        )
        response.raise_for_status()
        
        share_data = response.json()
        result = "Documents Shared Successfully:\n"
        shares = share_data if isinstance(share_data, list) else [share_data]
        
        for i, share in enumerate(shares, 1):
            result += f"\nShare {i}:\n"
            result += f"   - Share UUID: {share.get('uuid')}\n"
            result += f"   - Document: {share.get('name', 'N/A')}\n"
            result += f"   - Recipient: {share.get('recipient', {}).get('mail', 'N/A')}\n"
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error sharing documents: {str(e)}")
        return f"Error: {str(e)}"

@mcp.tool()
def upload_document_to_personal_space(
    user_uuid: str,
    document_url: str,
    file_name: str,
    file_size: int = None,
    async_upload: bool = False
) -> str:
    """Upload a document to a user's personal space in LinShare from a URL.
    
    Args:
        user_uuid: The user's UUID (actor who will own the document)
        document_url: URL of the document to upload (must be publicly accessible)
        file_name: Name of the file (required)
        file_size: Size of the file in bytes (optional)
        async_upload: Enable asynchronous upload processing (default: False)
    
    Returns:
        JSON string with uploaded document information
    """
    logger.info(f"Tool called: upload_document_to_personal_space({user_uuid}, {file_name})")
    
    if not LINSHARE_BASE_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    
    if not LINSHARE_USERNAME or not LINSHARE_PASSWORD:
        return "Error: LinShare credentials not configured."
    
    try:
        url = f"{LINSHARE_BASE_URL}/{user_uuid}/documents"
        params = {'async': str(async_upload).lower()}
        payload = {"url": document_url, "fileName": file_name}
        if file_size is not None: payload["size"] = file_size
        
        admin_auth = auth_manager.get_admin_auth()

        response = requests.post(
            url,
            params=params,
            json=payload,
            auth=admin_auth,
            headers={
                'accept': 'application/json',
                'Content-Type': 'application/json'
            },
            timeout=60
        )
        response.raise_for_status()
        doc_data = response.json()
        
        result = f"Document Uploaded to Personal Space Successfully:\n- Name: {doc_data.get('name')}\n- UUID: {doc_data.get('uuid')}\n"
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error: {str(e)}")
        return f"Error: {str(e)}"
