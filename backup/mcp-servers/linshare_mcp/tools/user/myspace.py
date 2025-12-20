import requests
import uuid
import math
from ...app import mcp
from ...config import LINSHARE_USER_URL, LINSHARE_UPLOAD_DIR
from ...utils.logging import logger
from ...utils.common import format_file_size, guess_mime_type
from ...utils.auth import auth_manager

@mcp.tool()
def list_user_documents(user_uuid: str | None = None) -> str:
    """List all documents in your personal space.
    

    Args:
        user_uuid: Optional. The user's UUID. If not provided, uses the currently logged-in user.

    Returns:
        Formatted list of all documents owned by the user
    """
    logger.info(f"Tool called: list_user_documents({user_uuid})")

    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."

    try:
        # Ensure user is logged in
        if not auth_manager.is_logged_in():
            return "Error: User not logged in. Please use 'login_user' first."
            
        # If user_uuid is not provided, use the logged-in user's UUID
        if not user_uuid:
            user_info = auth_manager.get_user_info()
            if user_info and 'uuid' in user_info:
                user_uuid = user_info['uuid']
            else:
                return "Error: Could not determine user UUID from session."

        url = f"{LINSHARE_USER_URL}/documents"

        response = requests.get(
            url,
            headers={
                'accept': 'application/json',
                **auth_manager.get_auth_header()
            },
            timeout=10
        )
        response.raise_for_status()

        documents = response.json()

        if not documents:
            return "No documents found in user's personal space."

        # Format the response nicely
        result = f"Personal Documents ({len(documents)} total):\\n\\n"

        for i, doc in enumerate(documents, 1):
            result += f"{i}. {doc.get('name', 'Unnamed')}\\n"
            result += f"   - UUID: {doc.get('uuid')}\\n"
            result += f"   - Size: {doc.get('size', 0)} bytes\\n"
            result += f"   - Type: {doc.get('type', 'N/A')}\\n"
            result += f"   - Creation Date: {doc.get('creationDate', 'N/A')}\\n"
            result += f"   - Modification Date: {doc.get('modificationDate', 'N/A')}\\n"
            if doc.get('description'):
                result += f"   - Description: {doc.get('description')}\\n"
            result += "\\n"

        return result

    except requests.RequestException as e:
        logger.error(f"Error fetching user documents: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            return f"Error fetching user documents: {str(e)}\\nResponse: {e.response.text}"
        return f"Error fetching user documents: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def share_documents(
    document_uuids: list[str],
    user_uuid: str | None = None,
    recipient_emails: list[str] | None = None,
    mailing_list_uuid: str | None = None,
    subject: str | None = None,
    message: str | None = None,
    expiration_date: str | None = None,
    secured: bool = False,
    creation_acknowledgement: bool = False
) -> str:
    """Share documents from your personal space with other users.
    
    
    Args:
        document_uuids: List of document UUIDs to share (required)
        user_uuid: Optional. The user's UUID. If not provided, uses the currently logged-in user.
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
    logger.info(f"Tool called: share_documents({len(document_uuids)} documents)")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
    
    # Validate that at least one recipient method is provided
    if not recipient_emails and not mailing_list_uuid:
        return "Error: Either recipient_emails or mailing_list_uuid must be provided."
    
    try:
        # Ensure user is logged in
        if not auth_manager.is_logged_in():
            return "Error: User not logged in. Please use 'login_user' first."
            
        # If user_uuid is not provided, use the logged-in user's UUID
        if not user_uuid:
            user_info = auth_manager.get_user_info()
            if user_info and 'uuid' in user_info:
                user_uuid = user_info['uuid']
            else:
                return "Error: Could not determine user UUID from session."

        url = f"{LINSHARE_USER_URL}/{user_uuid}/shares"
        
        # Build request body
        payload = {
            "documents": document_uuids,
            "secured": secured,
            "creationAcknowledgement": creation_acknowledgement
        }
        
        # Add recipients if provided
        if recipient_emails:
            payload["recipients"] = [{"mail": email} for email in recipient_emails]
        
        # Add mailing list if provided
        if mailing_list_uuid:
            payload["mailingListUuid"] = mailing_list_uuid
        
        # Add optional fields
        if subject:
            payload["subject"] = subject
        
        if message:
            payload["message"] = message
        
        if expiration_date:
            payload["expirationDate"] = expiration_date
        
        response = requests.post(
            url,
            json=payload,
            headers={
                'accept': 'application/json',
                'Content-Type': 'application/json',
                **auth_manager.get_auth_header()
            },
            timeout=30
        )
        response.raise_for_status()
        
        share_data = response.json()
        
        # Format the response
        result = f"""Documents Shared Successfully:\\n"""
        
        # Handle both single share and multiple shares response
        shares = share_data if isinstance(share_data, list) else [share_data]
        
        for i, share in enumerate(shares, 1):
            result += f"\\nShare {i}:\\n"
            result += f"   - Share UUID: {share.get('uuid')}\\n"
            result += f"   - Document: {share.get('name', 'N/A')}\\n"
            result += f"   - Recipient: {share.get('recipient', {}).get('mail', 'N/A')}\\n"
            result += f"   - Size: {share.get('size', 0)} bytes\\n"
            result += f"   - Creation Date: {share.get('creationDate', 'N/A')}\\n"
            if share.get('expirationDate'):
                result += f"   - Expiration Date: {share.get('expirationDate')}\\n"
            result += f"   - Downloaded: {share.get('downloaded', 0)} times\\n"
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error sharing documents: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            return f"Error sharing documents: {str(e)}\\nResponse: {e.response.text}"
        return f"Error sharing documents: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"


@mcp.tool()
def upload_document_to_personal_space(
    document_url: str,
    file_name: str,
    user_uuid: str | None = None,
    file_size: int | None = None,
    async_upload: bool = False
) -> str:
    """Upload a document to a user's personal space in LinShare from a URL.
    
    Args:
        document_url: URL of the document to upload (must be publicly accessible)
        file_name: Name of the file (required)
        user_uuid: Optional. The user's UUID. If not provided, uses the currently logged-in user.
        file_size: Size of the file in bytes (optional)
        async_upload: Enable asynchronous upload processing (default: False)
    
    Returns:
        JSON string with uploaded document information
    """
    logger.info(f"Tool called: upload_document_to_personal_space({file_name})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
    
    try:
        # Ensure user is logged in
        if not auth_manager.is_logged_in():
            return "Error: User not logged in. Please use 'login_user' first."
            
        # If user_uuid is not provided, use the logged-in user's UUID
        if not user_uuid:
            user_info = auth_manager.get_user_info()
            if user_info and 'uuid' in user_info:
                user_uuid = user_info['uuid']
            else:
                return "Error: Could not determine user UUID from session."

        url = f"{LINSHARE_USER_URL}/{user_uuid}/documents"
        
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
        
        logger.info(f"Uploading {file_name} to personal space")
        
        response = requests.post(
            url,
            params=params,
            json=payload,
            headers={
                'accept': 'application/json',
                'Content-Type': 'application/json',
                **auth_manager.get_auth_header()
            },
            timeout=60
        )
        
        logger.info(f"Response status: {response.status_code}")
        
        response.raise_for_status()
        
        doc_data = response.json()
        
        result = f"""Document Uploaded to Personal Space Successfully:
- Name: {doc_data.get('name')}
- UUID: {doc_data.get('uuid')}
- Size: {doc_data.get('size')} bytes
- Type: {doc_data.get('type')}
- SHA256: {doc_data.get('sha256sum', 'N/A')}
- Creation Date: {doc_data.get('creationDate')}
- Modification Date: {doc_data.get('modificationDate')}
"""
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error uploading document to personal space: {str(e)}")
        error_msg = f"Error uploading document to personal space: {str(e)}"
        if hasattr(e, 'response') and e.response is not None:
            error_msg += f"\\nStatus Code: {e.response.status_code}"
            error_msg += f"\\nResponse: {e.response.text}"
        return error_msg
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return f"Unexpected error: {str(e)}"

@mcp.tool()
def upload_file_from_directory(
    filename: str,
    workgroup_uuid: str | None = None,
    folder_uuid: str | None = None,
    async_task: bool = True
) -> str:
    """Upload a file from the upload directory to your personal space or a workgroup.
    
    
    Uses the Flow.js chunked upload API for reliable file transfers.
    
    Args:
        filename: Name of file in upload directory
        workgroup_uuid: Optional workgroup UUID (leave empty for personal space)
        folder_uuid: Optional folder UUID within workgroup (leave empty for root)
        async_task: Process asynchronously (default: true)
    
    Returns:
        Upload confirmation
    """
    import time
    
    logger.info(f"Tool called: upload_file_from_directory({filename})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
    
    try:
        # Get auth header (will raise error if not logged in)
        auth_header = auth_manager.get_auth_header()
        
        # Get user info for quota check
        user_info = auth_manager.get_user_info()
        if not user_info or 'uuid' not in user_info:
            return "Error: Could not determine user UUID from session."
        user_uuid = user_info['uuid']
        
        file_path = LINSHARE_UPLOAD_DIR / filename
        
        # Security check
        if not file_path.resolve().is_relative_to(LINSHARE_UPLOAD_DIR.resolve()):
            return "Error: Access denied - path outside upload directory"
        
        if not file_path.exists():
            return f"Error: File '{filename}' not found in upload directory: {LINSHARE_UPLOAD_DIR}"
        
        # Get file info
        file_size = file_path.stat().st_size
        chunk_size = 2097152  # 2MB chunks (2 * 1024 * 1024)
        total_chunks = math.ceil(file_size / chunk_size)
        flow_identifier = str(uuid.uuid4())
        
        # Step 1: Check quota before upload
        # First, get quotaUuid from authentication/authorized endpoint
        logger.info(f"Getting quotaUuid from authentication/authorized endpoint")
        auth_url = f"{LINSHARE_USER_URL}/authentication/authorized"
        auth_response = requests.get(
            auth_url,
            headers={
                'accept': 'application/json',
                **auth_header
            },
            timeout=10
        )
        
        if auth_response.status_code != 200:
            return f"Error getting user authentication info: {auth_response.status_code}\\n{auth_response.text}"
        
        auth_data = auth_response.json()
        quota_uuid = auth_data.get('quotaUuid')
        
        if not quota_uuid:
            return "Error: Could not retrieve quotaUuid from authentication endpoint"
        
        logger.info(f"Retrieved quotaUuid: {quota_uuid}")
        
        # Now get quota information using quotaUuid
        logger.info(f"Checking quota using quotaUuid")
        quota_url = f"{LINSHARE_USER_URL}/quota/{quota_uuid}"
        quota_response = requests.get(
            quota_url,
            headers={
                'accept': 'application/json',
                **auth_header
            },
            timeout=10
        )
        
        if quota_response.status_code != 200:
            return f"Error checking quota: {quota_response.status_code}\\n{quota_response.text}"
        
        quota_data = quota_response.json()
        available_quota = quota_data.get('quota', 0) - quota_data.get('usedSpace', 0)
        
        if file_size > available_quota:
            return f"Error: Insufficient quota. File size: {format_file_size(file_size)}, Available: {format_file_size(available_quota)}"
        
        logger.info(f"Quota check passed. Available: {format_file_size(available_quota)}")
        
        # Step 2: Upload file in chunks
        base_url = f"{LINSHARE_USER_URL}/flow.json"
        
        with open(file_path, 'rb') as f:
            for chunk_number in range(1, total_chunks + 1):
                # Read chunk
                chunk_data = f.read(chunk_size)
                current_chunk_size = len(chunk_data)
                
                # Build form data (Flow.js parameters)
                # LinShare expects these as part of the multipart form, not query params
                data = {
                    'flowChunkNumber': str(chunk_number),
                    'flowChunkSize': str(chunk_size),
                    'flowCurrentChunkSize': str(current_chunk_size),
                    'flowTotalSize': str(file_size),
                    'flowIdentifier': flow_identifier,
                    'flowFilename': filename,
                    'flowRelativePath': filename,
                    'flowTotalChunks': str(total_chunks)
                }
                
                params = {
                    'asyncTask': str(async_task).lower()
                }
                
                # Add optional workgroup parameters only if provided
                if workgroup_uuid:
                    data['workGroupUuid'] = workgroup_uuid
                if folder_uuid:
                    data['workGroupParentNodeUuid'] = folder_uuid
                
                # Prepare multipart form data
                files = {
                    'file': (filename, chunk_data, 'multipart/form-data')
                }
                
                # Upload chunk with JWT auth
                # Note: asyncTask is usually for the completion request, not individual chunks
                response = requests.post(
                    base_url,
                    params=params,
                    data=data,
                    files=files,
                    headers=auth_header,  # JWT Bearer token
                    timeout=60
                )
                
                if response.status_code not in [200, 201, 202]:
                    logger.error(f"Chunk upload failed: {response.status_code} - {response.text}")
                    return f"Error uploading chunk {chunk_number}/{total_chunks}: {response.status_code}\\n{response.text}"
                
                logger.info(f"Uploaded chunk {chunk_number}/{total_chunks}")
        
        # Step 3: Notify server that all chunks are uploaded
        logger.info("Notifying server of upload completion")
        # LinShare's flow.json completion often expects form data, not JSON
        completion_data = {
            'flowIdentifier': flow_identifier,
            'flowTotalChunks': str(total_chunks),
            'flowFilename': filename,
            'chunkUploadSuccess': 'true'
        }
        
        completion_params = {
            'asyncTask': str(async_task).lower()
        }
        
        # Add target location if provided
        if workgroup_uuid:
            completion_data['workGroupUuid'] = workgroup_uuid
        if folder_uuid:
            completion_data['workGroupParentNodeUuid'] = folder_uuid
        
        completion_response = requests.post(
            base_url,
            params=completion_params,
            data=completion_data,
            files={}, # Force multipart/form-data
            headers={
                'accept': '*/*',
                **auth_header
            },
            timeout=30
        )
        
        if completion_response.status_code not in [200, 201, 202]:
            return f"Error completing upload: {completion_response.status_code}\\n{completion_response.text}"
        
        completion_data = completion_response.json()
        upload_uuid = completion_data.get('uuid')
        
        if not upload_uuid:
            return f"Error: No UUID returned from upload completion"
        
        logger.info(f"Upload completion acknowledged. UUID: {upload_uuid}")
        
        # Step 4: Poll for upload status
        status_url = f"{LINSHARE_USER_URL}/flow/{upload_uuid}"
        max_attempts = 30  # Maximum 30 attempts
        poll_interval = 1  # Poll every 1 second
        
        for attempt in range(max_attempts):
            logger.info(f"Checking upload status (attempt {attempt + 1}/{max_attempts})")
            
            status_response = requests.get(
                status_url,
                headers={
                    'accept': 'application/json',
                    **auth_header
                },
                timeout=10
            )
            
            if status_response.status_code != 200:
                return f"Error checking upload status: {status_response.status_code}\\n{status_response.text}"
            
            status_data = status_response.json()
            status = status_data.get('status')
            
            logger.info(f"Upload status: {status}")
            
            if status == 'SUCCESS':
                # Upload completed successfully
                output = f"✅ File uploaded successfully!\\n\\n"
                output += f"File: {filename}\\n"
                output += f"Size: {format_file_size(file_size)}\\n"
                output += f"Chunks: {total_chunks}\\n"
                
                if workgroup_uuid:
                    output += f"Workgroup: {workgroup_uuid}\\n"
                    if folder_uuid:
                        output += f"Folder: {folder_uuid}\\n"
                else:
                    output += f"Location: Personal space\\n"
                
                output += f"Upload UUID: {upload_uuid}\\n"
                
                if status_data.get('resourceUuid'):
                    output += f"Resource UUID: {status_data.get('resourceUuid')}\\n"
                
                output += f"Transfer Duration: {status_data.get('transfertDuration', 'N/A')} ms\\n"
                output += f"Processing Duration: {status_data.get('processingDuration', 'N/A')} ms\\n"
                
                return output
            
            elif status == 'PROCESSING':
                # Still processing, wait and retry
                time.sleep(poll_interval)
                continue
            
            else:
                # Error or unknown status
                error_msg = status_data.get('errorMsg', 'Unknown error')
                error_name = status_data.get('errorName', 'N/A')
                error_code = status_data.get('errorCode', 'N/A')
                return f"Upload failed with status: {status}\\nError: {error_msg}\\nError Name: {error_name}\\nError Code: {error_code}"
        
        # Timeout waiting for completion
        return f"Upload timeout: File is still processing after {max_attempts} attempts. Upload UUID: {upload_uuid}"
        
    except ValueError as e:
        # Auth manager raises ValueError if not logged in
        return f"Error: {str(e)}"
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {str(e)}"