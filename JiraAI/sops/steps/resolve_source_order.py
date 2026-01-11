import requests

COUNTRY_FALLBACK = ["PE", "CL", "CO"]


def execute(ctx):
    ctx.log("🔄 STEP: RESOLVE_SOURCE_ORDER")

    ids = ctx.get("ids", {})

    # ----------------------------------
    # 1️⃣ FO already present → done
    # ----------------------------------
    if ids.get("fo_ids"):
        ctx["fo_id"] = ids["fo_ids"][0]
        ctx.log(f"🆔 FO ID already present → {ctx['fo_id']}")
        return ctx

    # ----------------------------------
    # 2️⃣ Try Source Order
    # ----------------------------------
    if ids.get("source_order_ids"):
        source_id = ids["source_order_ids"][0]
    else:
        source_id = None

    # ----------------------------------
    # 3️⃣ Country resolution order
    # ----------------------------------
    tried_countries = []
    countries = []

    if ctx.get("country"):
        countries.append(ctx["country"])

    for c in COUNTRY_FALLBACK:
        if c not in countries:
            countries.append(c)

    # ----------------------------------
    # 4️⃣ Resolve via Source Order
    # ----------------------------------
    if source_id:
        for country in countries:
            tried_countries.append(country)
            ctx.log(f"🌍 Trying Source Order in {country}")

            url = (
                "https://localhost:8082/"
                f"fulfilment-order/fulfilment-logistic-order/source-order/{source_id}"
            )

            headers = {
                "x-commerce": "FAL",
                "x-country": country,
            }

            try:
                resp = requests.get(url, headers=headers, timeout=10, verify=False)
            except Exception as e:
                ctx.log(f"⚠️ Connection error in {country} → {e}")
                continue

            if resp.status_code != 200:
                continue

            data = resp.json()
            fo_id = data.get("logisticOrderId")

            if fo_id:
                ctx["fo_id"] = fo_id
                ctx["country"] = country
                ctx.log(f"✅ Source Order resolved → FO ID = {fo_id} ({country})")
                return ctx

    # ----------------------------------
    # 5️⃣ Resolve via LPN (NEW)
    # ----------------------------------
    if ids.get("lpn_ids"):
        lpn = ids["lpn_ids"][0]
        ctx.log(f"📦 Trying LPN resolution → {lpn}")

        for country in countries:
            url = (
                "https://localhost:8082/"
                f"logistic-packages/?packageLpnValue={lpn}"
            )

            headers = {
                "x-commerce": "FALABELLA",
                "x-country": country,
            }

            try:
                resp = requests.get(url, headers=headers, timeout=10, verify=False)
            except Exception as e:
                ctx.log(f"⚠️ LPN connection error in {country} → {e}")
                continue

            if resp.status_code != 200:
                continue

            pkgs = resp.json()
            if not pkgs:
                continue

            order_ref = pkgs[0].get("orderRefId")
            if not order_ref:
                continue

            ctx.log(f"🔁 LPN resolved to orderRefId → {order_ref}")

            # Reuse FOORCH
            foorch_url = (
                "https://localhost:8082/"
                f"fulfilment-order-orchestrator/api/v1/"
                f"fulfilment-logistic-orchestrator/{order_ref}"
            )

            foorch_resp = requests.get(
                foorch_url, headers=headers, timeout=10, verify=False
            )

            if foorch_resp.status_code != 200:
                continue

            ctx["fo_id"] = order_ref
            ctx["country"] = country
            ctx.log(f"✅ FO resolved via LPN → {order_ref} ({country})")
            return ctx

    # ----------------------------------
    # 6️⃣ Failed everywhere
    # ----------------------------------
    ctx.log("❌ Unable to resolve FO via FO / Source Order / LPN")

    ctx["blocker"] = {
        "type": "SOURCE_ORDER_NOT_FOUND",
        "details": {
            "source_order_id": source_id,
            "lpn": ids.get("lpn_ids"),
        },
    }
    return ctx
