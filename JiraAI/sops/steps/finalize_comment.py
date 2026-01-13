import json

def execute(ctx):
    ctx.log("🧾 STEP: FINALIZE_COMMENT (child)")

    # --------------------------------------------------
    # SAFETY 0️⃣: issue_key MUST exist
    # --------------------------------------------------
    issue_key = ctx.get("issue_key")
    if not issue_key:
        ctx.log("❌ issue_key missing → cannot emit executor comments")
        ctx["executor_comments"] = []
        return ctx

    # --------------------------------------------------
    # SAFETY 1️⃣: Do NOT overwrite existing comments
    # --------------------------------------------------
    if ctx.get("executor_comments"):
        ctx.log("ℹ️ Executor comments already present → skipping child finalize")
        return ctx

    # --------------------------------------------------
    # SAFETY 2️⃣: No blocker → nothing to comment
    # --------------------------------------------------
    blocker = ctx.get("blocker")
    if not blocker:
        ctx.log("ℹ️ No blocker → skipping child finalize")
        ctx["executor_comments"] = []
        return ctx

    t = blocker.get("type")
    d = blocker.get("details", {})

    # --------------------------------------------------
    # 🔕 INFO-ONLY BLOCKERS → SILENT EXIT
    # --------------------------------------------------
    if t in ("LMP_INFO", "RECCP_INFO"):
        ctx.log(f"ℹ️ Informational blocker {t} → no executor comment")
        ctx["executor_comments"] = []
        return ctx

    executor_map = {}

    def add(executor, line):
        executor_map.setdefault(executor, []).append(line)

    # ================= MOVEP =================
    if t == "MOVEP":
        sequence = d.get("sequence")
        task = d.get("task")
        executor = d.get("executor")

        if sequence and task and executor:
            add(
                executor,
                f"MOVEP blocked at node sequence {sequence}. "
                f"{task} task is ACCEPTED."
            )

    # ================= LMP =================
    elif t == "LMP":
        packages = d.get("packages", [])
        lmp_id = d.get("lmp_id")
        actionable = False

        for p in packages:
            executor = p.get("executor")
            state = p.get("state")
            tracking = p.get("tracking")

            if not executor or state in ("DELIVERED", "CANCELLED"):
                continue

            actionable = True
            add(
                executor,
                f"LMP{f' - {lmp_id}' if lmp_id else ''} | "
                f"packageTrackingRef {tracking} in state {state} "
                f"belongs to {executor}"
            )

        if not actionable:
            add(
                "INFO",
                "All Last Mile packages are already delivered or cancelled. "
                "No action required."
            )

    # ================= RECCP =================
    elif t == "RECCP":
        packages = d.get("packages", [])
        reccp_id = d.get("reccp_id")
        actionable = False

        for p in packages:
            executor = p.get("executor")
            task = p.get("task")
            tracking = p.get("tracking")
            status = p.get("status")

            if not executor or status in ("COMPLETED", "CANCELLED"):
                continue

            actionable = True
            add(
                executor,
                f"RECCP{f' - {reccp_id}' if reccp_id else ''} | "
                f"{task} pending for packageTrackingRef {tracking} "
                f"(state: {status}) belongs to {executor}"
            )

        if not actionable:
            add(
                "INFO",
                "All Reception tasks are already completed or cancelled. "
                "No action required."
            )

    # ================= PIDDP =================
    elif t == "PIDDP":
        executor = d.get("executor")
        state = d.get("state")
        piddp_id = d.get("piddp_id")

        if executor:
            add(
                executor,
                f"PIDDP {piddp_id} is in state {state} "
                f"and belongs to {executor}."
            )

    # ================= PIDDP AWAITING SHIPMENT =================
    elif t == "PIDDP_AWAITING_SHIPMENT_CONFIRMATION":
        executor = d.get("executor", "UNKNOWN")
        fo_id = d.get("fo_id")
        piddp_id = d.get("piddp_id")

        if not ctx.get("asn_do_excel"):
            ctx["asn_do_excel"] = {
                "file": "N/A",
                "reason": "Awaiting shipment confirmation",
            }

        add(executor, f"Shipment confirmation pending for FO {fo_id}.")
        add(
            executor,
            f"PIDDP {piddp_id} is active and has not yet received shipment confirmation."
        )
        add(
            executor,
            "Please confirm shipment to allow ASN / DO crossdock processing."
        )

    # ================= FOORCH TERMINAL =================
    elif t == "FOORCH_TERMINAL":
        add(
            "INFO",
            f"Order {d.get('fo_id')} is already in terminal state: "
            f"{d.get('status')}."
        )
        add("INFO", "No operational action required.")

    # ================= ASN / DO CROSSDOCK =================
    elif t == "ASN_DO_FAILED":
        fo_id = d.get("fo_id")
        failure_count = d.get("failure_count", 0)
        excel = ctx.get("asn_do_excel")
        movep = ctx.get("movep", {})

        executors = set()

        try:
            payload = movep.get("payload")
            if isinstance(payload, str):
                payload = json.loads(payload)

            nodes = (
                payload
                .get("reservationDetails", {})
                .get("transferNodes", [])
            )

            for node in nodes:
                executor = node.get("executorRef")
                if executor:
                    executors.add(executor)

        except Exception:
            pass

        if not executors:
            executors.add("UNKNOWN")

        for executor in executors:
            add(
                executor,
                f"ASN / DO Crossdock flow failed for FO {fo_id}."
            )
            add(
                executor,
                f"{failure_count} blocking task(s) detected during crossdock validation."
            )

            if excel:
                add(
                    executor,
                    f"Detailed failure report generated in Excel file: {excel.get('file')}."
                )

    # ================= SAFETY NET =================
    else:
        add(
            "UNKNOWN",
            f"Blocking operation detected ({t}). Manual review required."
        )

    # --------------------------------------------------
    # EMIT EVENTS
    # --------------------------------------------------
    all_comments = []

    for executor, lines in executor_map.items():
        all_comments.append(f"Executor {executor}:")
        for l in lines:
            all_comments.append(f" - {l}")

        ctx.emit_event(
            "EXECUTOR_COMMENT",
            {
                "executor": executor,
                "comments": lines,
                "country": ctx.get("country"),
                "sop": ctx.get("__sop_name__"),
            }
        )

    ctx["executor_comments"] = all_comments
    ctx.log(f"🧩 Child executor comments → {all_comments}")

    # --------------------------------------------------
    # ✅ NEW: STOP SOP *AFTER* COMMENTS IF REQUIRED
    # --------------------------------------------------
    if ctx.get("stop_after_finalize"):
        ctx.log("⛔ SOP stopped after finalize_comment")
        ctx.stop()

    return ctx
