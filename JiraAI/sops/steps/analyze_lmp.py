import requests

TERMINAL_PACKAGE_STATES = {"DELIVERED", "CANCELLED", "ANNULLED"}


def execute(ctx):
    ctx.log("📍 STEP: ANALYZE_LMP")

    operations = ctx.get("operations", [])
    country = ctx.get("country")

    if not country:
        return ctx

    # 1️⃣ Locate LMP
    lmp_op = None
    for group in operations:
        for op in group.get("operationsInfo", []):
            if op.get("operationCode") == "LMP":
                lmp_op = op
                break
        if lmp_op:
            break

    if not lmp_op:
        return ctx
    
    if not lmp_op or lmp_op.get("operationCreated") != "SUCCESS":
        return ctx

    lmp_id = lmp_op.get("operationId")
    if not lmp_id:
        return ctx

    # 2️⃣ Fetch LMP
    url = f"https://localhost:8082/last-mile/api/v1/last-mile-operations/{lmp_id}"
    headers = {"x-commerce": "FAL", "x-country": country}

    resp = requests.get(url, headers=headers, timeout=10, verify=False)
    if resp.status_code != 200:
        return ctx

    data = resp.json()
    packages = data.get("packages", [])
    executor = data.get("executorRef")

    actionable = []
    all_terminal = True

    # 3️⃣ Analyze packages
    for pkg in packages:
        state = pkg.get("state")
        tracking = pkg.get("packageTrackingReference")

        if not tracking:
            continue

        if state not in TERMINAL_PACKAGE_STATES:
            all_terminal = False
            actionable.append({
                "tracking": tracking,
                "state": state,
                "executor": executor,
                "lmp_id": lmp_id,
            })

    # 4️⃣ Informational only
    if all_terminal:
        ctx["blocker"] = {
            "type": "LMP_INFO",
            "country": country,
            "details": {
                "lmp_id": lmp_id
            },
        }
        return ctx

    # 5️⃣ Actionable
    if actionable:
        ctx["blocker"] = {
            "type": "LMP",
            "country": country,
            "details": {
                "lmp_id": lmp_id,
                "packages": actionable,
            },
        }

    return ctx
