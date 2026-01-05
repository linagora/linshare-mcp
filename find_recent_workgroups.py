
import os
import sys
from datetime import datetime, timedelta, timezone

# Set up environment
os.environ["LINSHARE_USER_URL"] = "https://user.linshare-6-4-on-commit.integration-linshare.org/linshare/webservice/rest/user/v5"
# Ensure we have a token (using the one from verified session if simpler, or letting auth manager load from config)
# The config file in .gemini might not be set? user said "I'll help you..."
# I'll rely on the LINSHARE_JWT_TOKEN env var if set, or hardcode the last known good one.
os.environ["LINSHARE_JWT_TOKEN"] = "eyJhbGciOiJSUzUxMiJ9.eyJkb21haW4iOiIyNTQ3ZGI3YS02NjA2LTQwZDktOGRlZS1kNDVmZGY3NWJkMzgiLCJ1dWlkIjoiYmI4ZWY5ZTItMTU1My00NzhiLWJjODUtNzU5NjBkODI1OTk3Iiwic3ViIjoiYWJiZXkuY3VycnlAbGluc2hhcmUub3JnIiwiaWF0IjoxNzY3NjI1MzM0LCJpc3MiOiJMaW5TaGFyZSJ9.SEhpDiOipRMjbPOwp0skKKdT9RVQiD37LsXASN-Oo1nMOBp1nefT6A71M_CSenUjtJVIDpYx4dWXfwOJrGQ9EcyjoVcY_zcvhTeYH3txexgDuGjS1HlfxpfZdAXMsQ6GAdjmY6EVD07GBJMQQ6wbz7FqAZDAE_Qg8VYCMyzCe_61CZGwOznwPDowZwpN1XOqzSEpMgatOGffP-pKYEsWxEXFjwamf5V1IVK3TKrYyW8yIt-MaCFi2430KyUOAm6rJmW_Kzqlp7UWhnSk99UlfuPXdN5Dr43A-qsCHJehC0ZDAOJfdOLKQyn-agqgHFfFwY_v7dCmfG2L3KsSD7Jdhg"

from linshare_mcp.tools.user.audit import user_search_audit

# Calculate dates
now = datetime.now(timezone.utc)
seven_days_ago = now - timedelta(days=7)

# Format as ISO 8601 strings
end_date = now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
begin_date = seven_days_ago.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


import json

print(f"Searching for activities from {begin_date} to {end_date}...\n")

def filter_and_print_logs(logs_str, label):
    print(f"\n--- {label} ---")
    if "No audit logs found" in logs_str:
        print("No logs found.")
        return

    count = 0
    # Parse the text output from user_search_audit is hard because it returns formatted text.
    # BETTER: Call the API directly here or modify user_search_audit to return list? 
    # Since I cannot easily modify the tool return type without breaking other things, 
    # I will rely on the fact that I am in a script and I can just import requests and do it myself 
    # OR I can rely on the fact that the tool is just a wrapper.
    # Let's use the requests directly in this script for precise control and filtering.
    pass

# Redefine logic using direct requests to ensure we get the data and can filter it
from linshare_mcp.utils.auth import auth_manager
import requests

auth_header = auth_manager.get_user_header()
base_url = "https://user.linshare-6-4-on-commit.integration-linshare.org/linshare/webservice/rest/user/v5/audit"

def fetch_and_filter(action):
    params = {
        "forceAll": "true",
        "action": action,
        "type": "WORK_GROUP"
    }
    try:
        resp = requests.get(base_url, params=params, headers=auth_header)
        resp.raise_for_status()
        logs = resp.json()
        
        # Filter
        recent_logs = []
        for log in logs:
            cdate = log.get('creationDate') # ms timestamp
            if cdate:
                # Convert ms to datetime
                dt = datetime.fromtimestamp(cdate / 1000.0, tz=timezone.utc)
                if dt >= seven_days_ago:
                    recent_logs.append(log)
        
        print(f"--- Workgroups {action} ({len(recent_logs)} found) ---")
        for log in recent_logs:
            dt = datetime.fromtimestamp(log['creationDate'] / 1000.0, tz=timezone.utc)
            res_name = log.get('resource', {}).get('name', 'Unknown')
            uuid = log.get('uuid', 'N/A')
            print(f"[{dt}] {res_name} (UUID: {uuid})")

    except Exception as e:
        print(f"Error fetching {action}: {e}")

fetch_and_filter("CREATE")
fetch_and_filter("UPDATE")
