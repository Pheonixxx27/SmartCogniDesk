import requests

def execute(ctx):
    ctx.log("🌐 STEP: GET_FOORCH")

    fo_id = ctx.get("fo_id")
    country = ctx.get("country", "PE")

    url = (
        "https://localhost:8082/"
        f"fulfilment-order-orchestrator-c8/api/v1/fulfilment-logistic-orchestrator/{fo_id}"
    )

    headers = {
        "x-commerce": "FALABELLA",
        "x-country": country,
    }

    resp = requests.get(url, headers=headers, timeout=10, verify=False)

    # 1️⃣ Not found → hard stop
    if resp.status_code != 200:
        ctx.log(f"❌ FO {fo_id} not present in FOORCH")
        ctx.stop()
        return ctx

    ctx["foorch"] = resp.json()
    order_status = ctx["foorch"].get("orderStatus")
    ctx["operations"] = ctx["foorch"].get("operationGroups", [])

    # 2️⃣ Terminal → blocker but NOT stop
    if order_status in ("CANCELLED", "COMPLETED", "COMPLETED_EXCEPTIONS"):
        ctx.log(f"ℹ️ FOORCH in terminal state → {order_status}")
        ctx["blocker"] = {
            "type": "FOORCH_TERMINAL",
            "details": {
                "fo_id": fo_id,
                "status": order_status,
                "country": country,
            },
        }
        return ctx

    # 3️⃣ Missing operations → execution failure
    if not ctx["foorch"].get("operationGroups"):
        ctx.log("❌ FOORCH operations missing")
        ctx.stop()
        return ctx

    ctx["country"] = country
    ctx.log(f"✅ FOORCH retrieved successfully for country {country}")
    return ctx
