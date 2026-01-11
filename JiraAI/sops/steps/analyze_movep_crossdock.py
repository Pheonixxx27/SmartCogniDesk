import json

FAIL_STATES = {"CREATED", "FAILED", "REJECTED"}

def execute(ctx):
    ctx.log("🔎 STEP: ANALYZE_MOVEP")

    movep = ctx["movep"]
    if movep.get("operationCreated") != "SUCCESS":
        ctx.log("⚠️ MOVEP not created successfully")
        ctx.stop()
        return ctx

    payload = json.loads(movep.get("payload", "{}"))
    nodes = payload.get("reservationDetails", {}).get("transferNodes", [])

    failures = []

    for n in nodes:
        info = n.get("packageNodeInfo", {})
        if isinstance(info, list) and info:
            info = info[0]

        for task in ["receptionTask", "dispatchTask"]:
            state = info.get(task, {}).get("state")
            if state in FAIL_STATES:
                failures.append(f"{task}:{state}")

    if failures:
        ctx.log(f"⚠️ Failures → {failures}")
    else:
        ctx.log("✅ MOVEP healthy")

    return ctx
