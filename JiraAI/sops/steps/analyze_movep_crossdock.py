import json
import time
import requests

FAIL_STATES = {"CREATED", "FAILED", "REJECTED"}
OK_STATES = {"ACCEPTED", "COMPLETED", "CANCELLED"}

def execute(ctx):
    ctx.log("🔎 STEP: ANALYZE_MOVEP_CROSSDOCK")

    blocker = ctx.get("blocker")
    if blocker and blocker.get("type") == "PIDDP_AWAITING_SHIPMENT_CONFIRMATION":
        ctx.log("⏭ Skipping MOVEP analysis — awaiting shipment confirmation")
        return ctx
    
    movep_meta = ctx.get("movep")
    if not movep_meta:
        ctx.log("ℹ️ No MOVEP metadata present")
        return ctx

    movep_id = movep_meta.get("operationId") or movep_meta.get("operationCode")
    country = ctx.get("country", "PE")

    if not movep_id:
        ctx.log("❌ MOVEP id missing")
        ctx.stop()
        return ctx

    def fetch_movep():
        url = f"https://localhost:8082/movement-operation/movement-operations/{movep_id}"
        headers = {
            "x-country": country,
            "x-commerce": "FALABELLA",
        }
        resp = requests.get(url, headers=headers, timeout=10, verify=False)
        return resp.json() if resp.status_code == 200 else None

    def analyze(movep):
        failures = []

        nodes = (
            movep
            .get("reservationDetails", {})
            .get("transferNodes", [])
        )

        for node in nodes:
            seq = node.get("sequence")
            executor = node.get("executorRef", "UNKNOWN")

            infos = node.get("packageNodeInfo") or []
            if not isinstance(infos, list):
                infos = [infos]

            for info in infos:
                reception = info.get("receptionTask")
                dispatch = info.get("dispatchTask")

                if reception and reception.get("state") in FAIL_STATES:
                    failures.append({
                        "fo_id": ctx.get("fo_id"),
                        "node": seq,
                        "executor": executor,
                        "task": "RECEPTION",
                        "state": reception.get("state"),
                    })

                if dispatch and dispatch.get("state") in FAIL_STATES:
                    failures.append({
                        "fo_id": ctx.get("fo_id"),
                        "node": seq,
                        "executor": executor,
                        "task": "DISPATCH",
                        "state": dispatch.get("state"),
                    })

        return failures

    # 1️⃣ First GET MOVEP
    movep = fetch_movep()
    if not movep:
        ctx.log("❌ Failed to fetch MOVEP")
        ctx.stop()
        return ctx

    failures = analyze(movep)

    if not failures:
        ctx.log("✅ MOVEP healthy on first check")
        return ctx

    if failures:
        ctx.log(f"❌ MOVEP still failing → {len(failures)} issues")

        ctx.setdefault("asn_do_failures", []).extend(failures)

        ctx["blocker"] = {
            "type": "ASN_DO_FAILED",
            "details": {
                "fo_id": ctx.get("fo_id"),
                "failure_count": len(failures),
            },
        }

    return ctx
