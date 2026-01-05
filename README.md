# LinShare MCP Server

This is a Model Context Protocol (MCP) server for **LinShare**, an open-source secure file sharing application. It allows AI assistants (like Claude) to interact with a LinShare instance to manage files, shares, guests, and workgroups on behalf of a user or an administrator.

## 🚀 Capabilities

- **User Operations (My Space)**: List, upload, delete, and share personal documents.
- **Guest Management**: Create, list, and delete guest accounts (including restricted contacts).
- **Workgroup Management**: Upload files to permissions-based workgroups.
- **Audit Logs**: Search and filter user activity logs and document history.
- **Administration**: Manage workgroup members, shared spaces, and perform actions on behalf of other users (User Masquerading).

## 🔌 Usage Modes

The LinShare MCP server can be used in two different networking modes, which affects how files are uploaded:

### 1. Local (STDIN) Mode
Use this mode when the MCP server and the client (e.g., Claude Desktop) are running on the **same machine**.
- **Upload Tool**: `upload_file_from_local_directory`
- **How it works**: The server directly reads files from a local directory (configured via `LINSHARE_UPLOAD_DIR`).
- **Best for**: Desktop usage where the AI has access to your local files.

### 2. Remote (SSE) Mode
Use this mode when the MCP server is hosted **remotely** (e.g., in a Docker container or a cloud server) and the client interacts via Server-Sent Events.
- **Upload Tools**: `user_remote_upload_from_url` or `user_remote_upload_by_chunks`
- **How it works**: Since the server cannot access the client's local disk, files are either fetched from a public URL or sent in base64-encoded chunks over the MCP protocol.
- **Best for**: Web-based AI assistants or distributed setups.

## 🔐 Authentication

The server supports two modes of authentication, configured via environment variables.

### 1. User Authentication (JWT)
Used for tools that act as the logged-in user (Personal Space, My Shares, etc.).
- **Environment Variables**:
    - `LINSHARE_USER_URL`: The base URL for the User API (e.g., `https://user.linshare.org/linshare/webservice/rest/user/v5`)
    - `LINSHARE_JWT_TOKEN`: (Optional) Pre-configured JWT token.

If `LINSHARE_JWT_TOKEN` is not set, you can use the `user_login_user` tool to authenticate dynamically.

### 2. Admin Authentication (Service Account)
Used for administrative tools and delegation (acting on behalf of others).
- **Environment Variables**:
    - `LINSHARE_ADMIN_URL`: The base URL for the Admin API (e.g., `https://admin.linshare.org/linshare/webservice/rest/service`)
    - `LINSHARE_BASIC_AUTH_TOKEN`: The Base64 encoded `username:password` for the service account.

---

## 🛠️ Tools Reference

### 👤 User Tools (Personal Space)

These tools use the **User API** and require JWT authentication.

#### Authentication
| Tool | Description | Example Prompt |
|------|-------------|----------------|
| `user_login_user` | Log in to LinShare to get a session. | "Log me in as `john.doe@example.com` with password `secret`" |
| `user_logout_user` | Log out and clear the session. | "Log out of LinShare" |
| `user_get_current_user_info` | Get details about the current user. | "Who am I logged in as?" |
| `user_check_config` | Check API URLs and Auth status. | "Check my LinShare connection status" |

#### My Documents
| Tool | Description | Example Prompt |
|------|-------------|----------------|
| `list_my_documents` | List all files in your personal space. | "Show me my documents" |
| `upload_file_from_local_directory` | Upload a file from the server's local directory (STDIN mode). | "Upload `report.pdf` to my documents" |
| `user_remote_upload_from_url` | Upload a file to LinShare from a public URL (SSE/Remote mode). | "Fetch `https://.../logo.png` and save as `logo.png`" |
| `user_remote_upload_by_chunks` | Send a local file in chunks (SSE/Remote mode). | "Upload the file I just provided in chunks" |
| `user_delete_document` | Delete a document by UUID. | "Delete the document `1234-5678`" |
| `get_user_document_audit` | View activity history for a file. | "Who downloaded my file `contracts.pdf`?" |

#### Sharing
| Tool | Description | Example Prompt |
|------|-------------|----------------|
| `share_my_documents` | Share documents with emails or contacts. | "Share `report.pdf` with `jane@example.com`" |
| `get_user_document_shares` | See who a document is shared with. | "Is `budget.xlsx` shared with anyone?" |
| `user_delete_share` | Revoke a share. | "Stop sharing the file with `jane@example.com`" |
| `user_list_my_received_shares` | List files shared with you. | "What files have been shared with me?" |
| `user_copy_received_share_to_my_space` | Copy a shared file to your space. | "Save the shared `invoice.pdf` to my documents" |

#### Guests & Contacts
| Tool | Description | Example Prompt |
|------|-------------|----------------|
| `list_guests` | List your guest accounts. | "Show me my guest accounts" |
| `user_create_guest` | Create a guest with optional restrictions. | "Create a guest for `partner@ext.com` valid for 7 days" |
| `user_delete_guest` | Delete a guest account. | "Remove the guest `partner@ext.com`" |
| `user_list_contact_lists` | List your personal contact lists. | "List my contact lists" |
| `user_search_users` | Search for internal users. | "Find user with email `alice@company.com`" |

#### Activity Logs
| Tool | Description | Example Prompt |
|------|-------------|----------------|
| `user_search_audit` | Search your event logs (uploads, shares, etc.). | "What did I do yesterday?" or "Show my recent shares" |

---

### 🛡️ Admin / Workgroup Tools

These tools use the **Admin API** and require Service Account authentication.

#### Workgroups & Shared Spaces
| Tool | Description | Example Prompt |
|------|-------------|----------------|
| `create_shared_space` | Create a Workspace or Workgroup. | "Create a new Workgroup named 'Project Alpha'" |
| `list_user_shared_spaces` | List Workgroups a user belongs to. | "What workgroups is `bob@company.com` in?" |
| `list_workgroup_entries` | List files in a Workgroup. | "List files in the 'Marketing' workgroup" |
| `add_workspace_member` | Add a user to a Workgroup. | "Add `alice@company.com` to 'Project Alpha' as Admin" |
| `upload_file_to_workgroup` | Upload file to a Workgroup. | "Upload `specs.pdf` to the 'Engineering' workgroup" |

#### User Management (Delegation)
| Tool | Description | Example Prompt |
|------|-------------|----------------|
| `list_user_documents` | Admin listing of a user's files. | "List documents for user `user_uuid`" |
| `share_documents` | Share on behalf of a user. | "Share `doc_uuid` on behalf of `user_uuid`" |
| `search_user_audit_logs` | Search audit logs for any user. | "Show audit logs for user `bad_actor`" |
| `get_user_domain` | Get domain info for a user email. | "Get the domain UUID for `ceo@company.com`" |

---

## 📦 Installation & Configuration

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   Create a `.env` file or set environment variables:
   ```bash
    LINSHARE_USER_URL=https://user.linshare.org/...
    LINSHARE_ADMIN_URL=https://admin.linshare.org/...
    LINSHARE_JWT_TOKEN=...           # Optional: persistent user session
    LINSHARE_UPLOAD_DIR=/tmp/uploads # Optional: directory for file reassembly
    ```

3. **Run Server**:
   ```bash
   python -m linshare_mcp.main
   ```
