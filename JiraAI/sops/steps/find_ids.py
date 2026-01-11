# sops/steps/find_ids.py

from JiraAI.engine.util import merge_ids
from JiraAI.extractors.excel import extract_ids_from_excel
from JiraAI.extractors.csv import extract_ids_from_csv
from JiraAI.extractors.fallback import extract_from_text
from JiraAI.extractors.ocr import extract_ids_from_png


def execute(ctx):
    ctx.log("🔍 STEP: FIND_IDS")

    collected_ids = {
        "fo_ids": [],
        "source_order_ids": [],
        "lpn_ids": [],
        "unknown_ids": [],
    }

    used_attachments = False

    # =====================================================
    # 1️⃣ DESCRIPTION + DATA DETAIL (AUTHORITATIVE)
    # =====================================================
    description = ctx.get("description", "").strip()
    detail = ctx.get("detail", "").strip()

    if description:
        ctx.log("📝 Using ticket description")
        merge_ids(collected_ids, extract_from_text(description))

    if detail:
        ctx.log("🧾 Using Data Detail field")
        merge_ids(collected_ids, extract_from_text(detail))

    # =====================================================
    # 2️⃣ ATTACHMENTS (ENRICHMENT ONLY)
    # =====================================================
    attachments = ctx.get("attachments", [])

    if attachments:
        ctx.log(f"📎 Found {len(attachments)} attachment(s)")
    else:
        ctx.log("📎 No attachments found")

    jira_session = ctx.get("jira_session")

    for att in attachments:
        name = att.get("filename", "").lower()
        url = att.get("content")

        if not url:
            ctx.log(f"⚠️ Attachment {name} has no content URL")
            continue

        try:
            r = jira_session.get(url)
            r.raise_for_status()
            content = r.content
            used_attachments = True
        except Exception as e:
            ctx.log(f"⚠️ Failed downloading {name} → {e}")
            continue

        if name.endswith((".xlsx", ".xls")):
            ctx.log(f"📊 Parsing Excel → {name}")
            merge_ids(collected_ids, extract_ids_from_excel(content, ctx))

        elif name.endswith(".csv"):
            ctx.log(f"📄 Parsing CSV → {name}")
            merge_ids(collected_ids, extract_ids_from_csv(content, ctx))

        elif name.endswith(".png"):
            ctx.log(f"🖼️ Running OCR → {name}")
            merge_ids(collected_ids, extract_ids_from_png(content, ctx))

        else:
            ctx.log(f"ℹ️ Unsupported attachment type → {name}")

    # =====================================================
    # 3️⃣ FINAL VALIDATION + EVENT
    # =====================================================
    fo_count = len(collected_ids["fo_ids"])
    source_count = len(collected_ids["source_order_ids"])
    lpn_count = len(collected_ids["lpn_ids"])
    unknown_count = len(collected_ids["unknown_ids"])

    ctx.log(
        f"🆔 IDs found → "
        f"FO={fo_count}, "
        f"SOURCE={source_count}, "
        f"LPN={lpn_count}, "
        f"UNKNOWN={unknown_count}"
    )

    # 🔔 EMIT BUSINESS EVENT
    ctx.emit_event(
        "IDS_EXTRACTED",
        {
            "fo_count": fo_count,
            "source_order_count": source_count,
            "lpn_count": lpn_count,
            "unknown_count": unknown_count,
            "has_attachments": used_attachments,
            "stopped": not (fo_count or source_count or lpn_count),
        },
    )

    if collected_ids["unknown_ids"]:
        ctx.log(f"⚠️ Unknown IDs → {collected_ids['unknown_ids']}")

    if not (fo_count or source_count or lpn_count):
        ctx.log("❌ No usable IDs found from any source")
        ctx.stop()
        return ctx

    ctx["ids"] = collected_ids
    return ctx
