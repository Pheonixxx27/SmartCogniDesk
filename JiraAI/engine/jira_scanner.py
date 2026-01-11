# engine/jira_scanner.py

import os
from jira import JIRA
from dotenv import load_dotenv

load_dotenv()

JIRA_URL = os.getenv("JIRA_URL")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")

if not JIRA_URL or not JIRA_TOKEN:
    raise RuntimeError("❌ Jira credentials missing")

jira = JIRA(
    server=JIRA_URL,
    options={
        "headers": {
            "Authorization": f"Basic {JIRA_TOKEN}",
            "Content-Type": "application/json",
        }
    },
)

JQL = """
project = LOGFTC
AND status NOT IN (CANCELED, REJECTED, CLOSED, COMPLETED, RESOLVED)
AND "Resolution Group" = "ITSM - LOOR-FOO"
"""

# =====================================================
# Ticket Adapter (CRITICAL)
# =====================================================

class SimpleTicket:
    def __init__(self, issue):
        self.key = issue.key
        self.description = issue.fields.description or ""
        self.detail = str(issue.raw["fields"].get("customfield_19765") or "")
        self.tier2_text = self._extract_tier2(issue)
        self.attachments = issue.raw["fields"].get("attachment", [])

    def _extract_tier2(self, issue):
        val = issue.raw["fields"].get("customfield_34303")

        if isinstance(val, list) and val:
            val = val[0]

        if isinstance(val, dict):
            return val.get("value") or val.get("name") or ""

        if isinstance(val, str):
            return val

        return ""

# =====================================================
# Scanner
# =====================================================

def scan_queue():
    print("🔍 Fetching Jira queue...")

    fields = [
        "description",
        "customfield_34303",  # Tier 2
        "customfield_19765",  # Data Detail
        "attachment",
    ]

    issues = jira.search_issues(JQL, fields=fields, maxResults=100)
    print(f"📋 Found {len(issues)} tickets")

    tickets = [SimpleTicket(issue) for issue in issues]

    # ✅ IMPORTANT: return BOTH
    return tickets, jira._session
