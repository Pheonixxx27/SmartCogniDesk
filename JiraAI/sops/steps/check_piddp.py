import requests


def execute(ctx):
    ctx.log("📦 STEP: CHECK_PIDDP")

    operations = ctx.get("operations", [])
    country = ctx.get("country")

    if not country:
        ctx.log("⚠️ Country not available → skipping PIDDP")
        return ctx

    for group in operations:
        for op in group.get("operationsInfo", []):
            if op.get("operationCode") != "PIDDP":
                continue

            if op.get("operationCreated") != "SUCCESS":
                return ctx

            piddp_id = op.get("operationId")
            if not piddp_id:
                return ctx

            url = (
                "https://localhost:8082/"
                f"pick-and-dispatch/api/v1/pick-and-dispatch-operations/{piddp_id}"
            )

            headers = {"x-commerce": "FAL", "x-country": country}
            resp = requests.get(url, headers=headers, timeout=10, verify=False)

            if resp.status_code != 200:
                return ctx

            data = resp.json()
            state = data.get("state")
            executor = data.get("executorRef")

            if state in ("ACTIVE", "ACTIVE_EXCEPTIONS"):
                ctx["blocker"] = {
                    "type": "PIDDP",
                    "country": country,
                    "details": {
                        "state": state,
                        "executor": executor,
                        "piddp_id": piddp_id,
                    },
                }
                return ctx

            ctx.log(f"✅ PIDDP {state}, continuing SOP")

    return ctx
