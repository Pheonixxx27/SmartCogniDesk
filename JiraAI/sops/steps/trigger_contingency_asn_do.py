import time
import requests

USE_MOCK_CONTINGENCY = True


def mock_call(task, fo_id, node):
    """
    Mock contingency API.
    Always returns success without changing any state.
    """
    return {
        "status_code": 200,
        "task": task,
        "fo_id": fo_id,
        "node": node,
        "mock": True,
    }


def execute(ctx):
    ctx.log("🚨 STEP: TRIGGER_CONTINGENCY_ASN_DO")

    blocker = ctx.get("blocker")
    if not blocker or blocker.get("type") != "ASN_DO_FAILED":
        ctx.log("ℹ️ No ASN_DO_FAILED blocker → skipping contingency")
        return ctx

    failures = ctx.get("asn_do_failures", [])
    if not failures:
        ctx.log("ℹ️ No failures present → skipping contingency")
        return ctx

    country = ctx.get("country", "PE")
    results = []

    for failure in failures:
        task = failure.get("task")
        fo_id = failure.get("fo_id")
        node = failure.get("node")
        state = failure.get("state")

        if not task or not fo_id or node is None:
            results.append({
                **failure,
                "contingency": "SKIPPED",
                "error": "Missing required fields",
            })
            continue

        ctx.log(
            f"📡 Triggering contingency → "
            f"task={task}, FO={fo_id}, node={node}, state={state}"
        )

        try:
            # --------------------------------------------------
            # MOCK MODE (current phase)
            # --------------------------------------------------
            if USE_MOCK_CONTINGENCY:
                resp = mock_call(task, fo_id, node)
                status_code = resp["status_code"]

            # --------------------------------------------------
            # REAL API (future switch)
            # --------------------------------------------------
            else:
                if task == "RECEPTION":
                    url = "https://localhost:8082/contingency/reception"
                    payload = {
                        "foId": fo_id,
                        "nodeSequence": node,
                        "reason": f"ASN failure state={state}",
                    }

                elif task == "DISPATCH":
                    url = "https://localhost:8082/contingency/dispatch"
                    payload = {
                        "foId": fo_id,
                        "nodeSequence": node,
                        "reason": f"DO failure state={state}",
                    }

                else:
                    results.append({
                        **failure,
                        "contingency": "SKIPPED",
                        "error": "Unknown task type",
                    })
                    continue

                headers = {
                    "x-country": country,
                    "x-commerce": "FALABELLA",
                }

                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=10,
                    verify=False,
                )

                status_code = response.status_code

            results.append({
                **failure,
                "contingency": "SUCCESS" if status_code == 200 else "FAILED",
                "status_code": status_code,
            })

        except Exception as e:
            results.append({
                **failure,
                "contingency": "ERROR",
                "error": str(e),
            })
            ctx.log(f"❌ Contingency error → {e}")

    # --------------------------------------------------
    # Persist results (used by Excel + finalize_comment)
    # --------------------------------------------------
    ctx["contingency_results"] = results

    # Small wait so MOVEP can reflect changes in real API later
    time.sleep(5)

    return ctx
