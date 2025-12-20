import requests
import json
from ...app import mcp
from ...config import LINSHARE_USER_URL, LINSHARE_UPLOAD_DIR, COMMON_ROLES
from ...utils.logging import logger
from ...utils.auth import auth_manager
from ...utils.common import format_file_size, guess_mime_type, get_role_uuid

# ------------------------------------------------------------------------------
# USER WORKGROUP TOOLS (Using JWT Auth)
# ------------------------------------------------------------------------------

@mcp.tool()
def user_create_my_shared_space(
    name: str,
    node_type: str,
    description: str | None = None
) -> str:
    """Create a new workspace or workgroup as the logged-in user.
    
    Args:
        name: Name of the shared space
        node_type: Type of node - "WORK_SPACE" or "WORK_GROUP"
        description: Optional description
    
    Returns:
        Confirmation of creation
    """
    logger.info(f"Tool called: create_my_shared_space({name}, {node_type})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
    
    # Get auth header (this will raise error if not logged in)
    try:
        auth_header = auth_manager.get_auth_header()
    except ValueError as e:
        return f"Error: {str(e)}"
    
    # Validate node_type
    valid_types = ["WORK_SPACE", "WORK_GROUP"]
    if node_type not in valid_types:
        return f"Error: node_type must be one of {valid_types}"
    
    try:
        # We don't need user_uuid in URL for JWT auth, we use "me" or the extracted UUID
        # But LinShare API usually requires /linshare/webservice/rest/user/v2/shared_space_nodes
        # Let's check how the admin tool did it: /{user_uuid}/shared_space_nodes
        # For JWT, we should probably use the UUID from the token or "me" if supported, 
        # but LinShare often uses the UUID in the path even with JWT.
        # Let's use the UUID from the auth_manager if available.
        
        current_user = auth_manager.get_current_user()
        if not current_user:
             # Try to get it
             try:
                 # This is a bit circular if we call the tool, but we can call the API
                 # For now, let's assume we can get it or fail.
                 # Actually, let's just use the /documents endpoint which we know works with JWT?
                 # No, shared spaces are different.
                 # Let's try to fetch user info first if we don't have it.
                 pass
             except:
                 return "Error: Could not determine current user UUID. Please login again."
        
        user_uuid = current_user.get('uuid')
        if not user_uuid:
             return "Error: Current user UUID not found. Please login."

        url = f"{LINSHARE_USER_URL}/{user_uuid}/shared_space_nodes"
        
        # Build request body
        payload = {
            "name": name,
            "nodeType": node_type
        }
        
        if description:
            payload["description"] = description
        
        response = requests.post(
            url,
            json=payload,
            headers=auth_header,
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
        return result
        
    except requests.RequestException as e:
        logger.error(f"Error creating shared space: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
             return f"Error creating shared space: {str(e)}\nResponse: {e.response.text}"
        return f"Error creating shared space: {str(e)}"

@mcp.tool()
def user_list_my_shared_spaces() -> str:
    """List all shared spaces (Workspaces, Drives, Workgroups) the logged-in user belongs to.
    
    Returns:
        List of shared spaces with details.
    """
    logger.info("Tool called: list_my_shared_spaces()")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
    
    try:
        auth_header = auth_manager.get_auth_header()
        current_user = auth_manager.get_current_user()
        if not current_user or not current_user.get('uuid'):
            return "Error: Current user UUID not found. Please login."
        
        user_uuid = current_user['uuid']
        
        url = f"{LINSHARE_USER_URL}/{user_uuid}/shared_space_members"
        
        response = requests.get(
            url,
            headers=auth_header,
            timeout=30
        )
        response.raise_for_status()
        
        memberships = response.json()
        
        if not memberships:
            return "You are not a member of any shared spaces."
        
        # Separate by type
        workspaces = [m for m in memberships if m.get('node', {}).get('nodeType') == 'WORK_SPACE']
        drives = [m for m in memberships if m.get('node', {}).get('nodeType') == 'DRIVE']
        workgroups = [m for m in memberships if m.get('node', {}).get('nodeType') == 'WORK_GROUP']
        
        result = f"My Shared Spaces ({len(memberships)} total):\n\n"
        
        if workspaces:
            result += f"📁 WORKSPACES ({len(workspaces)}):\n"
            for i, membership in enumerate(workspaces, 1):
                node = membership.get('node', {})
                role = membership.get('role', {})
                result += f"{i}. {node.get('name', 'Unnamed')}\n"
                result += f"   UUID: {node.get('uuid')}\n"
                result += f"   Role: {role.get('name')}\n\n"
        
        if workgroups:
            result += f"👥 WORKGROUPS ({len(workgroups)}):\n"
            for i, membership in enumerate(workgroups, 1):
                node = membership.get('node', {})
                role = membership.get('role', {})
                result += f"{i}. {node.get('name', 'Unnamed')}\n"
                result += f"   UUID: {node.get('uuid')}\n"
                result += f"   Role: {role.get('name')}\n\n"

        if drives:
            result += f"💾 DRIVES ({len(drives)}):\n"
            for i, membership in enumerate(drives, 1):
                node = membership.get('node', {})
                result += f"{i}. {node.get('name', 'Unnamed')}\n"
                result += f"   UUID: {node.get('uuid')}\n\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def user_list_my_workgroup_entries(workgroup_uuid: str) -> str:
    """List files and folders in a specific workgroup/workspace the user has access to.
    
    Args:
        workgroup_uuid: UUID of the workgroup/workspace
    
    Returns:
        List of entries
    """
    logger.info(f"Tool called: list_my_workgroup_entries({workgroup_uuid})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
    
    try:
        auth_header = auth_manager.get_auth_header()
        current_user = auth_manager.get_current_user()
        if not current_user or not current_user.get('uuid'):
             return "Error: Current user UUID not found. Please login."
        
        user_uuid = current_user['uuid']
        
        url = f"{LINSHARE_USER_URL}/{user_uuid}/workgroups/{workgroup_uuid}/entries"
        
        response = requests.get(
            url,
            headers=auth_header,
            timeout=10
        )
        response.raise_for_status()
        
        entries = response.json()
        
        if not entries:
            return f"No entries found in workgroup {workgroup_uuid}."
        
        folders = [e for e in entries if e.get('type') == 'FOLDER']
        files = [e for e in entries if e.get('type') in ['DOCUMENT', 'DOCUMENT_REVISION']]
        
        result = f"Entries for {workgroup_uuid}\n"
        result += f"({len(entries)} total: {len(folders)} folders, {len(files)} files)\n\n"
        
        if folders:
            result += "📁 FOLDERS:\n"
            for i, folder in enumerate(folders, 1):
                result += f"{i}. {folder.get('name')}\n"
                result += f"   UUID: {folder.get('uuid')}\n"
        
        if files:
            result += "\n📄 FILES:\n"
            for i, file in enumerate(files, 1):
                result += f"{i}. {file.get('name')}\n"
                result += f"   UUID: {file.get('uuid')}\n"
                result += f"   Size: {format_file_size(file.get('size', 0))}\n"
                result += f"   Type: {file.get('mimeType', 'N/A')}\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def user_upload_file_to_my_workgroup(
    workgroup_uuid: str,
    filename: str,
    folder_uuid: str | None = None,
    description: str | None = None,
    async_upload: bool = False
) -> str:
    """Upload a file from the upload directory to a workgroup as the logged-in user.
    
    Args:
        workgroup_uuid: UUID of the target workgroup/workspace
        filename: Name of file in upload directory
        folder_uuid: Optional folder UUID
        description: Optional description
        async_upload: Upload asynchronously
    
    Returns:
        Upload confirmation
    """
    logger.info(f"Tool called: upload_file_to_my_workgroup({filename})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
    
    try:
        auth_header = auth_manager.get_auth_header()
        current_user = auth_manager.get_current_user()
        if not current_user or not current_user.get('uuid'):
             return "Error: Current user UUID not found. Please login."
        
        user_uuid = current_user['uuid']
        
        file_path = LINSHARE_UPLOAD_DIR / filename
        if not file_path.exists():
            return f"Error: File '{filename}' not found in upload directory."
            
        file_size = file_path.stat().st_size
        
        if folder_uuid:
            url = f"{LINSHARE_USER_URL}/{user_uuid}/workgroups/{workgroup_uuid}/folders/{folder_uuid}/entries"
        else:
            url = f"{LINSHARE_USER_URL}/{user_uuid}/workgroups/{workgroup_uuid}/entries"
            
        params = {'async': str(async_upload).lower()}
        
        with open(file_path, 'rb') as f:
            files = {'file': (filename, f, guess_mime_type(filename))}
            data = {
                'filesize': str(file_size),
                'filename': filename
            }
            if description:
                data['description'] = description
                
            # Merge auth header with other headers if needed, but requests handles dicts
            # We need to make sure we don't overwrite Content-Type for multipart
            # requests sets Content-Type automatically for files
            
            response = requests.post(
                url,
                params=params,
                files=files,
                data=data,
                headers=auth_header, # This contains Authorization: Bearer ...
                timeout=60
            )
            
        response.raise_for_status()
        result = response.json()
        
        return f"✅ File '{filename}' uploaded successfully to workgroup!"
        
    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def user_add_member_to_my_workspace(
    workspace_uuid: str,
    email: str,
    role: str
) -> str:
    """Add a member to a workspace where the logged-in user has admin rights.
    
    Args:
        workspace_uuid: UUID of the workspace
        email: Email of the user to add
        role: Role name (WORK_SPACE_ADMIN, WORK_SPACE_WRITER, WORK_SPACE_READER)
    
    Returns:
        Confirmation
    """
    logger.info(f"Tool called: add_member_to_my_workspace({email}, {role})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        auth_header = auth_manager.get_auth_header()
        current_user = auth_manager.get_current_user()
        if not current_user or not current_user.get('uuid'):
             return "Error: Current user UUID not found. Please login."
        
        user_uuid = current_user['uuid']
        
        role_uuid = get_role_uuid(role)
        if not role_uuid:
            return f"Error: Role '{role}' not found."
            
        # Need to find the user UUID for the email first
        # We can use the autocomplete/search endpoint or just try to add if we know the UUID
        # But here we only have email.
        # Let's try to search for the user.
        search_url = f"{LINSHARE_USER_URL}/users"
        search_params = {'pattern': email}
        
        search_resp = requests.get(search_url, params=search_params, headers=auth_header)
        search_resp.raise_for_status()
        search_results = search_resp.json()
        
        target_user_uuid = None
        for u in search_results:
            if u.get('mail') == email:
                target_user_uuid = u.get('uuid')
                break
        
        if not target_user_uuid:
            return f"Error: User with email '{email}' not found."
            
        url = f"{LINSHARE_USER_URL}/{user_uuid}/shared_space_members"
        
        payload = {
            "role": {"uuid": role_uuid},
            "user": {"uuid": target_user_uuid, "mail": email},
            "node": {"uuid": workspace_uuid}
        }
        
        response = requests.post(
            url,
            json=payload,
            headers=auth_header,
            timeout=10
        )
        response.raise_for_status()
        
        return f"✅ Member {email} added successfully with role {role}."
        
    except Exception as e:
        logger.error(f"Error adding member: {e}")
        return f"Error: {str(e)}"

@mcp.tool()
def user_remove_member_from_my_workspace(membership_uuid: str) -> str:
    """Remove a member from a workspace where the logged-in user has admin rights.
    
    Args:
        membership_uuid: UUID of the membership to remove
    
    Returns:
        Confirmation
    """
    logger.info(f"Tool called: remove_member_from_my_workspace({membership_uuid})")
    
    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
        
    try:
        auth_header = auth_manager.get_auth_header()
        current_user = auth_manager.get_current_user()
        if not current_user or not current_user.get('uuid'):
             return "Error: Current user UUID not found. Please login."
        
        user_uuid = current_user['uuid']
        
        url = f"{LINSHARE_USER_URL}/{user_uuid}/shared_space_members/{membership_uuid}"
        
        response = requests.delete(
            url,
            headers=auth_header,
            timeout=10
        )
        
        if response.status_code in [200, 204]:
            return "✅ Member removed successfully."
        else:
            return f"Error removing member: {response.status_code} - {response.text}"
            
    except Exception as e:
        logger.error(f"Error removing member: {e}")
        return f"Error: {str(e)}"
