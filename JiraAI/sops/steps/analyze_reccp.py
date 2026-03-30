import requests

TERMINAL_TASK_STATES = {"COMPLETED", "CANCELLED"}


def execute(ctx):
    ctx.log("📦 STEP: ANALYZE_RECCP")

    operations = ctx.get("operations", [])
    country = ctx.get("country")

    if not country:
        return ctx

    # 1️⃣ Locate RECCP
    reccp_id = None
    reccp_op = None
    for group in operations:
        for op in group.get("operationsInfo", []):
            if op.get("operationCode") == "RECCP":
                reccp_id = op.get("operationId")
                reccp_op = op
                break
        if reccp_id:
            break
        if not reccp_op or reccp_op.get("operationCreated") != "SUCCESS":
          return ctx

        if not reccp_id:
         return ctx

    # 2️⃣ Fetch RECCP
    url = f"https://localhost:8082/receive-and-collect/api/v1/receive-and-collect/{reccp_id}"
    headers = {"x-commerce": "FAL", "x-country": country}

    resp = requests.get(url, headers=headers, timeout=10, verify=False)
    if resp.status_code != 200:
        return ctx

    data = resp.json()
    
    # Store raw API response for integrity checks
    ctx["reccp_data"] = data
    
    packages = data.get("packages", [])

    actionable = []
    all_terminal = True

    # 3️⃣ Analyze tracking data
    for pkg in packages:
        for td in pkg.get("trackingData", []):
            state = td.get("status")
            executor = td.get("carrierName")
            tracking = td.get("number")

            if not tracking or not executor:
                continue

            if state not in TERMINAL_TASK_STATES:
                all_terminal = False
                actionable.append({
                    "tracking": tracking,
                    "executor": executor,
                    "state": state,
                    "reccp_id": reccp_id,
                })

    # 4️⃣ Informational only
    if all_terminal:
        ctx["blocker"] = {
            "type": "RECCP_INFO",
            "country": country,
            "details": {
                "reccp_id": reccp_id
            },
        }
        return ctx

    # 5️⃣ Actionable
    if actionable:
        ctx["blocker"] = {
            "type": "RECCP",
            "country": country,
            "details": {
                "reccp_id": reccp_id,
                "packages": actionable,
            },
        }
        # Store for integrity check
        ctx["reccp_blocker"] = ctx["blocker"]

    return ctx
