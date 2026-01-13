import pandas as pd
from datetime import datetime
from pathlib import Path

REPORTS_BASE = Path("reports")
ASN_DO_DIR = REPORTS_BASE / "asn_do"
ASN_DO_DIR.mkdir(parents=True, exist_ok=True)

def execute(ctx):
    failures = ctx.get("asn_do_failures", [])
    if not failures:
        return ctx

    ticket = ctx.get("issue_key")
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    filename = f"{ticket}_ASN_DO_{ts}.xlsx"
    path = ASN_DO_DIR / filename

    pd.DataFrame(failures).to_excel(path, index=False)

    ctx["asn_do_excel"] = {
        "file": filename,
        "relative_path": f"asn_do/{filename}",
        "rows": len(failures),
    }

    ctx.log(f"📄 ASN/DO Excel generated → {filename}")
    return ctx
