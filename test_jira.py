import os
from dotenv import load_dotenv
from jira import JIRA
from pathlib import Path

print("HELLO")

# Load .env
BASE_DIR = Path(__file__).resolve().parent
print("BASE DIR =", BASE_DIR)
load_dotenv(BASE_DIR / ".env")

JIRA_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_PAT = os.getenv("JIRA_TOKEN")

print("DEBUG JIRA_URL =", JIRA_URL)
print("DEBUG JIRA_USERNAME =", JIRA_USERNAME)

if not all([JIRA_URL, JIRA_USERNAME, JIRA_PAT]):
    raise RuntimeError("Missing Jira credentials")

# ❌ Basic/PAT auth (this triggers OAuth error)
jira = JIRA(
    server=JIRA_URL,
    basic_auth=(JIRA_USERNAME, JIRA_PAT),
    options={"verify": True}
)

# This call reproduces the issue
me = jira.myself()
print("✅ Connected to Jira as:", me["displayName"])