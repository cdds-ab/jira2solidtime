#!/usr/bin/env python3
"""Debug the complete sync flow with Solidtime."""

import json
import os
import sys
from datetime import datetime, timedelta
from typing import cast

sys.path.insert(0, "src")

from jira2solidtime.api.jira_client import JiraClient
from jira2solidtime.api.solidtime_client import SolidtimeClient
from jira2solidtime.api.tempo_client import TempoClient
from jira2solidtime.sync.mapper import Mapper

SOLID_TOKEN = os.getenv("SOLID_TOKEN")
TEMPO_TOKEN = os.getenv("TEMPO_TOKEN")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")

if not all([SOLID_TOKEN, TEMPO_TOKEN, JIRA_EMAIL, JIRA_TOKEN]):
    print("❌ Missing environment variables")
    print("   Required: SOLID_TOKEN, TEMPO_TOKEN, JIRA_EMAIL, JIRA_TOKEN")
    sys.exit(1)

# Type guard after checking (cast is safe here since we've validated)
SOLID_TOKEN = cast(str, SOLID_TOKEN)
TEMPO_TOKEN = cast(str, TEMPO_TOKEN)
JIRA_EMAIL = cast(str, JIRA_EMAIL)
JIRA_TOKEN = cast(str, JIRA_TOKEN)

print("🔍 Debugging Complete Sync Flow")
print("")

# 1. Get Tempo worklogs
print("1️⃣  Fetching Tempo worklogs...")
tempo = TempoClient(api_token=TEMPO_TOKEN)
to_date = datetime.now()
from_date = to_date - timedelta(days=30)
worklogs = tempo.get_worklogs(from_date, to_date)
print(f"✅ Found {len(worklogs)} worklog(s)")

if not worklogs:
    print("❌ No worklogs found")
    sys.exit(1)

worklog = worklogs[0]
print(f"   Worklog: {json.dumps(worklog, indent=4, default=str)}")
print("")

# 2. Get Jira issue
print("2️⃣  Fetching Jira issue...")
jira = JiraClient(base_url="https://cdds.atlassian.net", email=JIRA_EMAIL, api_token=JIRA_TOKEN)
issue_id = worklog.get("issue", {}).get("id")
jira_issue = jira.get_issue(str(issue_id))
issue_key = jira_issue.get("key")
if not issue_key:
    print("❌ Could not get issue key from Jira")
    sys.exit(1)
print(f"✅ Issue: {issue_key}")
print("")

# 3. Get Solidtime projects and build payload
print("3️⃣  Building Solidtime payload...")
solidtime = SolidtimeClient(
    base_url="https://solidtime.grossweber.com",
    api_token=SOLID_TOKEN,
    organization_id="c0cd7d90-5465-4ef8-8d5f-4e32fad400bf",
)

projects = solidtime.get_projects()
print(f"✅ Found {len(projects)} project(s)")

mapper = Mapper({"AS": "Beratung (CI/CD, DevOps)"})
project_key = issue_key.split("-")[0]
project_name = mapper.map_project(project_key)
print(f"   Mapped {project_key} -> {project_name}")

project = None
for p in projects:
    if p.get("name") == project_name:
        project = p
        break

if not project:
    print(f"❌ Project not found: {project_name}")
    sys.exit(1)

print(f"✅ Project: {project.get('name')} (ID: {project.get('id')})")
print("")

# 4. Build exact payload that will be sent
print("4️⃣  Building exact payload...")
duration_minutes = worklog.get("timeSpentSeconds", 0) // 60
start_date_str = worklog.get("startDate", "")
start_time_str = worklog.get("startTime", "08:00:00")
work_date = datetime.fromisoformat(f"{start_date_str}T{start_time_str}")

print(f"   Duration: {duration_minutes} minutes = {duration_minutes * 60} seconds")
print(f"   Date: {start_date_str} at {start_time_str}")
print(f"   Parsed datetime: {work_date}")
print(f"   Formatted start: {work_date.strftime('%Y-%m-%dT%H:%M:%SZ')}")
print("")

# Get member ID
print("5️⃣  Getting member ID...")
try:
    member_id = solidtime._get_member_id()
    print(f"✅ Member ID: {member_id}")
except Exception as e:
    print(f"❌ Error getting member ID: {e}")
    sys.exit(1)

print("")

# 6. Try to create time entry
print("6️⃣  Creating time entry...")
payload = {
    "member_id": member_id,
    "project_id": project.get("id"),
    "start": work_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "duration": duration_minutes * 60,
    "billable": True,
    "description": worklog.get("comment", issue_key or ""),
}

print(f"   Payload: {json.dumps(payload, indent=4)}")
print("")

try:
    project_id = project.get("id")
    if not project_id:
        print("❌ Could not get project ID")
        sys.exit(1)
    result = solidtime.create_time_entry(
        project_id=project_id,
        duration_minutes=duration_minutes,
        date=work_date,
        description=worklog.get("comment", issue_key or ""),
    )
    print("✅ SUCCESS!")
    print(f"   Result: {json.dumps(result, indent=4, default=str)}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback

    traceback.print_exc()
