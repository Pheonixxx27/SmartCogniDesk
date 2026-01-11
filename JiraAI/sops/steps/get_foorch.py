import requests

def execute(ctx):
    ctx.log("🌐 STEP: GET_FOORCH")

    fo_id = ctx.get("fo_id")
    country = ctx.get("country", "PE")

    url = (
        "https://localhost:8082/"
        f"fulfilment-order-orchestrator/api/v1/fulfilment-logistic-orchestrator/{fo_id}"
    )

    headers = {
        "x-commerce": "FALABELLA",
        "x-country": country,
    }

    resp = requests.get(url, headers=headers, timeout=10, verify=False)

    # --------------------------------------------------
    # 1️⃣ FOORCH not found → HARD STOP (no business comment)
    # --------------------------------------------------
    if resp.status_code != 200:
        ctx.log(f"❌ FO {fo_id} not present in FOORCH")
        ctx.stop()
        return ctx

    ctx["foorch"] = resp.json()

    order_status = ctx["foorch"].get("orderStatus")

    # --------------------------------------------------
    # 2️⃣ TERMINAL STATE → BUSINESS BLOCKER (NO STOP)
    # --------------------------------------------------
    if order_status in ("CANCELLED", "COMPLETED", "COMPLETED_EXCEPTIONS"):
        ctx.log(f"ℹ️ FOORCH in terminal state → {order_status}")

        ctx["blocker"] = {
            "type": "FOORCH_TERMINAL",
            "country": country,
            "details": {
                "status": order_status,
                "fo_id": fo_id,
            },
        }
        return ctx  # ✅ allow finalize_comment

    # --------------------------------------------------
    # 3️⃣ Missing operations → EXECUTION FAILURE
    # --------------------------------------------------
    operation_groups = ctx["foorch"].get("operationGroups")

    if not operation_groups:
        ctx.log("❌ FOORCH operations data is missing")
        ctx.stop()
        return ctx

    # --------------------------------------------------
    # 4️⃣ NORMAL FLOW
    # --------------------------------------------------
    ctx["operations"] = operation_groups
    ctx["country"] = country

    ctx.log(f"✅ FOORCH retrieved successfully for country {country}")
    return ctx
