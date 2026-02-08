# LinShare MCP Testing Guide - Scenarios & Prompts

This guide provides curated prompts to test the AI Assistant's ability to use LinShare tools correctly. It is divided into **User Mode** and **Admin Mode**.

## 👤 User Mode (Personal Space)

Use these prompts when the Assistant is configured in **User Mode** (Admin toggle OFF).

### 1. Connection & Session
*   **Prompt**: "Check my LinShare connection and tell me who I am."
    *   **Goal**: Verify `user_check_config` and `user_get_current_user_info`.
*   **Prompt**: "Am I logged in to LinShare?"
    *   **Goal**: Verify session detection.

### 2. File Management
*   **Prompt**: "List the documents in my personal space."
    *   **Goal**: Verify `list_my_documents`.
*   **Prompt**: "Search for any files related to 'report' or 'presentation'."
    *   **Goal**: Verify `user_search_my_documents` with patterns.
*   **Prompt**: "What is the size and creation date of my file 'upload.txt'?"
    *   **Goal**: Verify data extraction from file lists.

### 3. Collaboration & Sharing
*   **Prompt**: "Share the document 'Project.pdf' with amy.wolsh@linshare.org."
    *   **Goal**: Verify `share_my_documents`.
*   **Prompt**: "Create a guest account for partner@external.com that expires in 10 days."
    *   **Goal**: Verify `user_create_guest` with expiration.
*   **Prompt**: "Show me my audit logs for the last 24 hours."
    *   **Goal**: Verify `user_search_audit` with date filtering.

---

## 🛡️ Admin Mode (Delegation & Governance)

Use these prompts when the Assistant is configured in **Admin Mode** (Admin toggle ON).

### 1. User Audit & Masquerading
*   **Prompt**: "List the documents for the user with UUID `b428d01d-55e1-4564-8178-5776d6537dbd`."
    *   **Goal**: Verify `list_user_documents` (Admin tool).
*   **Prompt**: "Search audit logs for user john.doe@linshare.org from January 1st to today."
    *   **Goal**: Verify `search_user_audit_logs` with date normalization.

### 2. Workgroup Management
*   **Prompt**: "List all my shared spaces and workgroups."
    *   **Goal**: Verify `list_user_shared_spaces`.
*   **Prompt**: "Create a new workgroup called 'Legal Review 2026'."
    *   **Goal**: Verify `create_shared_space`.
*   **Prompt**: "Add user `alice@linshare.org` to the 'Marketing' workgroup as a READER."
    *   **Goal**: Verify `add_workspace_member` with specific roles.

---

## 🚀 Advanced Chained Scenarios

Tests the AI's ability to coordinate multiple tools.

*   **Prompt**: "Find the largest PDF in my space and share it with amy.wolsh@linshare.org."
    *   **Scenario**: `list_my_documents` -> Analyze sizes -> `share_my_documents`.
*   **Prompt**: "Check if 'sensitive_data.zip' has been shared with anyone, and if so, revoke all shares."
    *   **Scenario**: `user_search_my_documents` -> `get_user_document_shares` -> `user_delete_share` (repeatedly).
*   **Prompt**: "I need to audit John Doe's activity. Find his workgroups, then list the files in the most recently joined one."
    *   **Scenario**: `user_search_users` -> `list_user_shared_spaces` -> `list_workgroup_entries`.

---

## 🤖 Automated Testing

You can run these tests programmatically using the provided test runner:

```bash
python scripts/auto_test_prompts.py
```

Check the `scripts/` directory for configuration and reporting options.
