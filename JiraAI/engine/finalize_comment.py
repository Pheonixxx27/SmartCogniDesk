from JiraAI.engine.reporting.daily_report import write_business_comment


def execute(ctx):
    ctx.log("📝 STEP: FINALIZE_COMMENT (engine)")

    batch_results = ctx.get("batch_results")
    if not batch_results:
        return ctx

    final_lines = []
    blockers = set()

    for r in batch_results:
        order_id = r.get("id")
        comments = r.get("executor_comments", [])

        if comments:
            final_lines.append(f"🔹 Order ID: {order_id}")
            for c in comments:
                final_lines.append(f"  - {c}")
            final_lines.append("")

        if r.get("blocked_by"):
            blockers.add(r["blocked_by"])

    if not final_lines:
        final_lines.append(
            "Packages are already delivered or cancelled. No operational action required."
        )

    final_comment = "\n".join(final_lines)

    ctx["final_comment"] = final_comment
    ctx["blocked_by"] = ", ".join(sorted(blockers)) if blockers else None

    event = {
        "type": "FINAL_COMMENT",
        "ticket": ctx.get("issue_key"),
        "payload": {
            "comment": final_comment,
            "blocked_by": ctx["blocked_by"],
            "country": ctx.get("country"),
            "sop": ctx.get("__sop_name__"),
        },
    }

    ctx.emit_event(event["type"], event["payload"])

    ctx.log("📝 FINAL COMMENT GENERATED (engine)")
    ctx.log(final_comment)

    return ctx
