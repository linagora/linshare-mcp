import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests
from mcp.server.fastmcp import Image

from ...app import mcp
from ...config import LINSHARE_USER_URL
from ...utils.auth import auth_manager
from ...utils.common import format_file_size
from ...utils.logging import logger

_ALLOWED_TYPES = {"DOCUMENT", "FOLDER"}
_ALLOWED_SORT_FIELDS = {"name", "modificationDate", "creationDate", "size", "type"}
_ALLOWED_SORT_ORDERS = {"ASC", "DESC"}
_CROSS_SEARCH_MAX_WORKERS = 8
_THUMBNAIL_SIZE = "large"


def _format_node(index: int, node: dict) -> str:
    name = node.get("name", "Unnamed")
    node_type = node.get("type", "?")
    icon = "📄" if node_type == "DOCUMENT" else ("📁" if node_type == "FOLDER" else "•")
    full_uuid = node.get("uuid", "N/A")

    line = f"{index}. {icon} {name} [{node_type}]\n"
    # Single canonical UUID — labelling it "Short UUID … (full: …)" previously
    # caused the LLM to pass the truncated 8-char prefix to downstream tools.
    line += f"   - UUID: {full_uuid}\n"

    size = node.get("size")
    if isinstance(size, int):
        line += f"   - Size: {format_file_size(size)}\n"

    mod = node.get("modificationDate") or node.get("creationDate")
    if isinstance(mod, int):
        try:
            line += f"   - Modified: {datetime.fromtimestamp(mod / 1000).strftime('%Y-%m-%d %H:%M:%S')}\n"
        except Exception:
            line += f"   - Modified (raw ms): {mod}\n"

    parent = node.get("parent")
    if parent and parent != node.get("workGroup"):
        line += f"   - Parent folder UUID: {parent}\n"

    path_entries = node.get("treePath") or node.get("pathFromParent")
    if isinstance(path_entries, list) and path_entries:
        crumbs = " / ".join(p.get("name", "?") for p in path_entries if isinstance(p, dict))
        if crumbs:
            line += f"   - Path: /{crumbs}\n"

    return line


@mcp.tool()
def user_search_workgroup_nodes(
    workgroup_uuid: str,
    pattern: str,
    types: list[str] | None = None,
    sort_field: str = "modificationDate",
    sort_order: str = "DESC",
    page_number: int = 0,
    page_size: int = 25,
    tree: bool = True,
) -> str:
    """[USER API] Search for files and folders inside a specific workgroup (shared space) by name pattern.

    Use this tool when the user wants to find a node *within a known workgroup*
    rather than across their personal space. The workgroup UUID must be known
    in advance — pass it through from prior context.

    🔐 Authentication: JWT token required
    🌐 API Endpoint: User v5 (/shared_spaces/{workgroup_uuid}/nodes/search)

    Args:
        workgroup_uuid: UUID of the workgroup (shared space) to search inside.
        pattern: Substring to look for in node names (case-insensitive on the server).
        types: Node types to include. Any of "DOCUMENT", "FOLDER". Defaults to both.
        sort_field: One of "name", "modificationDate", "creationDate", "size", "type".
            Default: "modificationDate".
        sort_order: "ASC" or "DESC". Default: "DESC".
        page_number: Zero-based page index. Default: 0.
        page_size: Results per page (1-100 typical). Default: 25.
        tree: When True, the response includes the path from the workgroup root
            for each match (useful for showing where a file lives). Default: True.

    Returns:
        A formatted list of matching nodes with UUIDs, types, sizes, and paths,
        plus pagination metadata when more results are available.
    """
    logger.info(
        f"Tool called: user_search_workgroup_nodes("
        f"workgroup_uuid={workgroup_uuid}, pattern='{pattern}', types={types}, "
        f"sort_field={sort_field}, sort_order={sort_order}, "
        f"page_number={page_number}, page_size={page_size}, tree={tree})"
    )

    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."

    if not auth_manager.is_logged_in():
        return "Error: User not logged in. Use 'user_login_user' or set LINSHARE_JWT_TOKEN."

    if not workgroup_uuid:
        return "Error: workgroup_uuid is required."
    if not pattern:
        return "Error: pattern is required."

    if sort_field not in _ALLOWED_SORT_FIELDS:
        return f"Error: sort_field must be one of {sorted(_ALLOWED_SORT_FIELDS)}."
    sort_order_norm = sort_order.upper()
    if sort_order_norm not in _ALLOWED_SORT_ORDERS:
        return f"Error: sort_order must be 'ASC' or 'DESC'."

    requested_types = types if types else ["DOCUMENT", "FOLDER"]
    normalized_types = [t.upper() for t in requested_types]
    invalid_types = [t for t in normalized_types if t not in _ALLOWED_TYPES]
    if invalid_types:
        return f"Error: invalid type(s) {invalid_types}. Allowed: {sorted(_ALLOWED_TYPES)}."

    url = f"{LINSHARE_USER_URL}/shared_spaces/{workgroup_uuid}/nodes/search"
    params = [
        ("pageNumber", str(page_number)),
        ("pageSize", str(page_size)),
        ("pattern", pattern),
        ("sortField", sort_field),
        ("sortOrder", sort_order_norm),
        ("tree", str(bool(tree)).lower()),
    ]
    params.extend(("types", t) for t in normalized_types)

    try:
        response = requests.get(
            url,
            params=params,
            headers=auth_manager.get_user_header(),
            timeout=15,
        )
    except requests.RequestException as e:
        logger.error(f"Network error searching workgroup nodes: {e}")
        return f"Error contacting LinShare: {e}"

    if response.status_code == 401:
        return "Error: 401 Unauthorized. JWT is missing, expired, or invalid."
    if response.status_code == 403:
        return f"Error: 403 Forbidden. You don't have access to workgroup {workgroup_uuid}."
    if response.status_code == 404:
        return f"Error: 404 Not Found. Workgroup {workgroup_uuid} does not exist."
    if response.status_code >= 400:
        snippet = response.text[:300]
        return f"Error: LinShare returned status {response.status_code}. Body: {snippet}"

    try:
        payload = response.json()
    except ValueError:
        return f"Error: LinShare returned non-JSON response: {response.text[:300]}"

    # The endpoint may return a bare list or a page wrapper, depending on the LinShare version.
    if isinstance(payload, dict) and "data" in payload:
        items = payload.get("data") or []
        total = payload.get("totalElements", len(items))
    elif isinstance(payload, list):
        items = payload
        total = len(items)
    else:
        items = []
        total = 0

    if not items:
        return (
            f"No matches for '{pattern}' in workgroup {workgroup_uuid} "
            f"(page {page_number}, types={normalized_types})."
        )

    header = (
        f"🔍 Workgroup search results for '{pattern}' "
        f"(workgroup {workgroup_uuid}):\n"
        f"   Page {page_number} (size {page_size}) — showing {len(items)} of {total} total\n\n"
    )
    body = "".join(_format_node(i, n) + "\n" for i, n in enumerate(items, start=1))

    footer = ""
    if (page_number + 1) * page_size < total:
        footer = (
            f"⚠️  More results available. "
            f"Call again with page_number={page_number + 1} to see the next page.\n"
        )

    return header + body + footer


@mcp.tool()
def user_list_my_shared_spaces(name_pattern: str | None = None) -> str:
    """[USER API] List the shared spaces (workgroups / workspaces) the current user belongs to.

    Use this tool to discover the UUID of a workgroup by name before calling
    'user_search_workgroup_nodes' or any other tool that requires a
    workgroup_uuid.

    🔐 Authentication: JWT token required
    🌐 API Endpoint: User v5 (/shared_spaces?withRole=true)

    Args:
        name_pattern: Optional case-insensitive substring to filter by name
            client-side. Leave empty to list all shared spaces.

    Returns:
        A formatted list of shared spaces with their UUIDs, types (WORK_GROUP /
        WORK_SPACE), and the current user's role on each.
    """
    logger.info(f"Tool called: user_list_my_shared_spaces(name_pattern={name_pattern!r})")

    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."

    if not auth_manager.is_logged_in():
        return "Error: User not logged in. Use 'user_login_user' or set LINSHARE_JWT_TOKEN."

    url = f"{LINSHARE_USER_URL}/shared_spaces"
    try:
        response = requests.get(
            url,
            params={"withRole": "true"},
            headers=auth_manager.get_user_header(),
            timeout=15,
        )
    except requests.RequestException as e:
        logger.error(f"Network error listing shared spaces: {e}")
        return f"Error contacting LinShare: {e}"

    if response.status_code == 401:
        return "Error: 401 Unauthorized. JWT is missing, expired, or invalid."
    if response.status_code >= 400:
        return f"Error: LinShare returned status {response.status_code}. Body: {response.text[:300]}"

    try:
        spaces = response.json()
    except ValueError:
        return f"Error: LinShare returned non-JSON response: {response.text[:300]}"

    if not isinstance(spaces, list):
        return f"Error: unexpected response shape (expected list): {str(spaces)[:300]}"

    if name_pattern:
        needle = name_pattern.lower()
        spaces = [s for s in spaces if needle in (s.get("name") or "").lower()]

    if not spaces:
        suffix = f" matching '{name_pattern}'" if name_pattern else ""
        return f"No shared spaces found{suffix}."

    header = f"🗂️  Shared spaces ({len(spaces)}):\n\n"
    lines = []
    for i, s in enumerate(spaces, 1):
        name = s.get("name", "Unnamed")
        space_type = s.get("nodeType") or s.get("type") or "?"
        icon = "👥" if space_type == "WORK_GROUP" else ("🏢" if space_type == "WORK_SPACE" else "•")
        full_uuid = s.get("uuid", "N/A")

        line = f"{i}. {icon} {name} [{space_type}]\n"
        line += f"   - UUID: {full_uuid}\n"

        role = s.get("role")
        if isinstance(role, dict) and role.get("name"):
            line += f"   - Your role: {role['name']}\n"

        mod = s.get("modificationDate") or s.get("creationDate")
        if isinstance(mod, int):
            try:
                line += f"   - Modified: {datetime.fromtimestamp(mod / 1000).strftime('%Y-%m-%d %H:%M:%S')}\n"
            except Exception:
                pass

        lines.append(line)

    return header + "\n".join(lines)


def _fetch_workgroup_list(headers: dict) -> list[dict]:
    response = requests.get(
        f"{LINSHARE_USER_URL}/shared_spaces",
        params={"withRole": "true"},
        headers=headers,
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        return []
    return [s for s in data if (s.get("nodeType") or s.get("type")) == "WORK_GROUP"]


def _search_one_workgroup(
    workgroup: dict, pattern: str, types: list[str], page_size: int, headers: dict
) -> tuple[dict, list[dict], str | None]:
    """Run the search against a single workgroup. Returns (workgroup, items, error)."""
    uuid_ = workgroup.get("uuid")
    url = f"{LINSHARE_USER_URL}/shared_spaces/{uuid_}/nodes/search"
    params = [
        ("pageNumber", "0"),
        ("pageSize", str(page_size)),
        ("pattern", pattern),
        ("sortField", "modificationDate"),
        ("sortOrder", "DESC"),
        ("tree", "true"),
    ]
    params.extend(("types", t) for t in types)

    try:
        response = requests.get(url, params=params, headers=headers, timeout=15)
    except requests.RequestException as e:
        return workgroup, [], f"network error: {e}"

    if response.status_code >= 400:
        return workgroup, [], f"HTTP {response.status_code}"

    try:
        payload = response.json()
    except ValueError:
        return workgroup, [], "non-JSON response"

    if isinstance(payload, dict) and "data" in payload:
        items = payload.get("data") or []
    elif isinstance(payload, list):
        items = payload
    else:
        items = []
    return workgroup, items, None


@mcp.tool()
def user_search_all_my_workgroups(
    pattern: str,
    types: list[str] | None = None,
    limit_per_workgroup: int = 10,
    workgroup_name_filter: str | None = None,
    max_workgroups: int | None = None,
) -> str:
    """[USER API] Search a pattern across ALL workgroups the user belongs to.

    Use this when the user wants to find files matching a name across every
    workgroup at once, without already knowing which one to look in. This tool
    internally calls 'user_list_my_shared_spaces' then runs the search against
    each workgroup in parallel — the LLM does not need to chain calls itself.

    🔐 Authentication: JWT token required
    🌐 API Endpoints: User v5
        - GET /shared_spaces?withRole=true
        - GET /shared_spaces/{uuid}/nodes/search  (per workgroup, in parallel)

    Args:
        pattern: Substring to look for in node names.
        types: Node types to include — "DOCUMENT", "FOLDER", or both (default).
        limit_per_workgroup: Max matches to keep per workgroup (default 10).
            Use this to control output size; bump it only when needed.
        workgroup_name_filter: Optional case-insensitive substring; only
            workgroups whose name matches will be scanned. Useful when the
            user's account has many workgroups and you want a subset.
        max_workgroups: Optional hard cap on how many workgroups to scan
            (after the name filter). Prevents runaway API usage on accounts
            with hundreds of workgroups. Default: no cap.

    Returns:
        A formatted, grouped-by-workgroup report of every match, plus a
        summary line (workgroups scanned, workgroups with matches, total
        matches) and any per-workgroup errors encountered.
    """
    logger.info(
        f"Tool called: user_search_all_my_workgroups(pattern='{pattern}', "
        f"types={types}, limit_per_workgroup={limit_per_workgroup}, "
        f"workgroup_name_filter={workgroup_name_filter!r}, "
        f"max_workgroups={max_workgroups})"
    )

    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
    if not auth_manager.is_logged_in():
        return "Error: User not logged in. Use 'user_login_user' or set LINSHARE_JWT_TOKEN."
    if not pattern:
        return "Error: pattern is required."

    requested_types = types if types else ["DOCUMENT", "FOLDER"]
    normalized_types = [t.upper() for t in requested_types]
    invalid_types = [t for t in normalized_types if t not in _ALLOWED_TYPES]
    if invalid_types:
        return f"Error: invalid type(s) {invalid_types}. Allowed: {sorted(_ALLOWED_TYPES)}."

    if limit_per_workgroup < 1:
        return "Error: limit_per_workgroup must be >= 1."

    headers = auth_manager.get_user_header()

    try:
        workgroups = _fetch_workgroup_list(headers)
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "?"
        return f"Error listing workgroups: HTTP {status}."
    except requests.RequestException as e:
        return f"Error contacting LinShare: {e}"

    total_available = len(workgroups)

    if workgroup_name_filter:
        needle = workgroup_name_filter.lower()
        workgroups = [w for w in workgroups if needle in (w.get("name") or "").lower()]

    if max_workgroups is not None and max_workgroups >= 0:
        workgroups = workgroups[:max_workgroups]

    if not workgroups:
        return f"No workgroups to scan (filter='{workgroup_name_filter}', total available={total_available})."

    results: list[tuple[dict, list[dict]]] = []
    errors: list[tuple[dict, str]] = []
    with ThreadPoolExecutor(max_workers=min(_CROSS_SEARCH_MAX_WORKERS, len(workgroups))) as pool:
        futures = [
            pool.submit(_search_one_workgroup, wg, pattern, normalized_types, limit_per_workgroup, headers)
            for wg in workgroups
        ]
        for fut in as_completed(futures):
            wg, items, err = fut.result()
            if err is not None:
                errors.append((wg, err))
            if items:
                results.append((wg, items[:limit_per_workgroup]))

    # Stable ordering: by workgroup name
    results.sort(key=lambda r: (r[0].get("name") or "").lower())

    total_matches = sum(len(items) for _, items in results)

    header = (
        f"🔍 Cross-workgroup search for '{pattern}':\n"
        f"   Scanned {len(workgroups)} workgroup(s) "
        f"(of {total_available} available); matches in {len(results)}; "
        f"{total_matches} total match(es).\n\n"
    )

    if not results:
        body = "No matches found in any workgroup.\n"
    else:
        sections = []
        for wg, items in results:
            wg_name = wg.get("name", "Unnamed")
            wg_uuid = wg.get("uuid", "N/A")
            section = f"📂 {wg_name} (workgroup UUID: {wg_uuid}) — {len(items)} match(es)\n"
            for i, node in enumerate(items, 1):
                section += "   " + _format_node(i, node).replace("\n", "\n   ").rstrip() + "\n"
            sections.append(section)
        body = "\n".join(sections)

    footer = ""
    if errors:
        footer = "\n⚠️  Errors in " + str(len(errors)) + " workgroup(s):\n"
        for wg, err in errors[:5]:
            footer += f"   - {wg.get('name', '?')} ({wg.get('uuid') or '?'}): {err}\n"
        if len(errors) > 5:
            footer += f"   …and {len(errors) - 5} more\n"

    return header + body + footer


@mcp.tool()
def user_get_workgroup_file_preview(
    workgroup_uuid: str,
    node_uuid: str,
):
    """[USER API] Get a large thumbnail preview image of a file inside a workgroup.

    Returns a PNG (or PDF) preview that the chat assistant can render inline.
    Only files LinShare can preview will return an image (typically images,
    PDFs and some office docs); folders and unpreviewable file types return a
    text message.

    🔐 Authentication: JWT token required
    🌐 API Endpoint: User v5
        - GET /shared_spaces/{workgroup_uuid}/nodes/{node_uuid}/thumbnail/large?base64=true

    Args:
        workgroup_uuid: UUID of the workgroup containing the file.
        node_uuid: UUID of the file node (must be a DOCUMENT — folders have no thumbnail).

    Returns:
        An Image object on success, or a text message explaining why no
        preview is available (e.g. node has no thumbnail, wrong type, 404).
    """
    logger.info(
        f"Tool called: user_get_workgroup_file_preview(workgroup_uuid={workgroup_uuid}, "
        f"node_uuid={node_uuid})"
    )

    if not LINSHARE_USER_URL:
        return "Error: LINSHARE_USER_URL not configured."
    if not auth_manager.is_logged_in():
        return "Error: User not logged in. Use 'user_login_user' or set LINSHARE_JWT_TOKEN."
    if not workgroup_uuid:
        return "Error: workgroup_uuid is required."
    if not node_uuid:
        return "Error: node_uuid is required."

    # Precheck: ask LinShare for the node metadata and read hasThumbnail before
    # spending bandwidth on a potentially-empty thumbnail download.
    meta_url = f"{LINSHARE_USER_URL}/shared_spaces/{workgroup_uuid}/nodes/{node_uuid}"
    meta_headers = {**auth_manager.get_user_header(), "Accept": "application/json"}
    try:
        meta_resp = requests.get(meta_url, headers=meta_headers, timeout=15)
    except requests.RequestException as e:
        logger.error(f"Network error fetching node metadata: {e}")
        return f"Error contacting LinShare: {e}"

    if meta_resp.status_code == 401:
        return "Error: 401 Unauthorized. JWT is missing, expired, or invalid."
    if meta_resp.status_code == 403:
        return f"Error: 403 Forbidden. You don't have access to workgroup {workgroup_uuid}."
    if meta_resp.status_code == 404:
        return f"File not found: node {node_uuid} does not exist in workgroup {workgroup_uuid}."
    if meta_resp.status_code >= 400:
        return f"Error: LinShare returned status {meta_resp.status_code} for node metadata."

    try:
        meta = meta_resp.json()
    except ValueError:
        return f"Error: node metadata response was not JSON (got {meta_resp.headers.get('Content-Type')})."

    node_name = meta.get("name") or node_uuid
    node_type = meta.get("type") or meta.get("nodeType")
    if node_type and node_type != "DOCUMENT":
        return f"No preview available: '{node_name}' is a {node_type}, not a file."
    if not meta.get("hasThumbnail", False):
        mime = meta.get("mimeType") or "unknown"
        return f"No preview available for '{node_name}' (mime: {mime}). LinShare did not generate a thumbnail for this file."

    url = (
        f"{LINSHARE_USER_URL}/shared_spaces/{workgroup_uuid}"
        f"/nodes/{node_uuid}/thumbnail/{_THUMBNAIL_SIZE}"
    )
    try:
        response = requests.get(
            url,
            params={"base64": "true"},
            headers=auth_manager.get_user_header(),
            timeout=30,
        )
    except requests.RequestException as e:
        logger.error(f"Network error fetching thumbnail: {e}")
        return f"Error contacting LinShare: {e}"

    if response.status_code == 401:
        return "Error: 401 Unauthorized. JWT is missing, expired, or invalid."
    if response.status_code == 403:
        return f"Error: 403 Forbidden. You don't have access to workgroup {workgroup_uuid}."
    if response.status_code == 404:
        return (
            f"No preview available: node {node_uuid} not found in workgroup "
            f"{workgroup_uuid}, or this file type has no thumbnail."
        )
    if response.status_code >= 400:
        return f"Error: LinShare returned status {response.status_code}. Body: {response.text[:300]}"

    body = response.content
    if not body:
        return f"No preview available for node {node_uuid} (empty thumbnail response)."

    # Body may be a bare base64 string or a JSON-quoted string. Strip quotes if present.
    raw_b64 = body.strip()
    if raw_b64[:1] in (b'"', b"'"):
        raw_b64 = raw_b64.strip(b'"\'')

    try:
        png_bytes = base64.b64decode(raw_b64, validate=False)
    except Exception as e:
        logger.error(f"Failed to decode base64 thumbnail: {e}")
        return f"Error: thumbnail response was not valid base64 ({e})."

    if not png_bytes or png_bytes[:4] not in (b"\x89PNG", b"%PDF"):
        return f"No preview available for node {node_uuid} (decoded payload was not an image)."

    fmt = "pdf" if png_bytes[:4] == b"%PDF" else "png"
    return Image(data=png_bytes, format=fmt)
