# engine/reporting/daily_report.py

import csv
from pathlib import Path
from datetime import date, datetime

REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)


def _append_csv(path: Path, fieldnames: list, row: dict):
    exists = path.exists()

    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        if not exists:
            writer.writeheader()

        writer.writerow(row)


# =====================================================
# DAILY FAILURE / STOPPED REPORT
# =====================================================
def write_daily_failure(ctx):
    today = date.today().isoformat()
    path = REPORT_DIR / f"daily_report_{today}.csv"

    fields = [
        "timestamp",
        "ticket",
        "sop",
        "step",
        "intent",
        "reason",
    ]

    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "ticket": ctx.get("issue_key"),
        "sop": ctx.get("__sop_name__"),
        "step": ctx.get("__current_step__"),
        "intent": ctx.get("intent"),
        "reason": ctx.get("intent_reason"),
    }

    _append_csv(path, fields, row)


# =====================================================
# UNKNOWN INTENT REPORT
# =====================================================
def write_unknown_intent(ctx):
    # ⛔ DO NOT log UNKNOWN caused by execution errors
    if ctx.get("execution_error"):
        return

    today = date.today().isoformat()
    path = REPORT_DIR / f"unknown_intent_report_{today}.csv"

    fields = [
        "timestamp",
        "ticket",
        "tier2",
        "intent_reason",
        "description",
        "detail",
    ]

    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "ticket": ctx.get("issue_key"),
        "tier2": ctx.get("tier2"),
        "intent_reason": ctx.get("intent_reason"),
        "description": (ctx.get("description") or "")[:500],
        "detail": (ctx.get("detail") or "")[:500],
    }

    _append_csv(path, fields, row)


# =====================================================
# BUSINESS FINAL COMMENT REPORT
# =====================================================
def write_business_comment(event: dict):
    today = date.today().isoformat()
    path = REPORT_DIR / f"business_report_{today}.csv"

    payload = event.get("payload", {})

    fields = [
        "timestamp",
        "ticket",
        "sop",
        "blocked_by",
        "country",
        "final_comment",
    ]

    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "ticket": event.get("ticket"),
        "sop": payload.get("sop"),
        "blocked_by": payload.get("blocked_by"),
        "country": payload.get("country"),
        "final_comment": payload.get("comment"),
    }

    _append_csv(path, fields, row)
