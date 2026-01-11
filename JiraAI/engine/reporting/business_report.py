import pandas as pd
from pathlib import Path
from datetime import date, datetime

REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(exist_ok=True)

COLUMNS = [
    "timestamp",
    "ticket",
    "sop",
    "blocked_by",
    "country",
    "final_comment",
]


def write_business_comment(event: dict):
    today = date.today().isoformat()
    report_path = REPORT_DIR / f"business_report_{today}.xlsx"

    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "ticket": event.get("ticket"),
        "sop": event.get("payload", {}).get("sop"),
        "blocked_by": event.get("payload", {}).get("blocked_by"),
        "country": event.get("payload", {}).get("country"),
        "final_comment": event.get("payload", {}).get("comment"),
    }

    if report_path.exists():
        df = pd.read_excel(report_path)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row], columns=COLUMNS)

    df.to_excel(report_path, index=False)
