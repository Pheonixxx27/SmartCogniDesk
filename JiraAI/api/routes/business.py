# api/routes/business.py
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
                    "payload.intent": "UNKNOWN"
                }
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
                    "ticket": "$ticket"
                }
            }
        },
        {
            "$group": {
                "_id": "$_id.sop",
                "count": {"$sum": 1}
            }
        }
    ]
    return list(events_col.aggregate(pipeline))

@router.get("/ticket/{ticket}/comments")
def ticket_comments(ticket: str):

    # 1️⃣ Latest SOP boundary
    boundary = (
        events_col.find(
            {
                "ticket": ticket,
                "type": {"$in": ["SOP_COMPLETED", "SOP_STOPPED"]}
            }
        )
        .sort("_id", -1)
        .limit(1)
    )

    boundary = next(boundary, None)
    if not boundary:
        return {"ticket": ticket, "executor_comments": []}

    # 2️⃣ Fetch executor comments for THIS run
    cursor = events_col.find(
        {
            "ticket": ticket,
            "type": "EXECUTOR_COMMENT",
            "_id": {"$lt": boundary["_id"]}
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

    # 3️⃣ Deduplicate while preserving order
    result = []
    for executor, comments in grouped.items():
        seen = set()
        unique = []
        for c in comments:
            if c not in seen:
                seen.add(c)
                unique.append(c)

        if unique:
            result.append({
                "executor": executor,
                "comments": unique
            })

    return {
        "ticket": ticket,
        "executor_comments": result
    }
