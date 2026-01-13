# api/routes/dev.py
from fastapi import APIRouter
from fastapi.responses import FileResponse
from JiraAI.engine.storage.mongo import logs_col, events_col
from pathlib import Path
from datetime import date

router = APIRouter()

REPORT_DIR = Path("reports")
ASN_DO_DIR = REPORT_DIR / "asn_do"


def clean(doc):
    doc["_id"] = str(doc["_id"])
    return doc


@router.get("/ticket/{ticket}")
def ticket_details(ticket: str):
    logs = [clean(d) for d in logs_col.find({"ticket": ticket})]
    events = [clean(d) for d in events_col.find({"ticket": ticket})]

    return {
        "ticket": ticket,
        "logs": logs,
        "events": events,
    }


@router.get("/reports/business")
def download_business_report():
    path = REPORT_DIR / f"business_report_{date.today().isoformat()}.csv"
    return FileResponse(path, filename=path.name)


@router.get("/reports/unknown")
def download_unknown_report():
    path = REPORT_DIR / f"unknown_intent_report_{date.today().isoformat()}.csv"
    return FileResponse(path, filename=path.name)


@router.get("/reports/daily")
def download_daily_report():
    path = REPORT_DIR / f"daily_report_{date.today().isoformat()}.csv"
    return FileResponse(path, filename=path.name)


# --------------------------------------------------
# ✅ NEW: ASN / DO FAILED REPORT LIST (DEV ONLY)
# --------------------------------------------------
@router.get("/reports/asn-do")
def list_asn_do_reports():
    if not ASN_DO_DIR.exists():
        return []

    reports = []

    for f in ASN_DO_DIR.glob("*.xlsx"):
        ticket = f.name.split("_")[0]
        reports.append({
            "ticket": ticket,
            "file": f.name,
            "download_url": f"/reports/asn_do/{f.name}",
        })

    return reports


@router.get("/ticket/{ticket}/final-comment")
def get_final_comment(ticket: str):
    doc = events_col.find_one(
        {"ticket": ticket, "type": "FINAL_COMMENT"},
        sort=[("_id", -1)]
    )

    if not doc:
        return {"ticket": ticket, "comment": None}

    return {
        "ticket": ticket,
        "sop": doc["payload"].get("sop"),
        "blocked_by": doc["payload"].get("blocked_by"),
        "country": doc["payload"].get("country"),
        "comment": doc["payload"].get("comment"),
    }
