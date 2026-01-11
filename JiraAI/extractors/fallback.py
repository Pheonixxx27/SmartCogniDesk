import re

def extract_from_text(text: str):
    ids = {"fo_ids": [], "source_order_ids": [], "lpn_ids": [], "unknown_ids": []}

    for token in re.findall(r"\b[\w-]+\b", text):
        if token.startswith("FOF"):
            ids["fo_ids"].append(token)
        elif token.isdigit():
            if len(token) == 10:
                ids["source_order_ids"].append(token)
            elif len(token) > 10:
                ids["lpn_ids"].append(token)

    return ids
