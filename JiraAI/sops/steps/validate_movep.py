def execute(ctx):
    ctx.log("🧠 STEP: VALIDATE_MOVEP")

    for group in ctx["foorch"].get("operationGroups", []):
        for op in group.get("operationsInfo", []):
            if op.get("operationCode") == "MOVEP":
                ctx["movep"] = op
                return ctx

    # MOVEP missing → business-visible blocker
    ctx.log("ℹ️ MOVEP operation not present")

    ctx["blocker"] = {
        "type": "MOVEP_NOT_PRESENT",
        "details": {
            "fo_id": ctx.get("fo_id"),
        },
    }
    return ctx
