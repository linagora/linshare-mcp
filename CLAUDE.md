# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repo contains two coordinated Python apps:

1. **`linshare_mcp/`** — An MCP (Model Context Protocol) server built on `FastMCP` that exposes LinShare (open-source secure file sharing) operations as tools for AI assistants.
2. **`linshare-chat-client/`** — A Chainlit web chat client (LangChain + multi-LLM) that connects to the MCP server over SSE to provide a user-facing assistant.

The two are independent processes that talk over MCP (stdio or SSE).

## Common Commands

All commands assume the project root (`/home/walidboudiche/working/linshare-mcp`) unless noted. Use `uv` if available; otherwise fall back to plain `python`/`pip`.

### Install
```bash
# Editable install is required — without it, running the module from Claude Desktop
# fails with ModuleNotFoundError: No module named 'linshare_mcp'.
uv venv && source .venv/bin/activate
pip install -e .
```

### Run the MCP server
```bash
# STDIO transport (for Claude Desktop / local integrations)
python -m linshare_mcp.main

# SSE transport (for the chat client or remote use); default port 8000
python -m linshare_mcp.main --transport sse --host 0.0.0.0 --port 8000

# Restrict the loaded tool surface — affects which modules are imported in app.py
python -m linshare_mcp.main --mode user   # personal-space tools only (JWT auth)
python -m linshare_mcp.main --mode admin  # delegation/admin tools only (Basic auth)
python -m linshare_mcp.main --mode all    # default

# The --mode flag is also read from LINSHARE_MCP_MODE before the CLI parses,
# because tool registration happens at import time (see "Architecture" below).
```

### Run the chat client
```bash
cd linshare-chat-client
pip install -r requirements.txt
chainlit run chat_client.py -w   # default http://localhost:8000
```

### Tests
```bash
# Whole suite (pytest.ini sets testpaths=tests, asyncio_mode=auto)
uv run pytest tests/ -v

# Run by marker (markers: unit, integration, e2e — registered in conftest.py)
uv run pytest -m unit -v
uv run pytest -m integration -v   # needs live LinShare + env vars

# Single test
uv run pytest tests/unit/test_user_tools.py::TestClassName::test_name -v

# Coverage
uv run pytest --cov=linshare_mcp --cov-report=term-missing
```

Integration and e2e tests require `LINSHARE_USER_URL`, `LINSHARE_ADMIN_URL`, and credentials in `.env` — they will hit a real LinShare instance.

### Useful scripts (in `scripts/`)
- `verify_setup.py` — sanity-check the environment/install.
- `check_tools.py` — JSON-RPC ping into the stdio server to enumerate registered tools.
- `auto_test_prompts.py` — LLM-driven prompt → tool-selection assertions (needs `GOOGLE_API_KEY`).

## Architecture

### Tool registration is import-driven and mode-gated
`linshare_mcp/app.py` instantiates a single global `FastMCP` named `linshare-mcp-server`. Every tool module decorates functions with `@mcp.tool()` at import time, so **a tool only exists if its module is imported**. `linshare_mcp/main.py` decides which modules to import based on `MODE` (resolved from `--mode` or `LINSHARE_MCP_MODE` *before* `from .app import mcp`):

- `user`/`all` → imports `tools/user/*` (auth, myspace, users, files, received_shares, guests, audit, contact_lists)
- `admin`/`all` → imports `tools/admin/*` (workgroups, users, myspace, audit)
- Always loaded: `tools/files.py` (common upload-dir helpers) and `resources/files.py` (`file://upload/{filename}` MCP resource).

When adding a new tool, place it in the right `tools/{user,admin}/` subfolder and add the `from .tools.{user,admin} import <module>` line in `main.py`'s mode branch — there is no auto-discovery.

### Two authentication paths, unified via `AuthManager`
`linshare_mcp/utils/auth.py` exposes a singleton `auth_manager` and a `request_auth` `ContextVar`. There are two LinShare APIs in play with different auth:

- **User API** (`LINSHARE_USER_URL`, e.g. `.../webservice/rest/user/v5`) — JWT Bearer auth, used by all `tools/user/*` tools. Token comes from (in priority order): the per-request `request_auth` context, then `auth_manager.token` (loaded from `LINSHARE_JWT_TOKEN` env or set via `user_login_user` / `user_oidc_setup`).
- **Admin / Delegation API** (`LINSHARE_ADMIN_URL`, e.g. `.../webservice/rest/delegation/v2`) — HTTP Basic auth from `LINSHARE_USERNAME`/`LINSHARE_PASSWORD` (or per-request context), used by `tools/admin/*` tools.

`config.py` will *infer* one URL from the other (`/user/v5` ⇄ `/delegation/v2`) if only one is set; setting `LINSHARE_BASE_URL` overrides both.

### SSE auth middleware sets per-request credentials
In SSE mode, `main.py` wraps the FastMCP ASGI app with `AuthMiddleware`, which:
1. Requires `Authorization` on `/sse` and `/messages`.
2. `Bearer <jwt>` → stores `{'type': 'Bearer', 'token': ...}` in the `request_auth` ContextVar.
3. `Basic base64(user:pass)` → stores `{'type': 'Basic', 'auth': HTTPBasicAuth(...)}`.
4. The middleware **does not verify** the credentials itself — it sets the context and lets the downstream LinShare API call fail if they are bad.

This means tools must always go through `auth_manager.get_user_header()` / `get_admin_auth()` so per-request credentials win over the configured globals. Do not read `LINSHARE_JWT_TOKEN` / `LINSHARE_USERNAME` directly inside tools.

### Logging must go to stderr
`utils/logging.py` rewires the root logger to `sys.stderr` because stdio MCP uses stdout for the JSON-RPC protocol — printing/logging to stdout will corrupt the stream. Use the shared `logger` from `utils.logging` instead of `print` in tool code (`main.py`'s startup banners use `print` because that runs before stdio is handed to FastMCP).

### Chat client ↔ MCP server contract
`linshare-chat-client/chat_client.py` connects to the MCP server's `/sse` endpoint and always sends an `Authorization` header (Bearer JWT in User mode, Basic in Admin mode), which the middleware above consumes. The client also does OIDC login for *itself* via Chainlit — that OIDC session is unrelated to the LinShare API auth, which is still configured via the Settings UI or env (`LINSHARE_JWT_TOKEN`, etc.). Per-user chat-client settings persist to `linshare-chat-client/user_configs.json` (gitignored).

### Upload modes
Two distinct upload paths exist because the server may run on a different machine than the client:
- `upload_file_from_local_directory` reads from `LINSHARE_UPLOAD_DIR` on the **server's** disk — only useful in stdio/local mode.
- `user_remote_upload_from_url` / `user_remote_upload_by_chunks` are the SSE-friendly paths (fetch from URL, or base64 chunks over MCP).

## Conventions

- Tool names follow `user_*` / `admin_*` / `*_my_*` prefixes; preserve them so prompts continue to route correctly. Tool docstrings encode tags like `[USER API]` / `[SERVER SIDE]` that the LLM reads — keep that style when adding tools.
- The `mcp` instance is imported from `..app` (or `...app` from `tools/user|admin/`), never re-created.
- New shared role/UUID constants belong in `config.COMMON_ROLES`, accessed via `utils/common.get_role_uuid`.
