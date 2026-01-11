# extractors/csv.py

import pandas as pd
import io

def extract_ids_from_csv(content: bytes, ctx):
    ids = {
        "fo_ids": [],
        "source_order_ids": [],
        "lpn_ids": [],
        "unknown_ids": [],
    }

    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        ctx.log(f"⚠️ Failed to read CSV → {e}")
        return ids

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
