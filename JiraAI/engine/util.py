import re
import unicodedata

def normalize(text: str) -> str:
    """
    Normalize Jira category text for SOP matching.
    - Removes Jira codes
    - Removes accents
    - Normalizes separators
    - Collapses spaces
    """
    if not text:
        return ""

    # Remove Jira codes in brackets
    text = text.split("(")[0]

    # Lowercase
    text = text.lower()

    # Remove accents (estado → estado)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))

    # Replace separators with space
    text = re.sub(r"[\/\-_]", " ", text)

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text)

    return text.strip()
def classify_ids(raw_ids, ctx):
    """
    Deterministic ID classification with strict priority:
    FO > SOURCE_ORDER > LPN
    """

    fo_ids = []
    source_order_ids = []
    lpn_ids = []

    for raw in raw_ids:
        if not raw:
            continue

        i = str(raw).strip()

        # ----------------------------
        # FO ID
        # ----------------------------
        if i.startswith("FOF"):
            fo_ids.append(i)
            continue

        # ----------------------------
        # Numeric IDs only beyond this
        # ----------------------------
        if not i.isdigit():
            ctx.log(f"🧹 Ignored non-ID token → {i}")
            continue

        # Source Order (10 digits)
        if len(i) == 10:
            source_order_ids.append(i)

        # LPN (>10 digits)
        elif len(i) > 10:
            lpn_ids.append(i)

        else:
            ctx.log(f"🧹 Ignored short numeric token → {i}")

    # ----------------------------
    # Priority resolution
    # ----------------------------
    if fo_ids:
        ctx.log("🎯 ID priority selected → FO")
        return {
            "type": "FO",
            "ids": fo_ids
        }

    if source_order_ids:
        ctx.log("🎯 ID priority selected → SOURCE_ORDER")
        return {
            "type": "SOURCE_ORDER",
            "ids": source_order_ids
        }

    if lpn_ids:
        ctx.log("🎯 ID priority selected → LPN")
        return {
            "type": "LPN",
            "ids": lpn_ids
        }

    ctx.log("⚠️ No valid IDs after classification")
    return None

def normalize_col(col: str) -> str:
    return col.replace(" ", "").replace("_", "").lower()


def merge_ids(target: dict, source: dict):
    """
    Merge ID dictionaries without overwriting.
    """
    for k, v in source.items():
        if k not in target:
            target[k] = []
        for item in v:
            if item not in target[k]:
                target[k].append(item)