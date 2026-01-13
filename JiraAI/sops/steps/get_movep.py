import requests

def execute(ctx):
    ctx.log("🔁 STEP: GET_MOVEP (recheck)")

    movep = ctx.get("movep")
    if not movep:
        return ctx

    movep_id = movep.get("operationId")
    country = ctx.get("country", "PE")

    url = f"https://localhost:8082/movement-operation/movement-operations/{movep_id}"

    resp = requests.get(
        url,
        headers={
            "x-country": country,
            "x-commerce": "FALABELLA",
        },
        timeout=10,
        verify=False,
    )

    if resp.status_code == 200:
        ctx["movep"] = resp.json()

    return ctx
