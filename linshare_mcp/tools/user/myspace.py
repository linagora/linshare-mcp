import requests
import uuid
import math
from ...app import mcp
from ...config import LINSHARE_USER_URL, LINSHARE_UPLOAD_DIR
from ...utils.logging import logger
from ...utils.common import format_file_size, guess_mime_type
from ...utils.auth import auth_manager
from datetime import datetime, timedelta, timezone

from .myspace_helpers import _get_share_expiration_policy, _calculate_expiration_timestamp, _validate_expiration_range

@mcp.tool()
def list_my_documents(
    limit: int = 50,
    offset: int = 0
) -> str:
    """[USER API] List documents in your personal space with pagination.
    
    🔐 Authentication: JWT token required
    🌐 API Endpoint: User v5 (/documents)

    Args:
        limit: Max documents to return (default: 50)
        offset: Offset for pagination (default: 0)

    Returns:
        Formatted list of documents with total count metadata
    """
    logger.info(f"Tool called: list_my_documents(limit={limit}, offset={offset})")

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

        total_count = len(documents)
        # Apply client-side pagination (API doesn't support it well on v5 /documents)
        paged_docs = documents[offset : offset + limit]

        # Format the response nicely
        result = f"Personal Documents (Showing {len(paged_docs)} of {total_count} total):\n"
        if offset + limit < total_count:
            result += f"⚠️ NOTE: List is truncated. Use 'offset={offset + limit}' to see more.\n"
        result += "\n"

        for i, doc in enumerate(paged_docs, offset + 1):
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
def user_search_my_documents(pattern: str) -> str:
    """[USER API] Search for documents in your personal space by name.
    
    Use this tool instead of 'list_my_documents' if looking for a specific file.
    
    🔐 Authentication: JWT token required
    🌐 API Endpoint: User v5 (/documents)

    Args:
        pattern: Part of the filename to search for (case-insensitive)
        
    Returns:
        Filtered list of matching documents
    """
    logger.info(f"Tool called: user_search_my_documents(pattern='{pattern}')")

    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."

    try:
        if not auth_manager.is_logged_in():
            return "Error: User not logged in."

        url = f"{LINSHARE_USER_URL}/documents"
        response = requests.get(url, headers=auth_manager.get_user_header(), timeout=10)
        response.raise_for_status()

        documents = response.json()
        pattern_lower = pattern.lower()
        
        matches = [d for d in documents if pattern_lower in d.get('name', '').lower()]

        if not matches:
            return f"No documents found matching '{pattern}' (out of {len(documents)} total files)."

        result = f"Found {len(matches)} matches for '{pattern}':\n\n"
        for i, doc in enumerate(matches, 1):
            result += f"{i}. {doc.get('name')}\n"
            result += f"   - UUID: {doc.get('uuid')}\n"
            result += f"   - Size: {format_file_size(doc.get('size', 0))}\n\n"

        return result

    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return f"Error searching documents: {str(e)}"

@mcp.tool()
def get_user_document_shares(document_uuid: str) -> str:
    """[USER API] Get detailed information about a document and its shares.
    
    🔐 Authentication: JWT token required
    🌐 API Endpoint: User v5 (/documents/{document_uuid}?withShares=true)

    Args:
        document_uuid: UUID of the document to inspect
        
    Returns:
        Formatted information about the document and its active shares
    """
    logger.info(f"Tool called: get_user_document_shares({document_uuid})")

    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."

    try:
        if not auth_manager.is_logged_in():
            return "Error: User not logged in."

        url = f"{LINSHARE_USER_URL}/documents/{document_uuid}"
        params = {"withShares": "true"}
        
        response = requests.get(
            url,
            params=params,
            headers=auth_manager.get_user_header(),
            timeout=10
        )
        response.raise_for_status()
        doc = response.json()

        result = f"Document: {doc.get('name', 'N/A')}\n"
        result += f"UUID: {doc.get('uuid')}\n"
        result += f"Size: {format_file_size(doc.get('size', 0))}\n"
        result += f"Type: {doc.get('type', 'N/A')}\n"
        
        shares = doc.get('shares', [])
        if not shares:
            result += "\nNo active shares for this document."
        else:
            result += f"\nActive Shares ({len(shares)}):\n"
            for i, share in enumerate(shares, 1):
                recipient = share.get('recipient', {}).get('mail', 'Unknown')
                result += f"\n{i}. Recipient: {recipient}\n"
                result += f"   - Share UUID: {share.get('uuid')}\n"
                
                exp_ts = share.get('expirationDate')
                if exp_ts:
                    # ms to datetime
                    dt = datetime.fromtimestamp(exp_ts / 1000, tz=timezone.utc)
                    result += f"   - Expiration: {dt.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                else:
                    result += "   - Expiration: Never\n"
                
                result += f"   - Secured: {share.get('secured', False)}\n"
                result += f"   - Visibility: {share.get('visibility', 'N/A')}\n"

        return result

    except requests.RequestException as e:
        logger.error(f"Error fetching document shares: {str(e)}")
        return f"Error fetching document shares: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def get_user_document_audit(document_uuid: str) -> str:
    """[USER API] Get the audit trail (activity logs) for a specific document.
    
    🔐 Authentication: JWT token required
    🌐 API Endpoint: User v5 (/documents/{document_uuid}/audit)

    Args:
        document_uuid: UUID of the document to inspect
        
    Returns:
        Formatted audit logs showing actvities on the document
    """
    logger.info(f"Tool called: get_user_document_audit({document_uuid})")

    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."

    try:
        if not auth_manager.is_logged_in():
            return "Error: User not logged in."

        url = f"{LINSHARE_USER_URL}/documents/{document_uuid}/audit"
        
        response = requests.get(
            url,
            headers=auth_manager.get_user_header(),
            timeout=10
        )
        response.raise_for_status()
        audit_logs = response.json()

        if not audit_logs:
            return "No audit logs found for this document."

        result = f"Audit Trail for Document {document_uuid}:\n\n"
        
        for entry in audit_logs:
            # Entry structure typically has 'type', 'creationDate', 'author'
            event_type = entry.get('type', 'Unknown Event')
            author = entry.get('author', {}).get('mail', 'Unknown User')
            creation_date = entry.get('creationDate')
            
            date_str = "N/A"
            if creation_date:
                dt = datetime.fromtimestamp(creation_date / 1000, tz=timezone.utc)
                date_str = dt.strftime('%Y-%m-%d %H:%M:%S UTC')
            
            result += f"[{date_str}] {event_type}\n"
            result += f"   - Author: {author}\n"
            
            # Additional details if available
            details = entry.get('details', {})
            if details:
                for key, value in details.items():
                    result += f"   - {key}: {value}\n"
            result += "\n"

        return result

    except requests.RequestException as e:
        logger.error(f"Error fetching document audit: {str(e)}")
        return f"Error fetching document audit: {str(e)}"
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
    password: str | None = None,
    force_anonymous_sharing: bool = False,
    enable_usda: bool = False,
    notification_date_usda: str | int | None = None,
    sharing_note: str = "",
    in_reply_to: str | None = None,
    references: str | None = None,
    external_mail_locale: str = "en"
) -> str:
    """[USER API] Share documents from your personal space with other users (User API v5).
    
    🔐 Authentication: JWT token required (use login_user or set LINSHARE_JWT_TOKEN)
    🌐 API Endpoint: User v5 (/shares)
    
    Note: You can share with any email address. If the email is not found in the LinShare 
    directory, it will automatically be treated as an anonymous share. You do NOT need 
     to verify the existence of the email before sharing.

    Args:
        document_uuids: List of document UUIDs to share (required)
        recipients: List of recipient objects: [{"firstName": "...", "lastName": "...", "mail": "...", "domain": "..."}]
        recipient_emails: Simple list of emails (will be converted to basic recipient objects)
        mailing_list_uuids: List of mailing list UUIDs to share with
        subject: Subject line for the share notification
        message: Custom message to include with the share
        expiration_date: Expiration date (ISO string or timestamp)
        secured: Whether to require password protection
        password: Specific password for the share (if secured=True)
        creation_acknowledgement: Send acknowledgement to sender
        force_anonymous_sharing: Force anonymous sharing (works for both internal and unknown users)
        enable_usda: Enable "Undownloaded document alert" (USDA)
        notification_date_usda: Date for "Notification for undownloaded file"
        sharing_note: Internal note for the share
        in_reply_to: In-reply-to header value for notification email
        references: References header value for notification email
        external_mail_locale: Locale for external mail (default: "en")
    
    Returns:
        Formatted share result including recipient classification (INTERNAL, GUEST, or ANONYMOUS)
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
        
        # Build request body based on template
        payload = {
            "recipients": [],  # Will be populated below
            "documents": document_uuids,
            "mailingListUuid": mailing_list_uuids or [],
            "secured": secured,
            "creationAcknowledgement": creation_acknowledgement,
            "enableUSDA": enable_usda,
            "sharingNote": sharing_note,
            "subject": subject,
            "message": message,
            "forceAnonymousSharing": force_anonymous_sharing,
            "forceAnonymousSharing": force_anonymous_sharing,
            "externalMailLocale": {"en": "ENGLISH", "fr": "FRENCH", "vi": "VIETNAMESE", "ru": "RUSSIAN"}.get(external_mail_locale, "ENGLISH")
        }
        
        if password is not None:
            payload["password"] = password

        # Add email thread info if provided (optional fields in template)
        if in_reply_to: payload["inReplyTo"] = in_reply_to
        if references: payload["references"] = references
        
        # Handle recipients and categorize them
        categorized_recipients = []
        raw_recipients = recipients or []
        if recipient_emails:
            for email in recipient_emails:
                raw_recipients.append({"mail": email})
        
        auth_header = auth_manager.get_user_header()
        user_search_url = f"{LINSHARE_USER_URL}/users"
        
        for r in raw_recipients:
            mail = r.get('mail')
            if not mail:
                categorized_recipients.append({"data": r, "category": "UNKNOWN"})
                continue
                
            try:
                # Search for user to determine type
                search_resp = requests.get(user_search_url, params={'pattern': mail}, headers=auth_header, timeout=10)
                search_resp.raise_for_status()
                users = search_resp.json()
                
                found_user = next((u for u in users if u.get('mail') == mail), None)
                
                if found_user:
                    # Use full user data for better identification (as per template)
                    categorized_recipients.append({
                        "data": {
                            "uuid": found_user.get('uuid'),
                            "domain": found_user.get('domain'),
                            "firstName": found_user.get('firstName'),
                            "lastName": found_user.get('lastName'),
                            "mail": mail,
                            "accountType": found_user.get('accountType', 'INTERNAL'),
                            "external": found_user.get('external', False)
                        },
                        "category": found_user.get('accountType', 'INTERNAL').upper()
                    })
                else:
                    # Anonymous recipient
                    categorized_recipients.append({
                        "data": {"mail": mail},
                        "category": "ANONYMOUS"
                    })
            except Exception as e:
                logger.warning(f"Recipient lookup failed for {mail}: {e}")
                categorized_recipients.append({"data": r, "category": "LOOKUP_FAILED"})

        payload["recipients"] = [cr["data"] for cr in categorized_recipients]
        
        # Handle Expiration Policy
        func_config = _get_share_expiration_policy()
        if func_config:
            enabled = func_config.get('enable', False)
            if not enabled:
                # Rule 3: Feature disabled, do not send expiration
                expiration_date = None
            else:
                can_override = func_config.get('enableOverride', func_config.get('canOverride', False)) # Check both keys just in case
                default_val = func_config.get('value')
                unit = func_config.get('unit', 'DAY')
                default_val = func_config.get('value')

                if not can_override:
                    # Rule 2: Force default expiration
                    if default_val is not None:
                        expiration_date = _calculate_expiration_timestamp(default_val, unit)
                
                elif can_override and expiration_date:
                    # Rule 1: Validate user provided expiration
                    target_ts = expiration_date
                    if isinstance(target_ts, str):
                        try:
                            # Replace Z with +00:00 for fromisoformat compatibility in older python versions if needed, 
                            # though python 3.11+ handles Z. To be safe:
                            target_ts_str = target_ts.replace('Z', '+00:00')
                            dt = datetime.fromisoformat(target_ts_str)
                            
                            # Handle timezone naive dates as UTC
                            if dt.tzinfo is None:
                                dt = dt.replace(tzinfo=timezone.utc)
                            target_ts = int(dt.timestamp() * 1000)
                        except Exception as e:
                            # Fallback for other formats if necessary or just fail
                            return f"Error: Invalid expiration date format (ISO 8601 expected): {e}"
                    
                    is_valid, err_msg = _validate_expiration_range(target_ts, func_config)
                    if not is_valid:
                        return f"Error: {err_msg}"
                    
                    expiration_date = target_ts

        # Add timestamps to payload
        if expiration_date:
            payload["expirationDate"] = expiration_date
        if notification_date_usda:
            # Consistently ensure millisecond timestamp
            target_usda = notification_date_usda
            if isinstance(target_usda, str):
                try:
                    dt_usda = datetime.fromisoformat(target_usda.replace('Z', '+00:00'))
                    if dt_usda.tzinfo is None: dt_usda = dt_usda.replace(tzinfo=timezone.utc)
                    target_usda = int(dt_usda.timestamp() * 1000)
                except: pass
            payload["notificationDateForUSDA"] = target_usda
        
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
        if force_anonymous_sharing:
            result += "🔒 [FORCE ANONYMOUS SHARING ENABLED]\n"
            
        shares = share_data if isinstance(share_data, list) else [share_data]
        
        for i, share in enumerate(shares, 1):
            recipient_info = share.get('recipient', {})
            mail = recipient_info.get('mail', 'N/A')
            
            # Find the category we determined earlier
            category = "UNKNOWN"
            for cr in categorized_recipients:
                if cr["data"].get("mail") == mail:
                    category = cr["category"]
                    break
            
            result += f"\nShare {i}:\n"
            result += f"   - Document: {share.get('name', 'N/A')}\n"
            result += f"   - Recipient: {mail} [{category}]\n"
            result += f"   - UUID: {share.get('uuid')}\n"
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error sharing documents: {str(e)}")
        # Try to extract more helpful error message from response if available
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                # Capture the full response body as it often contains the validation error
                error_msg = f"API Error {e.response.status_code}: {e.response.text}"
                error_body = e.response.json()
                if 'message' in error_body:
                    error_msg = error_body['message']
            except:
                pass
        return f"Error sharing documents: {error_msg}"
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
    logger.info(f"Tool called: upload_file_from_local_directory({filename})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
    
    try:
        file_path = LINSHARE_UPLOAD_DIR / filename
        
        # Security check
        if not file_path.resolve().is_relative_to(LINSHARE_UPLOAD_DIR.resolve()):
            return "Error: Access denied - path outside upload directory"
        
        if not file_path.exists():
            return f"Error: File '{filename}' not found in upload directory: {LINSHARE_UPLOAD_DIR}"
        
        return _upload_file_to_linshare(file_path, workgroup_uuid, folder_uuid, async_task)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {str(e)}"

def _upload_file_to_linshare(
    file_path,
    workgroup_uuid: str | None = None,
    folder_uuid: str | None = None,
    async_task: bool = True
) -> str:
    """Helper to upload a file using LinShare Flow.js API.
    
    Args:
        file_path: Path to the local file (Path object)
        workgroup_uuid: Optional workgroup target
        folder_uuid: Optional folder target
        async_task: Process asynchronously (default: true)
        
    Returns:
        Upload confirmation string with debug log
    """
    import time
    filename = file_path.name
    
    http_calls = []
    
    def record_call(method, url, status, payload=None, response=None):
        call_info = f"[{method}] {url}\nStatus: {status}"
        if payload: call_info += f"\nPayload/Params: {payload}"
        if response: call_info += f"\nResponse: {response[:1000]}" # Truncate large responses
        http_calls.append(call_info)
        # Real-time logging
        logger.info(f"📡 API: [{method}] {url} -> {status}")
        if status >= 400:
            logger.error(f"❌ API Error: {response[:500]}")

    def get_debug_log():
        return "\n\n--- DETAILED HTTP DEBUG LOG ---\n" + "\n\n".join(http_calls)

    try:
        # Get auth header (will raise error if not logged in)
        auth_header = auth_manager.get_user_header()
        
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
                
                if get_response.status_code == 200:
                    logger.info(f"Chunk {chunk_number} already exists, skipping POST")
                else:
                    # Step 2B: POST chunk data
                    post_data = params.copy()
                    async_param = {'asyncTask': post_data.pop('asyncTask')}
                    
                    if not post_data.get('workGroupUuid'): del post_data['workGroupUuid']
                    if not post_data.get('workGroupParentNodeUuid'): del post_data['workGroupParentNodeUuid']
                    
                    files = {'file': (filename, chunk_data, 'application/octet-stream')}
                    post_response = requests.post(
                        base_url, 
                        params=async_param, 
                        data=post_data,
                        files=files, 
                        headers=auth_header, 
                        timeout=60
                    )
                    record_call("POST", base_url, post_response.status_code, payload={**async_param, **post_data}, response=post_response.text)
                    post_response.raise_for_status()
                    
                    response_json = post_response.json()
                    if response_json.get('lastChunk') is True:
                        upload_uuid = response_json.get('uuid') or response_json.get('entry', {}).get('uuid')
                        is_async_response = response_json.get('isAsync', False)
                        
                        # If not async, the upload is finished and entry contains the document
                        if not is_async_response and response_json.get('entry'):
                            entry = response_json['entry']
                            output = f"✅ File uploaded successfully!\n\n"
                            output += f"File: {entry.get('name', filename)}\n"
                            output += f"UUID: {entry.get('uuid')}\n"
                            output += f"Size: {format_file_size(entry.get('size', file_size))}\n"
                            output += f"Location: {'Workgroup' if workgroup_uuid else 'Personal space'}\n"
                            output += get_debug_log()
                            return output
                        
                        break
        
        # Try to find UUID if not captured in loop (e.g. if all chunks existed and were skipped)
        if not upload_uuid:
             # Check if file exists via GET request if all checks pass? 
             # Or more likely, if we skipped POST, we might not get the JSON response with UUID.
             # However, LinShare flow.js protocol usually returns success on last chunk POST.
             # If all chunks were skipped, we might not have a post_response.
             pass

        if not upload_uuid and 'post_response' in locals():
            rj = post_response.json()
            upload_uuid = rj.get('uuid') or rj.get('entry', {}).get('uuid')

        if not upload_uuid:
             # Fallback: if loop finished but no UUID, maybe it was already fully uploaded?
             # We can't easily know the UUID without searching by name, which is unreliable.
             return f"Error: Upload finished but no UUID was returned by the server. Debug Log:\n{get_debug_log()}"
        
        # Step 4: Poll for upload status
        status_url = f"{LINSHARE_USER_URL}/flow/{upload_uuid}"
        
        for i in range(30):
            status_response = requests.get(status_url, headers=auth_header, timeout=10)
            record_call("GET", status_url, status_response.status_code, response=status_response.text)
            status_response.raise_for_status()
            status_data = status_response.json()
            status = status_data.get('status')
            
            if status == 'SUCCESS':
                output = f"✅ File uploaded successfully!\n\n"
                output += f"File: {filename}\n"
                output += f"UUID: {upload_uuid}\n"
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
        logger.error(f"Error in _upload_file_to_linshare: {e}")
        return f"Error: {str(e)}{get_debug_log()}"

@mcp.tool()
def user_delete_document(document_uuid: str) -> str:
    """[USER API] Delete a document from your personal space.
    
    🔐 Authentication: JWT token required
    🌐 API Endpoint: User v5 (/documents/{uuid})
    
    Args:
        document_uuid: UUID of the document to delete
        
    Returns:
        Confirmation of deletion
    """
    logger.info(f"Tool called: user_delete_document({document_uuid})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        if not auth_manager.is_logged_in():
            return "Error: User not logged in."
            
        url = f"{LINSHARE_USER_URL}/documents/{document_uuid}"
        
        response = requests.delete(
            url,
            headers=auth_manager.get_user_header(),
            timeout=10
        )
        response.raise_for_status()
        
        return f"✅ Document ({document_uuid}) deleted successfully."
        
    except requests.RequestException as e:
        logger.error(f"Error deleting document: {str(e)}")
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
             try:
                error_msg = f"API Error {e.response.status_code}: {e.response.text}"
             except: pass
        return f"Error deleting document: {error_msg}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def user_delete_share(share_uuid: str) -> str:
    """[USER API] Delete a specific share.
    
    🔐 Authentication: JWT token required
    🌐 API Endpoint: User v5 (/shares/{uuid})
    
    Args:
        share_uuid: UUID of the share to delete
        
    Returns:
        Confirmation of deletion
    """
    logger.info(f"Tool called: user_delete_share({share_uuid})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        if not auth_manager.is_logged_in():
            return "Error: User not logged in."
            
        url = f"{LINSHARE_USER_URL}/shares/{share_uuid}"
        
        response = requests.delete(
            url,
            headers=auth_manager.get_user_header(),
            timeout=10
        )
        response.raise_for_status()
        
        return f"✅ Share ({share_uuid}) deleted successfully."
        
    except requests.RequestException as e:
        logger.error(f"Error deleting share: {str(e)}")
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
             try:
                error_msg = f"API Error {e.response.status_code}: {e.response.text}"
             except: pass
        return f"Error deleting share: {error_msg}"
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def user_remote_upload_from_url(
    url: str,
    filename: str,
    async_task: bool = True
) -> str:
    """[USER API] Upload a file to your personal space from a public URL.
    
    🔐 Authentication: JWT token required
    🌐 API Endpoint: User v5 (/documents)
    
    Args:
        url: Public URL of the file to fetch
        filename: Name to give the file in LinShare
        async_task: Process asynchronously (default: true)
        
    Returns:
        Confirmation of the upload request
    """
    logger.info(f"Tool called: user_remote_upload_from_url({filename}, {url})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        if not auth_manager.is_logged_in():
            return "Error: User not logged in. Please use 'user_login_user' tool first."
            
        # Endpoint: POST /documents (Create a document from an URL)
        api_url = f"{LINSHARE_USER_URL}/documents"
        
        payload = {
            "url": url,
            "fileName": filename
        }
        
        response = requests.post(
            api_url,
            json=payload,
            headers=auth_manager.get_user_header(),
            params={"async": str(async_task).lower()},
            timeout=30
        )
        
        response.raise_for_status()
        doc = response.json()
        
        async_info = doc.get('async', {})
        res_uuid = doc.get('uuid') or async_info.get('uuid')
        res_status = async_info.get('status', 'SUCCESS' if not async_task else 'PENDING')
        
        return f"✅ URL upload initiated!\n\nDocument: {doc.get('name')}\nUUID: {res_uuid}\nStatus: {res_status}"
        
    except Exception as e:
        logger.error(f"Error in user_remote_upload_from_url: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def user_remote_upload_by_chunks(
    filename: str,
    chunk_index: int,
    total_chunks: int,
    data_b64: str,
    session_id: str | None = None,
    workgroup_uuid: str | None = None
) -> str:
    """[USER API] Upload a file in chunks for remote (SSE) clients.
    
    Receives base64-encoded chunks, reassembles the file on the server, 
    and then automatically pushes it to LinShare.
    
    Args:
        filename: Name of the file being uploaded
        chunk_index: Current chunk index (0-based)
        total_chunks: Total number of chunks
        data_b64: Base64-encoded chunk data
        session_id: Optional unique session ID to distinguish parallel uploads
        workgroup_uuid: Optional target workgroup
        
    Returns:
        Status message (e.g., "Chunk 1/5 received" or "Success")
    """
    import base64
    from pathlib import Path
    
    logger.info(f"Tool called: user_remote_upload_by_chunks({filename}, {chunk_index+1}/{total_chunks})")
    
    if not LINSHARE_UPLOAD_DIR:
        return "Error: LINSHARE_UPLOAD_DIR not configured."

    # Create a unique temp name for reassembly
    safe_session = session_id or "default"
    temp_dir = LINSHARE_UPLOAD_DIR / ".remote_uploads" / safe_session
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    chunk_file = temp_dir / f"{filename}.part{chunk_index}"
    
    try:
        # Decode and write chunk
        chunk_bytes = base64.b64decode(data_b64)
        with open(chunk_file, 'wb') as f:
            f.write(chunk_bytes)
            
        # Check if all chunks are present
        parts = list(temp_dir.glob(f"{filename}.part*"))
        if len(parts) == total_chunks:
            # Reassemble
            final_path = LINSHARE_UPLOAD_DIR / filename
            with open(final_path, 'wb') as outfile:
                for i in range(total_chunks):
                    part_file = temp_dir / f"{filename}.part{i}"
                    with open(part_file, 'rb') as infile:
                        outfile.write(infile.read())
                    part_file.unlink() # Delete part
            
            # Clean up empty temp_dir
            try:
                temp_dir.rmdir()
            except:
                pass
            
            logger.info(f"Reassembly complete for {filename}. Pushing to LinShare...")
            return _upload_file_to_linshare(final_path, workgroup_uuid=workgroup_uuid)
        
        return f"✅ Chunk {chunk_index + 1}/{total_chunks} received. Waiting for remaining chunks."
        
    except Exception as e:
        logger.error(f"Error in user_remote_upload_by_chunks: {e}")
        return f"Error: {str(e)}"