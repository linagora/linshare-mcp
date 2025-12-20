import requests
from requests.auth import HTTPBasicAuth
from ...app import mcp
from ...config import (
    LINSHARE_ADMIN_URL,
    LINSHARE_USERNAME,
    LINSHARE_PASSWORD,
    LINSHARE_UPLOAD_DIR,
    COMMON_ROLES
)
from ...utils.logging import logger
from ...utils.common import format_file_size, guess_mime_type, get_role_uuid

@mcp.tool()
def upload_file_to_workgroup(
    actor_uuid: str,
    workgroup_uuid: str,
    filename: str,
    folder_uuid: str | None = None,
    description: str | None = None,
    async_upload: bool = False,
    strict: bool = False
) -> str:
    """Upload a file from the upload directory to a LinShare workgroup.
    
    Args:
        actor_uuid: UUID of the user
        workgroup_uuid: UUID of the workgroup
        filename: Name of file in upload directory
        folder_uuid: Optional folder UUID (for uploading to subfolders)
        description: Optional description
        async_upload: Upload asynchronously (default: false)
        strict: Raise error if file with same name exists (default: false)
    
    Returns:
        Upload confirmation
    """
    logger.info(f"Tool called: upload_file_to_workgroup({filename})")
    
    if not LINSHARE_ADMIN_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    if not LINSHARE_USERNAME or not LINSHARE_PASSWORD:
        return "Error: LinShare credentials not configured."
    
    try:
        file_path = LINSHARE_UPLOAD_DIR / filename
        
        # Security check
        if not file_path.resolve().is_relative_to(LINSHARE_UPLOAD_DIR.resolve()):
            return "Error: Access denied - path outside upload directory"
        
        if not file_path.exists():
            return f"Error: File '{filename}' not found in upload directory: {LINSHARE_UPLOAD_DIR}"
        
        # Get file size
        file_size = file_path.stat().st_size
        
        # Build URL
        if folder_uuid:
            url = f"{LINSHARE_ADMIN_URL}/{actor_uuid}/workgroups/{workgroup_uuid}/folders/{folder_uuid}/entries"
        else:
            url = f"{LINSHARE_ADMIN_URL}/{actor_uuid}/workgroups/{workgroup_uuid}/entries"
        
        # Query parameters
        params = {
            'async': str(async_upload).lower(),
            'strict': str(strict).lower()
        }
        
        # Prepare multipart form data
        # IMPORTANT: LinShare requires specific field names
        with open(file_path, 'rb') as f:
            files = {
                'file': (filename, f, guess_mime_type(filename))
            }
            
            # Required and optional form fields
            data = {
                'filesize': str(file_size),  # Required!
                'filename': filename,         # Recommended
            }
            
            if description:
                data['description'] = description
            
            # Make the request with Content-Length header
            response = requests.post(
                url,
                params=params,
                files=files,
                data=data,
                auth=HTTPBasicAuth(LINSHARE_USERNAME, LINSHARE_PASSWORD),
                headers={
                    'accept': 'application/json',
                },
                timeout=60
            )
        
        # Check for errors
        if response.status_code != 200:
            error_msg = f"Upload failed with status {response.status_code}\n"
            try:
                error_detail = response.json()
                error_msg += f"Error: {error_detail.get('message', response.text)}"
            except:
                error_msg += f"Response: {response.text}"
            return error_msg
        
        response.raise_for_status()
        result = response.json()
        
        # Format success response
        output = f"✅ File '{filename}' uploaded successfully to workgroup!\n\n"
        output += f"File: {result.get('name', filename)}\n"
        output += f"UUID: {result.get('uuid', 'N/A')}\n"
        output += f"Size: {format_file_size(result.get('size', file_size))}\n"
        output += f"Type: {result.get('mimeType', 'N/A')}\n"
        output += f"Workgroup: {workgroup_uuid}\n"
        
        if folder_uuid:
            output += f"Folder: {folder_uuid}\n"
        else:
            output += f"Location: Root\n"
        
        if result.get('creationDate'):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(result['creationDate'].replace('Z', '+00:00'))
                output += f"Uploaded: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
            except:
                pass
        
        return output
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error uploading file: {e}")
        error_msg = f"Error uploading file: {e.response.status_code}\n"
        try:
            error_detail = e.response.json()
            error_msg += f"Message: {error_detail.get('message', e.response.text)}"
        except:
            error_msg += f"Response: {e.response.text}"
        return error_msg
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def list_workgroup_entries(
    actor_uuid: str,
    workgroup_uuid: str
) -> str:
    """List all file and folder entries at the root level of a specific workgroup.
    
    Args:
        actor_uuid: UUID of the user (actor) accessing the workgroup
        workgroup_uuid: UUID of the workgroup to list entries from
    
    Returns:
        Formatted list of all files and folders in the workgroup root
    """
    logger.info(f"Tool called: list_workgroup_entries({actor_uuid}, {workgroup_uuid})")
    
    if not LINSHARE_ADMIN_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    if not LINSHARE_USERNAME or not LINSHARE_PASSWORD:
        return "Error: LinShare credentials not configured."
    
    try:
        url = f"{LINSHARE_ADMIN_URL}/{actor_uuid}/workgroups/{workgroup_uuid}/entries"
        
        response = requests.get(
            url,
            auth=HTTPBasicAuth(LINSHARE_USERNAME, LINSHARE_PASSWORD),
            headers={'accept': 'application/json'},
            timeout=10
        )
        response.raise_for_status()
        
        entries = response.json()
        
        if not entries:
            return f"No entries found in workgroup {workgroup_uuid}."
        
        # Separate folders and files
        folders = [e for e in entries if e.get('type') == 'FOLDER']
        files = [e for e in entries if e.get('type') in ['DOCUMENT', 'DOCUMENT_REVISION']]
        
        # Format the response nicely
        result = f"Workgroup Entries for {workgroup_uuid}\n"
        result += f"({len(entries)} total: {len(folders)} folders, {len(files)} files)\n\n"
        
        # List folders first
        if folders:
            result += "📁 FOLDERS:\n"
            for i, folder in enumerate(folders, 1):
                result += f"{i}. {folder.get('name', 'Unnamed folder')}"
                result += f" | UUID: {folder.get('uuid', 'N/A')}"
                
                if folder.get('creationDate'):
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(folder['creationDate'].replace('Z', '+00:00'))
                        result += f" | Created: {dt.strftime('%Y-%m-%d %H:%M')}"
                    except:
                        pass
                
                if folder.get('modificationDate'):
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(folder['modificationDate'].replace('Z', '+00:00'))
                        result += f" | Modified: {dt.strftime('%Y-%m-%d %H:%M')}"
                    except:
                        pass
                
                result += "\n"
            result += "\n"
        
        # List files
        if files:
            result += "📄 FILES:\n"
            for i, file in enumerate(files, 1):
                result += f"{i}. {file.get('name', 'Unnamed file')}"
                
                # File size
                size = file.get('size', 0)
                if size:
                    result += f" | Size: {format_file_size(size)}"
                
                # MIME type
                if file.get('mimeType'):
                    result += f" | Type: {file['mimeType']}"
                
                result += f"\n   UUID: {file.get('uuid', 'N/A')}"
                
                # Dates
                if file.get('creationDate'):
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(file['creationDate'].replace('Z', '+00:00'))
                        result += f" | Uploaded: {dt.strftime('%Y-%m-%d %H:%M')}"
                    except:
                        pass
                
                # Author
                if file.get('lastAuthor'):
                    author = file['lastAuthor']
                    author_name = f"{author.get('firstName', '')} {author.get('lastName', '')}".strip()
                    if author_name:
                        result += f"\n   Author: {author_name}"
                    if author.get('mail'):
                        result += f" ({author['mail']})"
                
                result += "\n\n"
        
        return result
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error listing workgroup entries: {e}")
        return f"Error retrieving workgroup entries: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        logger.error(f"Error listing workgroup entries: {e}")
        return f"Error: {str(e)}"


@mcp.tool()
def create_shared_space(
    user_uuid: str,
    name: str,
    node_type: str,
    parent_uuid: str | None = None,
    description: str | None = None
) -> str:
    """Create a new workspace or workgroup in LinShare.
    
    Args:
        user_uuid: The user's UUID (actor creating the space)
        name: Name of the workspace/workgroup (required)
        node_type: Type of node - must be either "WORK_SPACE" or "WORK_GROUP" (required)
        parent_uuid: UUID of parent WORK_SPACE (only for WORK_GROUP, optional)
        description: Description of the workspace/workgroup (optional)
    
    Returns:
        JSON string with created shared space information
    """
    logger.info(f"Tool called: create_shared_space({user_uuid}, {name}, {node_type})")
    
    if not LINSHARE_ADMIN_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    
    if not LINSHARE_USERNAME or not LINSHARE_PASSWORD:
        return "Error: LinShare credentials not configured."
    
    # Validate node_type
    valid_types = ["WORK_SPACE", "WORK_GROUP"]
    if node_type not in valid_types:
        return f"Error: node_type must be one of {valid_types}"
    
    try:
        url = f"{LINSHARE_ADMIN_URL}/{user_uuid}/shared_space_nodes"
        
        # Build request body
        payload = {
            "name": name,
            "nodeType": node_type
        }
        
        if parent_uuid:
            payload["parentUuid"] = parent_uuid
        
        if description:
            payload["description"] = description
        
        response = requests.post(
            url,
            json=payload,
            auth=HTTPBasicAuth(LINSHARE_USERNAME, LINSHARE_PASSWORD),
            headers={
                'accept': 'application/json',
                'Content-Type': 'application/json'
            },
            timeout=10
        )
        response.raise_for_status()
        
        space_data = response.json()
        
        result = f"""Shared Space Created Successfully:
- Name: {space_data.get('name')}
- UUID: {space_data.get('uuid')}
- Type: {space_data.get('nodeType')}
- Creation Date: {space_data.get('creationDate')}
- Description: {space_data.get('description', 'N/A')}
"""
        if parent_uuid:
            result += f"- Parent UUID: {space_data.get('parentUuid')}\n"
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error creating shared space: {str(e)}")
        if hasattr(e.response, 'text'):
            return f"Error creating shared space: {str(e)}\nResponse: {e.response.text}"
        return f"Error creating shared space: {str(e)}"

@mcp.tool()
def list_shared_space_nodes(user_uuid: str, with_role: bool = False) -> str:
    """List all shared space nodes for a user.
    
    Args:
        user_uuid: The user's UUID (e.g., 7c2d2fdb-9063-46e3-8041-363ae9910d01)
        with_role: Whether to include role information (default: False)
    
    Returns:
        JSON string with list of shared space nodes
    """
    logger.info(f"Tool called: list_shared_space_nodes({user_uuid}, {with_role})")
    
    if not LINSHARE_ADMIN_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    
    if not LINSHARE_USERNAME or not LINSHARE_PASSWORD:
        return "Error: LinShare credentials not configured."
    
    try:
        url = f"{LINSHARE_ADMIN_URL}/{user_uuid}/shared_space_nodes"
        params = {'withRole': str(with_role).lower()}
        
        response = requests.get(
            url,
            params=params,
            auth=HTTPBasicAuth(LINSHARE_USERNAME, LINSHARE_PASSWORD),
            headers={'accept': 'application/json'},
            timeout=10
        )
        response.raise_for_status()
        
        nodes = response.json()
        
        if not nodes:
            return "No shared space nodes found for this user."
        
        # Format the response nicely
        result = f"Shared Space Nodes ({len(nodes)} total):\n\n"
        
        for i, node in enumerate(nodes, 1):
            result += f"{i}. {node.get('name', 'Unnamed')}\n"
            result += f"   - UUID: {node.get('uuid')}\n"
            result += f"   - Type: {node.get('nodeType')}\n"
            result += f"   - Creation Date: {node.get('creationDate')}\n"
            result += f"   - Modification Date: {node.get('modificationDate')}\n"
            if with_role and 'role' in node:
                result += f"   - Role: {node.get('role', {}).get('name')}\n"
            result += "\n"
        
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error fetching shared space nodes: {str(e)}")
        return f"Error fetching shared space nodes: {str(e)}"

@mcp.tool()
def list_available_workspace_roles() -> str:
    """List available workspace roles with their UUIDs.
    
    Returns:
        List of workspace roles with UUIDs and descriptions
    """
    logger.info("Tool called: list_available_workspace_roles()")
    
    try:
        workspace_roles = COMMON_ROLES.get('WORK_SPACE', {})
        
        if not workspace_roles:
            return "Error: No workspace roles found in COMMON_ROLES."
        
        result = "Available Workspace Roles:\n\n"
        
        # Use .get() to safely access keys
        admin_uuid = workspace_roles.get('WORK_SPACE_ADMIN')
        writer_uuid = workspace_roles.get('WORK_SPACE_WRITER')
        reader_uuid = workspace_roles.get('WORK_SPACE_READER')
        
        if admin_uuid:
            result += "1. 👑 WORK_SPACE_ADMIN\n"
            result += f"   UUID: {admin_uuid}\n"
            result += "   Description: Full control - can manage members and settings\n\n"
        
        if writer_uuid:
            result += "2. ✍️ WORK_SPACE_WRITER\n"
            result += f"   UUID: {writer_uuid}\n"
            result += "   Description: Can create, edit, and delete content\n\n"
        
        if reader_uuid:
            result += "3. 👁️ WORK_SPACE_READER\n"
            result += f"   UUID: {reader_uuid}\n"
            result += "   Description: Read-only access\n\n"
        
        if not (admin_uuid or writer_uuid or reader_uuid):
            return "Error: No valid workspace roles found."
        
        return result
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def list_user_shared_spaces(actor_uuid: str) -> str:
    """List all shared spaces (Workspaces, Drives) that a user is a member of.
    
    Args:
        actor_uuid: UUID of the user
    
    Returns:
        List of workspaces and drives the user belongs to with roles
    """
    logger.info(f"Tool called: list_user_shared_spaces({actor_uuid})")
    
    if not LINSHARE_ADMIN_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    if not LINSHARE_USERNAME or not LINSHARE_PASSWORD:
        return "Error: LinShare credentials not configured."
    
    try:
        url = f"{LINSHARE_ADMIN_URL}/{actor_uuid}/shared_space_members"
        
        response = requests.get(
            url,
            auth=HTTPBasicAuth(LINSHARE_USERNAME, LINSHARE_PASSWORD),
            headers={'accept': 'application/json'},
            timeout=30
        )
        response.raise_for_status()
        
        memberships = response.json()
        
        if not memberships:
            return "User is not a member of any shared spaces."
        
        # Separate by type (exclude workgroups)
        workspaces = [m for m in memberships if m.get('node', {}).get('nodeType') == 'WORK_SPACE']
        drives = [m for m in memberships if m.get('node', {}).get('nodeType') == 'DRIVE']
        
        result = f"Shared Spaces for User ({len(workspaces) + len(drives)} total):\n\n"
        
        if workspaces:
            result += f"📁 WORKSPACES ({len(workspaces)}):\n"
            for i, membership in enumerate(workspaces, 1):
                node = membership.get('node', {})
                role = membership.get('role', {})
                
                result += f"{i}. {node.get('name', 'Unnamed workspace')}\n"
                result += f"   UUID: {node.get('uuid', 'N/A')}\n"
                result += f"   Role: {role.get('name', 'N/A')}\n"
                result += f"   Membership UUID: {membership.get('uuid', 'N/A')}\n"
                
                if node.get('creationDate'):
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(node['creationDate'].replace('Z', '+00:00'))
                        result += f"   Created: {dt.strftime('%Y-%m-%d')}\n"
                    except:
                        pass
                
                result += "\n"
            result += "\n"
        
        if drives:
            result += f"💾 DRIVES ({len(drives)}):\n"
            for i, membership in enumerate(drives, 1):
                node = membership.get('node', {})
                role = membership.get('role', {})
                
                result += f"{i}. {node.get('name', 'Unnamed drive')}\n"
                result += f"   UUID: {node.get('uuid', 'N/A')}\n"
                result += f"   Role: {role.get('name', 'N/A')}\n"
                result += f"   Membership UUID: {membership.get('uuid', 'N/A')}\n"
                
                if node.get('parentUuid'):
                    result += f"   Parent: {node['parentUuid']}\n"
                
                result += "\n"
            result += "\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def add_workspace_member(
    actor_uuid: str,
    workspace_uuid: str,
    account_uuid: str,
    role_name: str,
    mail: str
) -> str:
    """Add a member to a workspace with a specific role.
    
    Available roles (must use exact names):
    - WORK_SPACE_ADMIN: Full control
    - WORK_SPACE_WRITER: Can create and edit
    - WORK_SPACE_READER: Read-only
    
    Supports both INTERNAL and GUEST account types.
    
    Args:
        actor_uuid: UUID of the actor performing the action
        workspace_uuid: UUID of the workspace
        account_uuid: UUID of the user to add (can be INTERNAL or GUEST)
        role_name: Role name (WORK_SPACE_ADMIN, WORK_SPACE_WRITER, or WORK_SPACE_READER)
        mail: Email address of the user to add
    
    Returns:
        Confirmation with member details
    """
    logger.info(f"Tool called: add_workspace_member({account_uuid}, role: {role_name})")
    
    if not LINSHARE_ADMIN_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    if not LINSHARE_USERNAME or not LINSHARE_PASSWORD:
        return "Error: LinShare credentials not configured."
    
    try:
        # Get role UUID
        role_uuid = get_role_uuid(role_name)
        
        if not role_uuid:
            return (f"❌ Role '{role_name}' not found.\n\n"
                   f"Available roles (use exact names):\n"
                   f"- WORK_SPACE_ADMIN\n"
                   f"- WORK_SPACE_WRITER\n"
                   f"- WORK_SPACE_READER")
        
        url = f"{LINSHARE_ADMIN_URL}/{actor_uuid}/shared_space_members"
        
        # Build request body
        payload = {
            "role": {
                "uuid": role_uuid
            },
            "user": {
                "uuid": account_uuid,
                "mail": mail
            },
            "node": {
                "uuid": workspace_uuid
            }
        }
        
        response = requests.post(
            url,
            json=payload,
            auth=HTTPBasicAuth(LINSHARE_USERNAME, LINSHARE_PASSWORD),
            headers={
                'accept': 'application/json',
                'Content-Type': 'application/json'
            },
            timeout=10
        )
        
        if response.status_code != 200:
            error_msg = f"Failed to add member: {response.status_code}\n"
            try:
                error_detail = response.json()
                error_msg += f"Error: {error_detail.get('message', response.text)}"
                if 'errCode' in error_detail:
                    error_msg += f"\nCode: {error_detail['errCode']}"
            except:
                error_msg += f"Response: {response.text}"
            return error_msg
            
        response.raise_for_status()
        member_data = response.json()
        
        result = f"""✅ Member Added Successfully:
- User Email: {mail}
- Role: {role_name}
- Workspace UUID: {workspace_uuid}
- Membership UUID: {member_data.get('uuid')}
"""
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error adding workspace member: {str(e)}")
        return f"Error adding workspace member: {str(e)}"



@mcp.tool()
def remove_workspace_member(
    actor_uuid: str,
    membership_uuid: str
) -> str:
    """Remove a member from a workspace.
    
    IMPORTANT: Use the membership UUID, not the user UUID!
    Get membership UUIDs from list_user_shared_spaces().
    
    Args:
        actor_uuid: UUID of the actor performing the action
        membership_uuid: UUID of the membership to remove
    
    Returns:
        Confirmation of removal
    """
    logger.info(f"Tool called: remove_workspace_member({membership_uuid})")
    
    if not LINSHARE_ADMIN_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    if not LINSHARE_USERNAME or not LINSHARE_PASSWORD:
        return "Error: LinShare credentials not configured."
    
    try:
        url = f"{LINSHARE_ADMIN_URL}/{actor_uuid}/shared_space_members/{membership_uuid}"
        
        response = requests.delete(
            url,
            auth=HTTPBasicAuth(LINSHARE_USERNAME, LINSHARE_PASSWORD),
            headers={
                'accept': 'application/json',
                'Content-Type': 'application/json'
            },
            timeout=30
        )
        
        if response.status_code not in [200, 204]:
            return f"Failed to remove member: {response.status_code}\n{response.text}"
        
        # Try to parse response (may be empty for 204)
        try:
            result = response.json()
            
            output = f"✅ Member removed from workspace!\n\n"
            
            if result.get('account'):
                account = result['account']
                output += f"Removed: {account.get('firstName', '')} {account.get('lastName', '')}\n"
                output += f"Email: {account.get('mail', 'N/A')}\n"
            
            if result.get('node'):
                output += f"From: {result['node'].get('name', 'N/A')}\n"
            
            return output
        except:
            return f"✅ Member removed from workspace!\n\nMembership UUID: {membership_uuid}"
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def show_exact_role_keys() -> str:
    """Show the exact keys in COMMON_ROLES."""
    result = "Exact COMMON_ROLES structure:\n\n"

    result += f"Top-level keys: {list(COMMON_ROLES.keys())}\n\n"

    for top_key in COMMON_ROLES.keys():
        result += f"Under '{top_key}':\n"
        if isinstance(COMMON_ROLES[top_key], dict):
            for sub_key in COMMON_ROLES[top_key].keys():
                result += f"  - '{sub_key}' (repr: {repr(sub_key)})\n"
                result += f"    Value: {COMMON_ROLES[top_key][sub_key]}\n"
        else:
            result += f"  Value: {COMMON_ROLES[top_key]}\n"
        result += "\n"

    return result
