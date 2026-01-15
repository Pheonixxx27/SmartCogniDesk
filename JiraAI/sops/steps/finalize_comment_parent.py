def execute(ctx):
    ctx.log("🧾 STEP: FINALIZE_COMMENT (parent)")

    executor_comments = ctx.get("executor_comments")
    if not executor_comments:
        ctx.log("ℹ️ No executor comments → no final Jira comment")
        return ctx

    lines = []
    for line in executor_comments:
        lines.append(line)

    final_comment = "\n".join(lines)

    ctx["final_comment"] = final_comment

    ctx.emit_event(
        "FINAL_COMMENT",
        {
            "comment": final_comment,
            "sop": ctx.get("__sop_name__"),
            "country": ctx.get("country"),
        }
    )

    ctx.log("📝 Final Jira comment prepared")
    return ctx
