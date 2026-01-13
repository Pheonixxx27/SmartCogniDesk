from fastapi import APIRouter
from JiraAI.engine.storage.mongo import events_col

router = APIRouter()


@router.get("/summary")
def summary():
    return {
        "total_tickets": len(
            events_col.distinct("ticket", {"type": "SOP_SELECTED"})
        ),
        "unknown_intent": len(
            events_col.distinct(
                "ticket",
                {
                    "type": "INTENT_DETECTED",
                    "payload.intent": "UNKNOWN",
                },
            )
        ),
        "sop_completed": len(
            events_col.distinct("ticket", {"type": "SOP_COMPLETED"})
        ),
        "sop_stopped": len(
            events_col.distinct("ticket", {"type": "SOP_STOPPED"})
        ),
    }


@router.get("/ticket-type")
def sop_distribution():
    pipeline = [
        {"$match": {"type": "SOP_SELECTED"}},
        {
            "$group": {
                "_id": {
                    "sop": "$payload.sop",
                    "ticket": "$ticket",
                }
            }
        },
        {
            "$group": {
                "_id": "$_id.sop",
                "count": {"$sum": 1},
            }
        },
    ]

    return list(events_col.aggregate(pipeline))


@router.get("/ticket/{ticket}/comments")
def ticket_comments(ticket: str):

    # --------------------------------------------------
    # 1️⃣ Latest SOP boundary (one execution)
    # --------------------------------------------------
    boundary = (
        events_col.find(
            {
                "ticket": ticket,
                "type": {"$in": ["SOP_COMPLETED", "SOP_STOPPED"]},
            }
        )
        .sort("_id", -1)
        .limit(1)
    )

    boundary = next(boundary, None)

    if not boundary:
        return {
            "ticket": ticket,
            "executor_comments": [],
            "asn_do": None,
        }

    # --------------------------------------------------
    # 2️⃣ Fetch executor comments for THIS run
    # --------------------------------------------------
    cursor = events_col.find(
        {
            "ticket": ticket,
            "type": "EXECUTOR_COMMENT",
            "_id": {"$lt": boundary["_id"]},
        }
    )

    grouped = {}

    for doc in cursor:
        payload = doc.get("payload", {})
        executor = payload.get("executor")
        comments = payload.get("comments", [])

        # 🔕 drop useless executor
        if not executor or executor == "UNKNOWN":
            continue

        grouped.setdefault(executor, []).extend(comments)

    # --------------------------------------------------
    # 3️⃣ Deduplicate while preserving order
    # --------------------------------------------------
    executor_comments = []

    for executor, comments in grouped.items():
        seen = set()
        unique = []

        for c in comments:
            if c not in seen:
                seen.add(c)
                unique.append(c)

        if unique:
            executor_comments.append(
                {
                    "executor": executor,
                    "comments": unique,
                }
            )

    # --------------------------------------------------
    # 4️⃣ ASN / DO metadata (OPTIONAL, SAFE)
    # --------------------------------------------------
    asn_do_excel_event = events_col.find_one(
        {
            "ticket": ticket,
            "type": "EXECUTOR_COMMENT",
            "payload.sop": "ASN / DO de Crossdock con Problemas",
        },
        sort=[("_id", -1)],
    )

    asn_do = None

    if asn_do_excel_event:
        excel_event = events_col.find_one(
            {
                "ticket": ticket,
                "type": "EXECUTOR_COMMENT",
                "_id": {"$lt": boundary["_id"]},
                "payload.comments": {
                    "$elemMatch": {"$regex": "Excel file"}
                },
            },
            sort=[("_id", -1)],
        )

        if excel_event:
            comments = excel_event["payload"]["comments"]
            excel_line = next(
                (c for c in comments if "Excel file" in c),
                None,
            )

            asn_do = {
                "failed": True,
                "excel_generated": True,
                "message": excel_line,
            }
        else:
            asn_do = {
                "failed": True,
                "excel_generated": False,
                "message": (
                    "ASN / DO failure detected but no Excel was generated."
                ),
            }

    return {
        "ticket": ticket,
        "executor_comments": executor_comments,
        "asn_do": asn_do,
    }
