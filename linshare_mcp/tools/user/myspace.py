import requests
import uuid
import math
from ...app import mcp
from ...config import LINSHARE_USER_URL, LINSHARE_UPLOAD_DIR
from ...utils.logging import logger
from ...utils.common import format_file_size, guess_mime_type
from ...utils.auth import auth_manager

@mcp.tool()
def list_my_documents() -> str:
    """[USER API] List all documents in your personal space.
    
    🔐 Authentication: JWT token required (use login_user or set LINSHARE_JWT_TOKEN)
    🌐 API Endpoint: User v5 (/documents)

    Returns:
        Formatted list of all documents owned by the user
    """
    logger.info("Tool called: list_my_documents()")

    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."

    try:
        # Ensure user is logged in (loads from config automatically)
        if not auth_manager.is_logged_in():
            return "Error: User not logged in. Please use 'user_login_user' tool first or set LINSHARE_JWT_TOKEN."

        url = f"{LINSHARE_USER_URL}/documents"
        auth_header = auth_manager.get_user_header()
        response = requests.get(
            url,
            headers=auth_header,
            timeout=10
        )
        response.raise_for_status()

        documents = response.json()

        if not documents:
            return "No documents found in your personal space."

        # Format the response nicely
        result = f"Personal Documents ({len(documents)} total):\n\n"

        for i, doc in enumerate(documents, 1):
            result += f"{i}. {doc.get('name', 'Unnamed')}\n"
            result += f"   - UUID: {doc.get('uuid')}\n"
            result += f"   - Size: {format_file_size(doc.get('size', 0))}\n"
            result += f"   - Type: {doc.get('type', 'N/A')}\n"
            if doc.get('creationDate'):
                result += f"   - Created: {doc.get('creationDate')}\n"
            result += "\n"

        return result

    except requests.RequestException as e:
        logger.error(f"Error fetching documents: {str(e)}")
        return f"Error fetching documents: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def share_my_documents(
    document_uuids: list[str],
    recipients: list[dict] | None = None,
    recipient_emails: list[str] | None = None,
    mailing_list_uuids: list[str] | None = None,
    subject: str = "",
    message: str = "",
    expiration_date: str | int | None = None,
    secured: bool = False,
    creation_acknowledgement: bool = False,
    force_anonymous_sharing: bool = False,
    enable_usda: bool = False,
    notification_date_usda: str | int | None = None,
    sharing_note: str = "",
    in_reply_to: str | None = None,
    references: str | None = None,
    external_mail_locale: str = "ENGLISH"
) -> str:
    """[USER API] Share documents from your personal space with other users (User API v5).
    
    🔐 Authentication: JWT token required (use login_user or set LINSHARE_JWT_TOKEN)
    🌐 API Endpoint: User v5 (/shares)
    
    Args:
        document_uuids: List of document UUIDs to share (required)
        recipients: List of recipient objects: [{"firstName": "...", "lastName": "...", "mail": "...", "domain": "..."}]
        recipient_emails: Simple list of emails (will be converted to basic recipient objects)
        mailing_list_uuids: List of mailing list UUIDs to share with
        subject: Subject line for the share notification
        message: Custom message to include with the share
        expiration_date: Expiration date (ISO string or timestamp)
        secured: Whether to require password protection
        creation_acknowledgement: Send acknowledgement to sender
        force_anonymous_sharing: Force anonymous sharing
        enable_usda: Enable USDA (User Selected Delivery Acknowledgement)
        notification_date_usda: Notification date for USDA
        sharing_note: Internal note for the share
        in_reply_to: In-reply-to header value for notification email
        references: References header value for notification email
        external_mail_locale: Locale for external mail (default: "ENGLISH")
    
    Returns:
        Formatted share result
    """
    logger.info(f"Tool called: share_my_documents({len(document_uuids)} documents)")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
    
    # Validate that at least one recipient method is provided
    if not recipients and not recipient_emails and not mailing_list_uuids:
        return "Error: Either recipients, recipient_emails or mailing_list_uuids must be provided."
    
    try:
        # Ensure user is logged in
        if not auth_manager.is_logged_in():
            return "Error: User not logged in. Please use 'user_login_user' tool first or set LINSHARE_JWT_TOKEN."
            
        url = f"{LINSHARE_USER_URL}/shares"
        
        # Build request body
        payload = {
            "documents": document_uuids,
            "secured": secured,
            "creationAcknowledgement": creation_acknowledgement,
            "forceAnonymousSharing": force_anonymous_sharing,
            "enableUSDA": enable_usda,
            "sharingNote": sharing_note,
            "subject": subject,
            "message": message,
            "externalMailLocale": external_mail_locale,
            "mailingListUuid": mailing_list_uuids or []
        }
        
        # Handle recipients
        final_recipients = recipients or []
        if recipient_emails:
            for email in recipient_emails:
                final_recipients.append({"mail": email})
        payload["recipients"] = final_recipients
        
        # Add optional dates
        if expiration_date:
            payload["expirationDate"] = expiration_date
        if notification_date_usda:
            payload["notificationDateForUSDA"] = notification_date_usda
        
        # Add email thread info if provided
        if in_reply_to: payload["inReplyTo"] = in_reply_to
        if references: payload["references"] = references
        
        response = requests.post(
            url,
            json=payload,
            headers=auth_manager.get_user_header(),
            timeout=30
        )
        response.raise_for_status()
        
        share_data = response.json()
        
        # Format the response
        result = "✅ Documents Shared Successfully!\n"
        shares = share_data if isinstance(share_data, list) else [share_data]
        
        for i, share in enumerate(shares, 1):
            result += f"\nShare {i}:\n"
            result += f"   - Document: {share.get('name', 'N/A')}\n"
            result += f"   - Recipient: {share.get('recipient', {}).get('mail', 'N/A')}\n"
            result += f"   - UUID: {share.get('uuid')}\n"
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error sharing documents: {str(e)}")
        # Try to extract more helpful error message from response if available
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_body = e.response.json()
                if 'message' in error_body:
                    error_msg = error_body['message']
            except:
                pass
        return f"Error sharing documents: {error_msg}"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def upload_document_to_my_space(
    document_url: str,
    file_name: str,
    file_size: int | None = None,
    async_upload: bool = False
) -> str:
    """[USER API] Upload a document to your personal space from a URL.
    
    🔐 Authentication: JWT token required (use login_user or set LINSHARE_JWT_TOKEN)
    🌐 API Endpoint: User v5 (/{user_uuid}/documents)
    
    Args:
        document_url: URL of the document to upload (must be publicly accessible)
        file_name: Name of the file (required)
        file_size: Size of the file in bytes (optional)
        async_upload: Enable asynchronous upload processing (default: False)
    
    Returns:
        JSON string with uploaded document information
    """
    logger.info(f"Tool called: upload_document_to_my_space({file_name})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
    
    try:
        # Ensure user is logged in
        if not auth_manager.is_logged_in():
            return "Error: User not logged in. Please use 'user_login_user' tool first or set LINSHARE_JWT_TOKEN."
            
        user_info = auth_manager.get_user_info()
        if not user_info or 'uuid' not in user_info:
            return "Error: Could not determine user UUID from session."
        user_uuid = user_info['uuid']

        url = f"{LINSHARE_USER_URL}/{user_uuid}/documents"
        
        # Query parameters
        params = {'async': str(async_upload).lower()}
        
        # Build request body
        payload = {
            "url": document_url,
            "fileName": file_name
        }
        if file_size is not None: payload["size"] = file_size
        
        response = requests.post(
            url,
            params=params,
            json=payload,
            headers=auth_manager.get_user_header(),
            timeout=60
        )
        response.raise_for_status()
        
        doc_data = response.json()
        
        result = f"""✅ Document Uploaded Successfully:
- Name: {doc_data.get('name')}
- UUID: {doc_data.get('uuid')}
- Size: {format_file_size(doc_data.get('size', 0))}
- Type: {doc_data.get('type')}
"""
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error uploading document: {str(e)}")
        return f"Error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def upload_file_from_local_directory(
    filename: str,
    workgroup_uuid: str | None = None,
    folder_uuid: str | None = None,
    async_task: bool = True
) -> str:
    """[USER API] Upload a file from your local upload directory.
    
    🔐 Authentication: JWT token required (use login_user or set LINSHARE_JWT_TOKEN)
    🌐 API Endpoint: User v5 (/flow.json)
    
    Uses Flow.js chunked upload for reliable file transfers.
    
    Args:
        filename: Name of file in upload directory
        workgroup_uuid: Optional workgroup UUID (leave empty for personal space)
        folder_uuid: Optional folder UUID within workgroup (leave empty for root)
        async_task: Process asynchronously (default: true)
    
    Returns:
        Upload confirmation
    """
    import time
    
    logger.info(f"Tool called: upload_file_from_local_directory({filename})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
    
    http_calls = []
    
    def record_call(method, url, status, payload=None, response=None):
        call_info = f"[{method}] {url}\nStatus: {status}"
        if payload: call_info += f"\nPayload/Params: {payload}"
        if response: call_info += f"\nResponse: {response[:1000]}" # Truncate large responses
        http_calls.append(call_info)

    def get_debug_log():
        return "\n\n--- DETAILED HTTP DEBUG LOG ---\n" + "\n\n".join(http_calls)

    try:
        # Get auth header (will raise error if not logged in)
        auth_header = auth_manager.get_user_header()
        
        file_path = LINSHARE_UPLOAD_DIR / filename
        
        # Security check
        if not file_path.resolve().is_relative_to(LINSHARE_UPLOAD_DIR.resolve()):
            return f"Error: Access denied - path outside upload directory{get_debug_log()}"
        
        if not file_path.exists():
            return f"Error: File '{filename}' not found in upload directory: {LINSHARE_UPLOAD_DIR}{get_debug_log()}"
        
        # Get file info
        file_size = file_path.stat().st_size
        chunk_size = 2097152  # 2MB chunks
        total_chunks = math.ceil(file_size / chunk_size)
        flow_identifier = str(uuid.uuid4())
        
        # Step 1: Check quota before upload
        auth_url = f"{LINSHARE_USER_URL}/authentication/authorized"
        auth_response = requests.get(auth_url, headers=auth_header, timeout=10)
        record_call("GET", auth_url, auth_response.status_code, response=auth_response.text)
        auth_response.raise_for_status()
        quota_uuid = auth_response.json().get('quotaUuid')
        
        if not quota_uuid:
            return f"Error: Could not retrieve quotaUuid.{get_debug_log()}"
        
        quota_url = f"{LINSHARE_USER_URL}/quota/{quota_uuid}"
        quota_response = requests.get(quota_url, headers=auth_header, timeout=10)
        record_call("GET", quota_url, quota_response.status_code, response=quota_response.text)
        quota_response.raise_for_status()
        
        quota_data = quota_response.json()
        available_quota = quota_data.get('quota', 0) - quota_data.get('usedSpace', 0)
        max_file_size_allowed = quota_data.get('maxFileSize')
        
        # Check total remaining quota
        if file_size > available_quota:
            return f"Error: Insufficient quota. File size: {format_file_size(file_size)}, Available: {format_file_size(available_quota)}{get_debug_log()}"
        
        # Check individual max file size limit if provided by server
        if max_file_size_allowed is not None and file_size > max_file_size_allowed:
            return f"Error: File size exceeds the individual file limit. File size: {format_file_size(file_size)}, Maximum allowed: {format_file_size(max_file_size_allowed)}{get_debug_log()}"
        
        # Step 2: Upload file in chunks
        base_url = f"{LINSHARE_USER_URL}/flow.json"
        upload_uuid = None
        
        with open(file_path, 'rb') as f:
            for chunk_number in range(1, total_chunks + 1):
                chunk_data = f.read(chunk_size)
                current_chunk_size = len(chunk_data)
                
                params = {
                    'asyncTask': str(async_task).lower(),
                    'flowChunkNumber': str(chunk_number),
                    'flowChunkSize': str(chunk_size),
                    'flowCurrentChunkSize': str(current_chunk_size),
                    'flowTotalSize': str(file_size),
                    'flowIdentifier': flow_identifier,
                    'flowFilename': filename,
                    'flowRelativePath': filename,
                    'flowTotalChunks': str(total_chunks),
                    'workGroupUuid': workgroup_uuid or '',
                    'workGroupParentNodeUuid': folder_uuid or ''
                }
                
                # Step 2A: GET check to see if chunk exists
                logger.debug(f"GET check for chunk {chunk_number}: params={params}")
                get_response = requests.get(base_url, params=params, headers=auth_header, timeout=10)
                record_call("GET", base_url, get_response.status_code, payload=params, response=get_response.text)
                logger.debug(f"GET response status: {get_response.status_code}")
                
                if get_response.status_code == 200:
                    logger.info(f"Chunk {chunk_number} already exists, skipping POST")
                else:
                    # Step 2B: POST chunk data
                    # Move all params to body except asyncTask
                    post_data = params.copy()
                    async_param = {'asyncTask': post_data.pop('asyncTask')}
                    
                    # Remove empty workgroup parameters if they are empty
                    if not post_data.get('workGroupUuid'): del post_data['workGroupUuid']
                    if not post_data.get('workGroupParentNodeUuid'): del post_data['workGroupParentNodeUuid']
                    
                    logger.debug(f"POSTing chunk {chunk_number}: params={async_param}, data={post_data}")
                    files = {'file': (filename, chunk_data, 'application/octet-stream')}
                    post_response = requests.post(
                        base_url, 
                        params=async_param, # asyncTask in query string
                        data=post_data,    # metadata in form fields
                        files=files, 
                        headers=auth_header, 
                        timeout=60
                    )
                    logger.debug(f"POST response status: {post_response.status_code}")
                    record_call("POST", base_url, post_response.status_code, payload={**async_param, **post_data}, response=post_response.text)
                    post_response.raise_for_status()
                    
                    response_json = post_response.json()
                    logger.debug(f"POST response body: {response_json}")
                    
                    if response_json.get('lastChunk') is True:
                        upload_uuid = response_json.get('uuid')
                        logger.info(f"Last chunk uploaded. UUID: {upload_uuid}")
                        break
        
        # If we didn't get lastChunk: true but finished the loop, try to get UUID from last response
        if not upload_uuid and 'post_response' in locals():
            upload_uuid = post_response.json().get('uuid')

        if not upload_uuid:
            return f"Error: Upload finished but no UUID was returned by the server.{get_debug_log()}"
        
        # Step 4: Poll for upload status
        status_url = f"{LINSHARE_USER_URL}/flow/{upload_uuid}"
        logger.info(f"Starting polling for upload status: {status_url}")
        
        for i in range(30):
            logger.debug(f"Polling attempt {i+1}/30")
            status_response = requests.get(status_url, headers=auth_header, timeout=10)
            record_call("GET", status_url, status_response.status_code, response=status_response.text)
            status_response.raise_for_status()
            status_data = status_response.json()
            status = status_data.get('status')
            logger.debug(f"Status response: {status_data}")
            
            if status == 'SUCCESS':
                output = f"✅ File uploaded successfully!\n\n"
                output += f"File: {filename}\n"
                output += f"Size: {format_file_size(file_size)}\n"
                output += f"Location: {'Workgroup' if workgroup_uuid else 'Personal space'}\n"
                output += get_debug_log()
                return output
            elif status == 'PROCESSING':
                time.sleep(1)
                continue
            else:
                return f"Upload failed with status: {status}. Error: {status_data.get('errorMsg', 'Unknown error')}{get_debug_log()}"
        
        return f"Upload timeout. UUID: {upload_uuid}{get_debug_log()}"
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {str(e)}{get_debug_log()}"