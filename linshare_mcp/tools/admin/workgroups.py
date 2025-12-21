import requests
import json
from datetime import datetime
from ...app import mcp
from ...config import LINSHARE_ADMIN_URL as LINSHARE_BASE_URL, LINSHARE_UPLOAD_DIR, COMMON_ROLES
from ...utils.logging import logger
from ...utils.common import format_file_size, guess_mime_type, get_role_uuid
from ...utils.auth import auth_manager

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
    
    if not LINSHARE_BASE_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    
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
            url = f"{LINSHARE_BASE_URL}/{actor_uuid}/workgroups/{workgroup_uuid}/folders/{folder_uuid}/entries"
        else:
            url = f"{LINSHARE_BASE_URL}/{actor_uuid}/workgroups/{workgroup_uuid}/entries"
        
        # Query parameters
        params = {
            'async': str(async_upload).lower(),
            'strict': str(strict).lower()
        }
        
        # Prepare multipart form data
        with open(file_path, 'rb') as f:
            files = {
                'file': (filename, f, guess_mime_type(filename))
            }
            
            # Required and optional form fields
            data = {
                'filesize': str(file_size),
                'filename': filename,
            }
            
            if description:
                data['description'] = description
            
            admin_auth = auth_manager.get_admin_auth()
            
            response = requests.post(
                url,
                params=params,
                files=files,
                data=data,
                auth=admin_auth,
                headers={
                    'accept': 'application/json',
                },
                timeout=60
            )
        
        if response.status_code != 200:
            error_msg = f"Upload failed with status {response.status_code}\n"
            try:
                error_detail = response.json()
                error_msg += f"Error: {error_detail.get('message', response.text)}"
            except:
                error_msg += f"Response: {response.text}"
            return error_msg
        
        result = response.json()
        
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
                dt = datetime.fromisoformat(result['creationDate'].replace('Z', '+00:00'))
                output += f"Uploaded: {dt.strftime('%Y-%m-%d %H:%M:%S')}\n"
            except:
                pass
        
        return output
        
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
    
    if not LINSHARE_BASE_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    
    try:
        url = f"{LINSHARE_BASE_URL}/{actor_uuid}/workgroups/{workgroup_uuid}/entries"
        admin_auth = auth_manager.get_admin_auth()
        
        response = requests.get(
            url,
            auth=admin_auth,
            headers={'accept': 'application/json'},
            timeout=10
        )
        response.raise_for_status()
        
        entries = response.json()
        
        if not entries:
            return f"No entries found in workgroup {workgroup_uuid}."
        
        folders = [e for e in entries if e.get('type') == 'FOLDER']
        files = [e for e in entries if e.get('type') in ['DOCUMENT', 'DOCUMENT_REVISION']]
        
        result = f"Workgroup Entries for {workgroup_uuid}\n"
        result += f"({len(entries)} total: {len(folders)} folders, {len(files)} files)\n\n"
        
        if folders:
            result += "📁 FOLDERS:\n"
            for i, folder in enumerate(folders, 1):
                result += f"{i}. {folder.get('name', 'Unnamed folder')}"
                result += f" | UUID: {folder.get('uuid', 'N/A')}"
                if folder.get('modificationDate'):
                    try:
                        dt = datetime.fromisoformat(folder['modificationDate'].replace('Z', '+00:00'))
                        result += f" | Modified: {dt.strftime('%Y-%m-%d %H:%M')}"
                    except:
                        pass
                result += "\n"
            result += "\n"
        
        if files:
            result += "📄 FILES:\n"
            for i, file in enumerate(files, 1):
                result += f"{i}. {file.get('name', 'Unnamed file')}"
                size = file.get('size', 0)
                if size:
                    result += f" | Size: {format_file_size(size)}"
                result += f"\n   UUID: {file.get('uuid', 'N/A')}"
                if file.get('lastAuthor'):
                    author = file['lastAuthor']
                    author_name = f"{author.get('firstName', '')} {author.get('lastName', '')}".strip()
                    if author_name:
                        result += f"\n   Author: {author_name}"
                result += "\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error listing workgroup entries: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def list_shared_space_nodes(user_uuid: str, with_role: bool = False) -> str:
    """List all shared space nodes for a user.
    
    Args:
        user_uuid: The user's UUID
        with_role: Whether to include role information (default: False)
    
    Returns:
        Formatted list of shared space nodes
    """
    logger.info(f"Tool called: list_shared_space_nodes({user_uuid}, {with_role})")
    
    if not LINSHARE_BASE_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    
    try:
        url = f"{LINSHARE_BASE_URL}/{user_uuid}/shared_space_nodes"
        params = {'withRole': str(with_role).lower()}
        admin_auth = auth_manager.get_admin_auth()
        
        response = requests.get(
            url,
            params=params,
            auth=admin_auth,
            headers={'accept': 'application/json'},
            timeout=10
        )
        response.raise_for_status()
        
        nodes = response.json()
        
        if not nodes:
            return "No shared space nodes found for this user."
        
        result = f"Shared Space Nodes ({len(nodes)} total):\n\n"
        
        for i, node in enumerate(nodes, 1):
            result += f"{i}. {node.get('name', 'Unnamed')}\n"
            result += f"   - UUID: {node.get('uuid')}\n"
            result += f"   - Type: {node.get('nodeType')}\n"
            if with_role and 'role' in node:
                result += f"   - Role: {node.get('role', {}).get('name')}\n"
            result += "\n"
        
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
    
    if not LINSHARE_BASE_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    
    try:
        url = f"{LINSHARE_BASE_URL}/{actor_uuid}/shared_space_members"
        admin_auth = auth_manager.get_admin_auth()
        
        response = requests.get(
            url,
            auth=admin_auth,
            headers={'accept': 'application/json'},
            timeout=30
        )
        response.raise_for_status()
        
        memberships = response.json()
        
        if not memberships:
            return "User is not a member of any shared spaces."
        
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
                result += f"   Membership UUID: {membership.get('uuid', 'N/A')}\n\n"
        
        if drives:
            result += f"💾 DRIVES ({len(drives)}):\n"
            for i, membership in enumerate(drives, 1):
                node = membership.get('node', {})
                role = membership.get('role', {})
                result += f"{i}. {node.get('name', 'Unnamed drive')}\n"
                result += f"   UUID: {node.get('uuid', 'N/A')}\n"
                result += f"   Role: {role.get('name', 'N/A')}\n"
                result += f"   Membership UUID: {membership.get('uuid', 'N/A')}\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def create_shared_space(
    user_uuid: str,
    name: str,
    node_type: str,
    parent_uuid: str = None,
    description: str = None
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
    
    if not LINSHARE_BASE_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    
    valid_types = ["WORK_SPACE", "WORK_GROUP"]
    if node_type not in valid_types:
        return f"Error: node_type must be one of {valid_types}"
    
    try:
        url = f"{LINSHARE_BASE_URL}/{user_uuid}/shared_space_nodes"
        payload = {"name": name, "nodeType": node_type}
        if parent_uuid: payload["parentUuid"] = parent_uuid
        if description: payload["description"] = description
        
        admin_auth = auth_manager.get_admin_auth()
        
        response = requests.post(
            url,
            json=payload,
            auth=admin_auth,
            headers={'accept': 'application/json', 'Content-Type': 'application/json'},
            timeout=10
        )
        response.raise_for_status()
        space_data = response.json()
        
        result = f"Shared Space Created Successfully:\n- Name: {space_data.get('name')}\n- UUID: {space_data.get('uuid')}\n- Type: {space_data.get('nodeType')}\n"
        return result
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {str(e)}"

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
        for role, uuid in workspace_roles.items():
            result += f"- {role}: {uuid}\n"
        return result
    except Exception as e:
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
    
    Args:
        actor_uuid: UUID of the actor performing the action
        workspace_uuid: UUID of the workspace
        account_uuid: UUID of the user to add
        role_name: Role name (e.g. WORK_SPACE_ADMIN, WORK_SPACE_WRITER, or WORK_SPACE_READER)
        mail: Email address of the user to add
    
    Returns:
        Confirmation with member details
    """
    logger.info(f"Tool called: add_workspace_member({account_uuid}, role: {role_name})")
    
    if not LINSHARE_BASE_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    
    try:
        role_uuid = get_role_uuid(role_name)
        if not role_uuid: return f"❌ Role '{role_name}' not found."
        
        # Get workspace details
        workspace_url = f"{LINSHARE_BASE_URL}/{actor_uuid}/shared_spaces/{workspace_uuid}"
        admin_auth = auth_manager.get_admin_auth()
        ws_res = requests.get(workspace_url, auth=admin_auth, headers={'accept': 'application/json'}, timeout=30)
        if ws_res.status_code != 200: return f"Error fetching workspace: {ws_res.status_code}"
        ws_data = ws_res.json()
        
        # Get account details
        acc_url = f"{LINSHARE_BASE_URL}/users/{mail}"
        # admin_auth already defined above
        acc_res = requests.get(acc_url, auth=admin_auth, headers={'accept': 'application/json'}, timeout=30)
        if acc_res.status_code != 200: return f"Error fetching account: {acc_res.status_code}"
        acc_data = acc_res.json()
        
        current_time = datetime.utcnow().isoformat() + "Z"
        payload = {
            "node": {"uuid": workspace_uuid, "name": ws_data.get('name', ''), "parentUuid": ws_data.get('parentUuid'), "nodeType": ws_data.get('nodeType', 'WORK_SPACE'), "domainUuid": ws_data.get('domainUuid', '')},
            "role": {"uuid": role_uuid, "name": role_name.upper(), "type": "WORK_SPACE"},
            "account": {"uuid": account_uuid, "name": f"{acc_data.get('firstName', '')} {acc_data.get('lastName', '')}".strip(), "firstName": acc_data.get('firstName', ''), "lastName": acc_data.get('lastName', ''), "mail": acc_data.get('mail', ''), "accountType": acc_data.get('accountType', 'INTERNAL')},
            "creationDate": current_time, "modificationDate": current_time, "nested": True, "type": "WORK_SPACE"
        }
        
        url = f"{LINSHARE_BASE_URL}/{actor_uuid}/shared_space_members"
        response = requests.post(
            url,
            auth=admin_auth,
            headers={'accept': 'application/json', 'Content-Type': 'application/json'},
            data=json.dumps(payload),
            timeout=30
        )
        
        if response.status_code not in [200, 201]: return f"Failed to add member: {response.status_code}\n{response.text}"
        
        result = response.json()
        return f"✅ Member {mail} added successfully to workspace {workspace_uuid}."
        
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def remove_workspace_member(
    actor_uuid: str,
    membership_uuid: str
) -> str:
    """Remove a member from a workspace using membership UUID.
    
    Args:
        actor_uuid: UUID of the actor performing the action
        membership_uuid: UUID of the membership to remove
    """
    logger.info(f"Tool called: remove_workspace_member({membership_uuid})")
    
    if not LINSHARE_BASE_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    
    try:
        url = f"{LINSHARE_BASE_URL}/{actor_uuid}/shared_space_members/{membership_uuid}"
        admin_auth = auth_manager.get_admin_auth()
        response = requests.delete(url, auth=admin_auth, timeout=30)
        if response.status_code not in [200, 204]: return f"Failed to remove member: {response.status_code}"
        return f"✅ Member removed successfully (Membership UUID: {membership_uuid})."
    except Exception as e:
        return f"Error: {str(e)}"

@mcp.tool()
def add_document_to_workgroup(
    user_uuid: str,
    workgroup_uuid: str,
    document_url: str,
    file_name: str,
    async_upload: bool = False,
    strict: bool = False
) -> str:
    """Add a document to a LinShare workgroup from a URL.
    
    Args:
        user_uuid: The user's UUID
        workgroup_uuid: The workgroup UUID
        document_url: URL of the document
        file_name: Name of the file
        async_upload: Enable async processing (default: False)
        strict: Raise error if file exists (default: False)
    """
    logger.info(f"Tool called: add_document_to_workgroup({user_uuid}, {workgroup_uuid}, {file_name})")
    
    if not LINSHARE_BASE_URL:
        return "Error: LINSHARE_ADMIN_URL not configured."
    
    try:
        url = f"{LINSHARE_BASE_URL}/{user_uuid}/workgroups/{workgroup_uuid}/entries/url"
        params = {'async': str(async_upload).lower(), 'strict': str(strict).lower()}
        payload = {"url": document_url, "fileName": file_name}
        
        admin_auth = auth_manager.get_admin_auth()
        
        response = requests.post(
            url,
            params=params,
            json=payload,
            auth=admin_auth,
            headers={'accept': 'application/json', 'Content-Type': 'application/json'},
            timeout=30
        )
        response.raise_for_status()
        doc_data = response.json()
        return f"Document Added Successfully:\n- Name: {doc_data.get('name')}\n- UUID: {doc_data.get('uuid')}\n"
    except Exception as e:
        return f"Error adding document: {str(e)}"
