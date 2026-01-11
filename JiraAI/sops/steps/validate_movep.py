def execute(ctx):
    ctx.log("🧠 STEP: VALIDATE_MOVEP")

    for group in ctx["foorch"].get("operationGroups", []):
        for op in group.get("operationsInfo", []):
            if op.get("operationCode") == "MOVEP":
                ctx["movep"] = op
                return ctx

    ctx.log("ℹ️ No MOVEP operation")
    ctx.stop()
    return ctx
