from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor, as_completed
from JiraAI.engine.engine import run

BATCH_SIZE = 10
MAX_WORKERS = 5


def execute(ctx):
    ctx.log("🔁 STEP: DISPATCH_IDS (Parallel batch execution)")

    ids = ctx.get("ids", {})
    source_ids = ids.get("source_order_ids", [])
    fo_ids = ids.get("fo_ids", [])

    driving_ids = fo_ids if fo_ids else source_ids

    if not driving_ids:
        raise RuntimeError("DISPATCH_IDS: No IDs to dispatch (hard stop)")

    batches = [
        driving_ids[i:i + BATCH_SIZE]
        for i in range(0, len(driving_ids), BATCH_SIZE)
    ]

    ctx.log(f"📦 {len(driving_ids)} IDs → {len(batches)} batch(es)")

    sop_steps = ctx["__sop_steps__"]
    current_index = ctx["__step_index__"]

    if current_index + 1 >= len(sop_steps):
        raise RuntimeError("DISPATCH_IDS: No remaining steps after dispatch")

    remaining_steps = sop_steps[current_index + 1:]

    # ✅ parent aggregation bucket
    ctx["batch_results"] = []

    def process_single_id(single_id):
        child = ctx.spawn_child()
        child["__is_child__"] = True
        child["current_id"] = single_id

        child["ids"] = {
            "fo_ids": [single_id] if str(single_id).startswith("FOF") else [],
            "source_order_ids": [single_id] if str(single_id).isdigit() else [],
            "lpn_ids": [],
            "unknown_ids": [],
        }

        child.log(f"▶️ Processing ID → {single_id}")

        run(child, {
            "name": ctx.get("__sop_name__"),
            "steps": remaining_steps,
        })

        # 🔥🔥🔥 CRITICAL FIX: PROMOTE CHILD EVENTS & LOGS 🔥🔥🔥
        ctx.events.extend(child.events)
        ctx.logs.extend(child.logs)

        return {
            "id": single_id,
            "blocked_by": child.get("blocked_by"),
            "executor_comments": child.get("executor_comments", []),
        }

    for batch_no, batch in enumerate(batches, start=1):
        ctx.log(f"🚀 Executing batch {batch_no}: {batch}")

        results = []

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(process_single_id, i) for i in batch]
            for future in as_completed(futures):
                results.append(future.result())

        # 🔒 VALIDATE CHILD CONTRACT (CORRECT)
        for r in results:
            if r.get("blocked_by") and "executor_comments" not in r:
                raise RuntimeError(
                    f"DISPATCH_IDS: executor_comments missing for "
                    f"blocked ID {r['id']} ({r['blocked_by']})"
                )

        ctx["batch_results"].extend(results)

    ctx.log("⛔ Parent execution completed after parallel dispatch")
    return ctx
