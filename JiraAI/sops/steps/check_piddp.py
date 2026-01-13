import requests


def execute(ctx):
    ctx.log("📦 STEP: CHECK_PIDDP")

    operations = ctx.get("operations", [])
    country = ctx.get("country")
    sop_name = ctx.get("__sop_name__")

    ctx.log(f"🧭 SOP name = {sop_name}")

    if not country:
        ctx.log("⚠️ Country not available → skipping PIDDP")
        return ctx

    piddp_executor = None
    piddp_state = None
    piddp_id = None
    movep_state = None

    for group in operations:
        for op in group.get("operationsInfo", []):
            code = op.get("operationCode")

            if code == "PIDPP":
                ctx.log("🔍 Found PIDPP operation in FOORCH")

                if op.get("operationCreated") != "SUCCESS":
                    ctx.log("⚠️ PIDPP operation not SUCCESS → skipping")
                    continue

                piddp_id = op.get("operationId")
                if not piddp_id:
                    ctx.log("⚠️ PIDPP operationId missing → skipping")
                    continue

                ctx.log(f"➡️ Fetching PIDPP details for {piddp_id}")

                url = (
                    "https://localhost:8082/"
                    f"pick-and-dispatch/api/v1/pick-and-dispatch-operations/{piddp_id}"
                )

                headers = {"x-commerce": "FAL", "x-country": country}
                resp = requests.get(url, headers=headers, timeout=10, verify=False)

                if resp.status_code != 200:
                    ctx.log(f"❌ PIDPP GET failed → status {resp.status_code}")
                    continue

                data = resp.json()
                piddp_state = data.get("state")
                piddp_executor = data.get("executorRef")

                ctx.log(
                    f"📦 PIDPP resolved → id={piddp_id}, "
                    f"state={piddp_state}, executor={piddp_executor}"
                )

            if code == "MOVEP":
                movep_state = op.get("operationState")
                ctx.log(f"🚚 MOVEP operationState from FOORCH = {movep_state}")

    ctx.log(
        "🔎 PIDPP/MOVEP evaluation → "
        f"sop={sop_name}, piddp_state={piddp_state}, movep_state={movep_state}"
    )

    if (
        sop_name == "ASN / DO de Crossdock con Problemas"
        and piddp_state in ("ACTIVE", "ACTIVE_EXCEPTIONS")
        and movep_state == "NEW"
    ):
        ctx.log("⛔ ASN/DO BLOCKER → Awaiting shipment confirmation")

        ctx["blocker"] = {
            "type": "PIDDP_AWAITING_SHIPMENT_CONFIRMATION",
            "country": country,
            "details": {
                "executor": piddp_executor,
                "piddp_id": piddp_id,
                "fo_id": ctx.get("fo_id"),
            },
        }
        ctx["stop_after_finalize"] = True
        return ctx

    if piddp_state in ("ACTIVE", "ACTIVE_EXCEPTIONS"):
        ctx.log("⚠️ Generic PIDPP blocker triggered")

        ctx["blocker"] = {
            "type": "PIDDP",
            "country": country,
            "details": {
                "state": piddp_state,
                "executor": piddp_executor,
                "piddp_id": piddp_id,
            },
        }

    ctx.log("✅ PIDPP not blocking, continuing SOP")
    return ctx
