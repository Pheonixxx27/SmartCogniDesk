import requests


def execute(ctx):
    ctx.log("🚚 STEP: ANALYZE_MOVEP")

    operations = ctx.get("operations", [])
    country = ctx.get("country")

    if not country:
        return ctx

    movep_op = None
    for group in operations:
        for op in group.get("operationsInfo", []):
            if op.get("operationCode") == "MOVEP":
                movep_op = op
                break
        if movep_op:
            break

    if not movep_op or movep_op.get("operationCreated") != "SUCCESS":
        return ctx

    movep_id = movep_op.get("operationId")
    if not movep_id:
        return ctx

    url = f"https://localhost:8082/movement-operation/movement-operations/{movep_id}"
    headers = {"x-country": country, "x-commerce": "FAL"}

    resp = requests.get(url, headers=headers, timeout=10, verify=False)
    if resp.status_code != 200:
        return ctx

    data = resp.json()
    nodes = data.get("reservationDetails", {}).get("transferNodes", [])

    blockers = []

    for node in nodes:
        pkg_infos = node.get("packageNodeInfo", [])
        for pkg in pkg_infos:
            seq = node.get("sequence")
            executor = node.get("executorRef")

            if pkg.get("receptionTask", {}).get("state") == "ACCEPTED":
                blockers.append(("RECEPTION", executor, seq))

            if pkg.get("dispatchTask", {}).get("state") == "ACCEPTED":
                blockers.append(("DISPATCH", executor, seq))

    if blockers:
        ctx["blocker"] = {
            "type": "MOVEP",
            "country": country,
            "details": {
                "tasks": blockers
            },
        }

    return ctx
