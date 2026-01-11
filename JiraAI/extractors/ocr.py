# extractors/ocr.py

import pytesseract
from PIL import Image
import io

def extract_ids_from_png(content: bytes, ctx):
    ids = {
        "fo_ids": [],
        "source_order_ids": [],
        "lpn_ids": [],
        "unknown_ids": [],
    }

    # 🛑 Guard: HTML instead of image
    if content[:20].lower().startswith(b"<html"):
        ctx.log("⚠️ PNG attachment is HTML → OCR skipped")
        return ids

    try:
        img = Image.open(io.BytesIO(content))
    except Exception as e:
        ctx.log(f"⚠️ Invalid PNG → {e}")
        return ids

    try:
        text = pytesseract.image_to_string(img)
    except Exception as e:
        ctx.log(f"⚠️ OCR failed → {e}")
        return ids

    for token in text.split():
        t = token.strip()
        if t.startswith("FOF"):
            ids["fo_ids"].append(t)
        elif t.isdigit():
            if len(t) == 10:
                ids["source_order_ids"].append(t)
            elif len(t) > 10:
                ids["lpn_ids"].append(t)

    return ids
