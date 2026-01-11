def execute(ctx):
    ctx.log("🧾 STEP: FINALIZE_COMMENT (child)")

    # --------------------------------------------------
    # SAFETY 0️⃣: issue_key MUST exist (CRITICAL)
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
    # 🔕 INFO-ONLY BLOCKERS → SILENT EXIT (DO NOT EMIT)
    # --------------------------------------------------
    if t in ("LMP_INFO", "RECCP_INFO"):
        ctx.log(f"ℹ️ Informational blocker {t} → no executor comment")
        ctx["executor_comments"] = []
        return ctx

    executor_map = {}  # executor → list[str]

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

    # ================= FOORCH TERMINAL =================
    elif t == "FOORCH_TERMINAL":
        add(
            "INFO",
            f"Order {d.get('fo_id')} is already in terminal state: "
            f"{d.get('status')}."
        )
        add("INFO", "No operational action required.")

    # ================= SAFETY NET =================
    else:
        add(
            "UNKNOWN",
            f"Blocking operation detected ({t}). Manual review required."
        )

    # --------------------------------------------------
    # EMIT EVENTS — ONE PER EXECUTOR (CORRECT & SAFE)
    # --------------------------------------------------
    all_comments = []

    for executor, lines in executor_map.items():
        all_comments.append(f"Executor {executor}:")
        for l in lines:
            all_comments.append(f" - {l}")

        # 🔑 ticket is injected by emit_event via issue_key
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

    return ctx
