# extractors/excel.py

import pandas as pd
import io
from JiraAI.engine.util import normalize_col

SOURCE_COLS = {
    "ordencliente",
    "deliveryordernumber",
    "sourceorder",
    "source_order",
    "IKEA_Orden"
}

LPN_COLS = {
    "lpn",
    "olpn",
}

def extract_ids_from_excel(content: bytes, ctx):
    ids = {
        "fo_ids": [],
        "source_order_ids": [],
        "lpn_ids": [],
        "unknown_ids": [],
    }

    # 🛑 Guard: HTML masquerading as Excel
    if content[:20].lower().startswith(b"<html"):
        ctx.log("⚠️ Excel attachment is HTML → skipped")
        return ids

    engines = ["openpyxl", "xlrd"]

    df = None
    for engine in engines:
        try:
            df = pd.read_excel(io.BytesIO(content), engine=engine)
            ctx.log(f"📊 Excel parsed using {engine}")
            break
        except Exception:
            continue

    if df is None or df.empty:
        ctx.log("⚠️ Excel unreadable or empty")
        return ids

    normalized_cols = {normalize_col(c): c for c in df.columns}

    source_cols = [normalized_cols[c] for c in normalized_cols if c in SOURCE_COLS]
    lpn_cols = [normalized_cols[c] for c in normalized_cols if c in LPN_COLS]

    # Column-based extraction
    for col in source_cols:
        for v in df[col].dropna():
            s = str(v).strip()
            if s.isdigit() and len(s) == 10:
                ids["source_order_ids"].append(s)

    for col in lpn_cols:
        for v in df[col].dropna():
            s = str(v).strip()
            if s.isdigit() and len(s) > 10:
                ids["lpn_ids"].append(s)

    # Fallback scan
    if not source_cols and not lpn_cols:
        ctx.log("ℹ️ No known Excel columns → fallback scan")
        for cell in df.astype(str).values.flatten():
            s = cell.strip()
            if s.startswith("FOF"):
                ids["fo_ids"].append(s)
            elif s.isdigit():
                if len(s) == 10:
                    ids["source_order_ids"].append(s)
                elif len(s) > 10:
                    ids["lpn_ids"].append(s)

    return ids
