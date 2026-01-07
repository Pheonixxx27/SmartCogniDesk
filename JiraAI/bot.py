import os
import json
import requests
import urllib3
from pathlib import Path
from jira import JIRA
from dotenv import load_dotenv
import ollama

# =====================================================
# GLOBAL SETUP
# =====================================================

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

session = requests.Session()
session.verify = False

# =====================================================
# 1. ENV & AUTH
# =====================================================

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

JIRA_URL = os.getenv("JIRA_URL")
JIRA_TOKEN = os.getenv("JIRA_TOKEN")

if not JIRA_URL or not JIRA_TOKEN:
    raise RuntimeError("❌ Jira credentials missing")

jira = JIRA(
    server=JIRA_URL,
    options={
        "verify": True,
        "headers": {
            "Authorization": f"Basic {JIRA_TOKEN}",
            "Content-Type": "application/json",
        },
    },
)

print("✅ Jira connection initialized successfully")

# =====================================================
# 2. FIELD IDS (VERIFIED)
# =====================================================

TIER_1_ID = "customfield_34302"
TIER_2_ID = "customfield_34303"
TIER_3_ID = "customfield_34304"
DATA_DETAIL_ID = "customfield_19765"

# =====================================================
# 3. HELPERS
# =====================================================

def normalize(text: str) -> str:
    return text.split("(")[0].strip().lower() if text else ""

def get_select_value(ticket, field_id):
    fields = ticket.raw.get("fields", {})
    val = fields.get(field_id)

    if not val:
        return ""

    # Multi-select or single-select wrapped as list
    if isinstance(val, list) and val:
        first = val[0]
        if isinstance(first, dict):
            return first.get("value") or first.get("name") or ""
        if isinstance(first, str):
            return first

    # Single select as dict
    if isinstance(val, dict):
        return val.get("value") or val.get("name") or ""

    # Sometimes Jira sends plain string
    if isinstance(val, str):
        return val

    return ""


def get_text(ticket, field_id):
    return str(ticket.raw.get("fields", {}).get(field_id) or "")


# =====================================================
# 4. LLM EXTRACTION (SINGLE SOURCE OF TRUTH)
# =====================================================

def extract_ids_with_llm(text: str):
    """
    Extract Order IDs / LPNs using Ollama.
    NO REGEX. NO GUESSING.
    """
    if not text.strip():
        return []

    prompt = f"""
Extract ALL Order IDs or LPN numbers from the text below.

Rules:
- IDs are numeric
- Return ONLY a JSON array of strings
- Do not explain anything

Text:
{text}
"""

    try:
        response = ollama.chat(
            model="llama3:8b",
            messages=[{"role": "user", "content": prompt}],
        )

        content = response["message"]["content"].strip()
        return json.loads(content)

    except Exception as e:
        print(f"⚠️ LLM extraction failed: {e}")
        return []


# =====================================================
# 5. ATTACHMENT HANDLING (OCR READY)
# =====================================================

def extract_text_from_attachments(ticket):
    """
    Placeholder for future OCR / PDF parsing.
    Currently downloads attachment names only.
    """
    attachments = ticket.raw.get("fields", {}).get("attachment", [])
    if not attachments:
        return ""

    collected_text = ""

    for att in attachments:
        filename = att.get("filename", "")
        mime = att.get("mimeType", "")
        content_url = att.get("content")

        print(f"📎 Found attachment: {filename} ({mime})")

        # 🔴 FUTURE:
        # - Download file
        # - If image → OCR
        # - If PDF → text extraction
        # For now, we just log presence

        collected_text += f"\nAttachment: {filename}\n"

    return collected_text


# =====================================================
# 6. MOVEP / CROSSDOCK SOP
# =====================================================

def solve_crossdock_logic(ticket):
    issue_key = ticket.key
    print(f"🚀 MOVEP SOP → {issue_key}")

    description = getattr(ticket.fields, "description", "") or ""
    detail = get_text(ticket, DATA_DETAIL_ID)

    # STEP 1️⃣ — Description / fields
    ids = extract_ids_with_llm(f"{detail}\n{description}")

    # STEP 2️⃣ — Attachments fallback
    if not ids:
        print("ℹ️ No IDs in description, checking attachments...")
        attachment_text = extract_text_from_attachments(ticket)
        ids = extract_ids_with_llm(attachment_text)

    if not ids:
        print(f"⚠️ No IDs found for {issue_key}")
        return

    for order_id in ids:
        orch_url = (
            "https://localhost:8082/"
            "fulfilment-order-orchestrator/api/v1/"
            f"fulfilment-logistic-orchestrator/{order_id}"
        )

        headers = {
            "x-commerce": "FALABELLA",
            "x-country": "CL",
        }

        try:
            resp = session.get(orch_url, headers=headers, timeout=10)

            if resp.status_code == 200:
                print(f"✅ Order {order_id} found → analyzing states")
            else:
                print(f"❌ Order {order_id} not found (HTTP {resp.status_code})")

        except Exception as e:
            print(f"⚠️ Orchestrator error for {order_id}: {e}")


# =====================================================
# 7. QUEUE SCANNER
# =====================================================

def scan_queue_and_solve():
    print("🔍 Fetching LOOR - Forward - Backlog Queue...")

    jql = """
        project = LOGFTC
        AND status NOT IN (CANCELED, REJECTED, CLOSED, COMPLETED, RESOLVED)
        AND "Resolution Group" = "ITSM - LOOR-FOO"
    """

    fields = [
        "summary",
        "description",
        TIER_1_ID,
        TIER_2_ID,
        TIER_3_ID,
        DATA_DETAIL_ID,
        "attachment",
    ]

    tickets = jira.search_issues(jql, fields=fields, maxResults=100)
    print(f"📋 Found {len(tickets)} active tickets.")

    for ticket in tickets:
        tier2 = normalize(get_select_value(ticket, TIER_2_ID))

        print(
            f"{ticket.key} | "
            f"Tier2 = {get_select_value(ticket, TIER_2_ID)}"
        )

        if any(x in tier2 for x in ["asn", "do", "crossdock"]):
            solve_crossdock_logic(ticket)

        elif "cambio de estado" in tier2:
            print(f"⚡ SOP MATCH → Cambio de Estado")

        else:
            print(f"⏭️ Skipping → {ticket.key}")


# =====================================================
# 8. MAIN
# =====================================================

if __name__ == "__main__":
    scan_queue_and_solve()
