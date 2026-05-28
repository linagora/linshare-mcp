"""
Unit tests for user/shared_spaces.py tools.
Patches LINSHARE_USER_URL and auth_manager at the tool-module level so the
real HTTP layer is never touched.
"""
import base64
import pytest
from unittest.mock import patch, MagicMock


_TOOL_MODULE = "linshare_mcp.tools.user.shared_spaces"
_WORKGROUP_UUID = "25e2d947-b3aa-4139-8de8-960d8eeef68e"


def _mock_response(status_code: int = 200, json_payload=None, text: str = "", content: bytes = b""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.content = content
    if json_payload is None:
        resp.json.side_effect = ValueError("no json")
    else:
        resp.json.return_value = json_payload
    return resp


_PNG_MAGIC = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


class TestUserSearchWorkgroupNodes:
    """Tests for user_search_workgroup_nodes."""

    @pytest.mark.unit
    def test_builds_correct_request_and_formats_results(self):
        payload = {
            "data": [
                {
                    "uuid": "doc-uuid-1",
                    "name": "test-report.pdf",
                    "type": "DOCUMENT",
                    "size": 2048,
                    "modificationDate": 1768609800000,
                },
                {
                    "uuid": "folder-uuid-2",
                    "name": "test-folder",
                    "type": "FOLDER",
                    "modificationDate": 1768609800000,
                },
            ],
            "totalElements": 2,
        }

        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth, \
             patch(f"{_TOOL_MODULE}.requests.get") as mock_get:
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
            mock_get.return_value = _mock_response(200, payload)

            from linshare_mcp.tools.user.shared_spaces import user_search_workgroup_nodes
            result = user_search_workgroup_nodes(
                workgroup_uuid=_WORKGROUP_UUID,
                pattern="test",
            )

        # URL and params
        called_url = mock_get.call_args.args[0]
        assert called_url == f"https://test.com/api/shared_spaces/{_WORKGROUP_UUID}/nodes/search"

        params = mock_get.call_args.kwargs["params"]
        # params is a list of (key, value) tuples so we can carry duplicate `types` keys
        as_dict_multi = {}
        for k, v in params:
            as_dict_multi.setdefault(k, []).append(v)
        assert as_dict_multi["pattern"] == ["test"]
        assert as_dict_multi["pageNumber"] == ["0"]
        assert as_dict_multi["pageSize"] == ["25"]
        assert as_dict_multi["sortField"] == ["modificationDate"]
        assert as_dict_multi["sortOrder"] == ["DESC"]
        assert as_dict_multi["tree"] == ["true"]
        assert sorted(as_dict_multi["types"]) == ["DOCUMENT", "FOLDER"]

        # Output
        assert "test-report.pdf" in result
        assert "test-folder" in result
        assert "DOCUMENT" in result and "FOLDER" in result
        assert "doc-uuid" in result  # full UUID present

    @pytest.mark.unit
    def test_empty_results(self):
        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth, \
             patch(f"{_TOOL_MODULE}.requests.get") as mock_get:
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
            mock_get.return_value = _mock_response(200, {"data": [], "totalElements": 0})

            from linshare_mcp.tools.user.shared_spaces import user_search_workgroup_nodes
            result = user_search_workgroup_nodes(
                workgroup_uuid=_WORKGROUP_UUID,
                pattern="nope",
            )

        assert "No matches" in result
        assert "nope" in result

    @pytest.mark.unit
    def test_pagination_footer_when_more_available(self):
        # 25 items returned, 100 total → footer should advertise page 1.
        items = [
            {"uuid": f"u{i}", "name": f"file-{i}", "type": "DOCUMENT", "size": 10}
            for i in range(25)
        ]
        payload = {"data": items, "totalElements": 100}

        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth, \
             patch(f"{_TOOL_MODULE}.requests.get") as mock_get:
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
            mock_get.return_value = _mock_response(200, payload)

            from linshare_mcp.tools.user.shared_spaces import user_search_workgroup_nodes
            result = user_search_workgroup_nodes(_WORKGROUP_UUID, "file")

        assert "More results available" in result
        assert "page_number=1" in result

    @pytest.mark.unit
    def test_bare_list_response_shape_is_accepted(self):
        # Some LinShare versions return a plain list rather than a {data, totalElements} wrapper.
        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth, \
             patch(f"{_TOOL_MODULE}.requests.get") as mock_get:
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
            mock_get.return_value = _mock_response(
                200,
                [{"uuid": "x", "name": "only.txt", "type": "DOCUMENT", "size": 1}],
            )

            from linshare_mcp.tools.user.shared_spaces import user_search_workgroup_nodes
            result = user_search_workgroup_nodes(_WORKGROUP_UUID, "only")

        assert "only.txt" in result

    @pytest.mark.unit
    @pytest.mark.parametrize("status,expected_substr", [
        (401, "401 Unauthorized"),
        (403, "403 Forbidden"),
        (404, "404 Not Found"),
    ])
    def test_http_error_status_codes(self, status, expected_substr):
        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth, \
             patch(f"{_TOOL_MODULE}.requests.get") as mock_get:
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
            mock_get.return_value = _mock_response(status, text="err")

            from linshare_mcp.tools.user.shared_spaces import user_search_workgroup_nodes
            result = user_search_workgroup_nodes(_WORKGROUP_UUID, "x")

        assert expected_substr in result

    @pytest.mark.unit
    def test_not_logged_in(self):
        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth:
            mock_auth.is_logged_in.return_value = False

            from linshare_mcp.tools.user.shared_spaces import user_search_workgroup_nodes
            result = user_search_workgroup_nodes(_WORKGROUP_UUID, "x")

        assert "not logged in" in result.lower()

    @pytest.mark.unit
    def test_validation_rejects_bad_sort_field(self):
        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth:
            mock_auth.is_logged_in.return_value = True

            from linshare_mcp.tools.user.shared_spaces import user_search_workgroup_nodes
            result = user_search_workgroup_nodes(
                _WORKGROUP_UUID, "x", sort_field="bogus",
            )

        assert "sort_field" in result

    @pytest.mark.unit
    def test_validation_rejects_bad_type(self):
        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth:
            mock_auth.is_logged_in.return_value = True

            from linshare_mcp.tools.user.shared_spaces import user_search_workgroup_nodes
            result = user_search_workgroup_nodes(
                _WORKGROUP_UUID, "x", types=["DOCUMENT", "BANANA"],
            )

        assert "BANANA" in result


class TestUserListMySharedSpaces:
    """Tests for user_list_my_shared_spaces."""

    @pytest.mark.unit
    def test_lists_with_role_and_filters_by_name(self):
        spaces = [
            {
                "uuid": "ws-1",
                "name": "Project Alpha",
                "nodeType": "WORK_GROUP",
                "role": {"name": "ADMIN", "uuid": "r1"},
            },
            {
                "uuid": "ws-2",
                "name": "Marketing",
                "nodeType": "WORK_GROUP",
                "role": {"name": "READER", "uuid": "r2"},
            },
        ]

        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth, \
             patch(f"{_TOOL_MODULE}.requests.get") as mock_get:
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
            mock_get.return_value = _mock_response(200, spaces)

            from linshare_mcp.tools.user.shared_spaces import user_list_my_shared_spaces
            # No filter → both rows
            result_all = user_list_my_shared_spaces()
            # Case-insensitive name filter → only Marketing
            result_filtered = user_list_my_shared_spaces(name_pattern="market")

        # URL + params
        assert mock_get.call_args.args[0] == "https://test.com/api/shared_spaces"
        assert mock_get.call_args.kwargs["params"] == {"withRole": "true"}

        assert "Project Alpha" in result_all and "Marketing" in result_all
        assert "ADMIN" in result_all and "READER" in result_all

        assert "Marketing" in result_filtered
        assert "Project Alpha" not in result_filtered

    @pytest.mark.unit
    def test_empty_list(self):
        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth, \
             patch(f"{_TOOL_MODULE}.requests.get") as mock_get:
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
            mock_get.return_value = _mock_response(200, [])

            from linshare_mcp.tools.user.shared_spaces import user_list_my_shared_spaces
            result = user_list_my_shared_spaces()

        assert "No shared spaces found" in result

    @pytest.mark.unit
    def test_unauthorized(self):
        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth, \
             patch(f"{_TOOL_MODULE}.requests.get") as mock_get:
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
            mock_get.return_value = _mock_response(401, text="bad token")

            from linshare_mcp.tools.user.shared_spaces import user_list_my_shared_spaces
            result = user_list_my_shared_spaces()

        assert "401 Unauthorized" in result


class TestUserSearchAllMyWorkgroups:
    """Tests for user_search_all_my_workgroups."""

    @pytest.mark.unit
    def test_aggregates_matches_and_groups_by_workgroup(self):
        workgroups = [
            {"uuid": "wg-1", "name": "Alpha", "nodeType": "WORK_GROUP"},
            {"uuid": "wg-2", "name": "Beta", "nodeType": "WORK_GROUP"},
            {"uuid": "ws-3", "name": "Workspace", "nodeType": "WORK_SPACE"},  # excluded
        ]
        per_wg_results = {
            "wg-1": [
                {"uuid": "n1", "name": "test-1.txt", "type": "DOCUMENT", "size": 10},
            ],
            "wg-2": [
                {"uuid": "n2", "name": "test-2.txt", "type": "DOCUMENT", "size": 20},
                {"uuid": "n3", "name": "testfolder", "type": "FOLDER"},
            ],
        }

        def fake_get(url, params=None, headers=None, timeout=None):
            if url.endswith("/shared_spaces"):
                return _mock_response(200, workgroups)
            for wg_uuid, items in per_wg_results.items():
                if f"/shared_spaces/{wg_uuid}/nodes/search" in url:
                    return _mock_response(200, items)
            return _mock_response(404, text="unknown")

        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth, \
             patch(f"{_TOOL_MODULE}.requests.get", side_effect=fake_get):
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}

            from linshare_mcp.tools.user.shared_spaces import user_search_all_my_workgroups
            result = user_search_all_my_workgroups("test")

        # Summary line reflects WORK_GROUP-only pool (2), both with matches, 3 nodes total
        assert "Scanned 2 workgroup(s)" in result
        assert "matches in 2" in result
        assert "3 total match(es)" in result
        # Workspace must NOT have been scanned
        assert "Workspace" not in result
        # Both workgroups represented and stably ordered (Alpha then Beta)
        assert result.index("Alpha") < result.index("Beta")
        # Node names present
        for name in ("test-1.txt", "test-2.txt", "testfolder"):
            assert name in result

    @pytest.mark.unit
    def test_workgroup_name_filter_narrows_the_scan(self):
        workgroups = [
            {"uuid": "wg-1", "name": "Marketing", "nodeType": "WORK_GROUP"},
            {"uuid": "wg-2", "name": "Engineering", "nodeType": "WORK_GROUP"},
        ]
        scanned = []

        def fake_get(url, params=None, headers=None, timeout=None):
            if url.endswith("/shared_spaces"):
                return _mock_response(200, workgroups)
            scanned.append(url)
            return _mock_response(200, [])

        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth, \
             patch(f"{_TOOL_MODULE}.requests.get", side_effect=fake_get):
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}

            from linshare_mcp.tools.user.shared_spaces import user_search_all_my_workgroups
            result = user_search_all_my_workgroups("x", workgroup_name_filter="market")

        # Only Marketing's search endpoint should have been called
        assert len(scanned) == 1
        assert "/shared_spaces/wg-1/nodes/search" in scanned[0]
        # Summary mentions the filtered count vs total available
        assert "Scanned 1 workgroup(s) (of 2 available)" in result

    @pytest.mark.unit
    def test_collects_per_workgroup_errors(self):
        workgroups = [
            {"uuid": "wg-good", "name": "Good", "nodeType": "WORK_GROUP"},
            {"uuid": "wg-bad", "name": "Bad", "nodeType": "WORK_GROUP"},
        ]

        def fake_get(url, params=None, headers=None, timeout=None):
            if url.endswith("/shared_spaces"):
                return _mock_response(200, workgroups)
            if "/wg-good/" in url:
                return _mock_response(200, [{"uuid": "n", "name": "hit", "type": "DOCUMENT"}])
            return _mock_response(500, text="boom")

        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth, \
             patch(f"{_TOOL_MODULE}.requests.get", side_effect=fake_get):
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}

            from linshare_mcp.tools.user.shared_spaces import user_search_all_my_workgroups
            result = user_search_all_my_workgroups("x")

        assert "Errors in 1 workgroup(s)" in result
        assert "Bad" in result and "HTTP 500" in result
        # The good workgroup's match is still reported
        assert "hit" in result


def _meta_response(has_thumbnail: bool = True, name: str = "file.jpg", node_type: str = "DOCUMENT", mime: str = "image/jpeg"):
    return _mock_response(200, json_payload={
        "uuid": "node-uuid", "name": name, "type": node_type,
        "mimeType": mime, "hasThumbnail": has_thumbnail,
    })


class TestUserGetWorkgroupFilePreview:
    """Tests for user_get_workgroup_file_preview."""

    @pytest.mark.unit
    def test_returns_image_when_hasThumbnail_true(self):
        from mcp.server.fastmcp import Image
        b64 = base64.b64encode(_PNG_MAGIC)

        def fake_get(url, params=None, headers=None, timeout=None):
            if url.endswith("/thumbnail/large"):
                return _mock_response(200, content=b64)
            # node-metadata precheck
            return _meta_response(has_thumbnail=True)

        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth, \
             patch(f"{_TOOL_MODULE}.requests.get", side_effect=fake_get) as mock_get:
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}

            from linshare_mcp.tools.user.shared_spaces import user_get_workgroup_file_preview
            result = user_get_workgroup_file_preview(_WORKGROUP_UUID, "node-uuid")

        # 2 calls: metadata precheck + thumbnail fetch
        assert mock_get.call_count == 2
        thumb_url = mock_get.call_args_list[-1].args[0]
        assert thumb_url == (
            f"https://test.com/api/shared_spaces/{_WORKGROUP_UUID}/nodes/node-uuid/thumbnail/large"
        )

        assert isinstance(result, Image)
        assert result._format == "png"
        assert result.data.startswith(b"\x89PNG")

    @pytest.mark.unit
    def test_skips_download_when_hasThumbnail_false(self):
        # When metadata says hasThumbnail=false, the tool must NOT call the thumbnail endpoint.
        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth, \
             patch(f"{_TOOL_MODULE}.requests.get") as mock_get:
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
            mock_get.return_value = _meta_response(
                has_thumbnail=False, name="archive.zip", mime="application/zip",
            )

            from linshare_mcp.tools.user.shared_spaces import user_get_workgroup_file_preview
            result = user_get_workgroup_file_preview(_WORKGROUP_UUID, "node-uuid")

        # Only the metadata call should have happened
        assert mock_get.call_count == 1
        assert "/thumbnail/" not in mock_get.call_args.args[0]
        assert "No preview available" in result
        assert "archive.zip" in result
        assert "application/zip" in result

    @pytest.mark.unit
    def test_rejects_non_document_nodes(self):
        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth, \
             patch(f"{_TOOL_MODULE}.requests.get") as mock_get:
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
            mock_get.return_value = _meta_response(
                has_thumbnail=True, name="my-folder", node_type="FOLDER", mime=None,
            )

            from linshare_mcp.tools.user.shared_spaces import user_get_workgroup_file_preview
            result = user_get_workgroup_file_preview(_WORKGROUP_UUID, "node-uuid")

        assert mock_get.call_count == 1
        assert "FOLDER" in result
        assert "my-folder" in result

    @pytest.mark.unit
    def test_404_on_metadata_returns_friendly_message(self):
        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth, \
             patch(f"{_TOOL_MODULE}.requests.get") as mock_get:
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}
            mock_get.return_value = _mock_response(404, text="not found")

            from linshare_mcp.tools.user.shared_spaces import user_get_workgroup_file_preview
            result = user_get_workgroup_file_preview(_WORKGROUP_UUID, "missing")

        assert "File not found" in result
        assert "missing" in result

    @pytest.mark.unit
    def test_non_image_payload_returns_text(self):
        # Metadata says we have a thumbnail, but the binary payload turns out to be junk.
        b64 = base64.b64encode(b"not-an-image-at-all")

        def fake_get(url, params=None, headers=None, timeout=None):
            if url.endswith("/thumbnail/large"):
                return _mock_response(200, content=b64)
            return _meta_response(has_thumbnail=True)

        with patch(f"{_TOOL_MODULE}.LINSHARE_USER_URL", "https://test.com/api"), \
             patch(f"{_TOOL_MODULE}.auth_manager") as mock_auth, \
             patch(f"{_TOOL_MODULE}.requests.get", side_effect=fake_get):
            mock_auth.is_logged_in.return_value = True
            mock_auth.get_user_header.return_value = {"Authorization": "Bearer token"}

            from linshare_mcp.tools.user.shared_spaces import user_get_workgroup_file_preview
            result = user_get_workgroup_file_preview(_WORKGROUP_UUID, "weird")

        assert "No preview available" in result
