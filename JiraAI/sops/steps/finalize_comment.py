import json

# Terminal states - packages in these states should not be commented
TERMINAL_STATES = {
    "CANCELLED",
    "DELIVERED",
    "ANNULLED",
    "EXCEPTION",
    "AUCTIONED",
    "RETURNED_TO_ORIGIN",
    "REPACKED",
    "COMPLETED",  # For RECCP
}


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

    # --------------------------------------------------
    # INTEGRITY CHECK: Filter by FALSE_POSITIVE & SOLVED
    # --------------------------------------------------
    integrity_results = ctx.get("integrity_results", {})
    false_positives = integrity_results.get("FALSE_POSITIVE", [])
    solved_case_ids = ctx.get("solved_case_ids", set())
    
    if false_positives:
        # Check if current blocker is for a FALSE_POSITIVE case
        blocker_type = blocker.get("type")
        blocker_details = blocker.get("details", {})
        
        # For LMP/RECCP blockers, check if all packages are FALSE_POSITIVE
        if blocker_type in ("LMP", "RECCP"):
            packages = blocker_details.get("packages", [])
            all_false_positive = True
            
            for pkg in packages:
                pkg_id = pkg.get("tracking")
                is_false_pos = any(fp.get("caseId") == pkg_id for fp in false_positives)
                
                if not is_false_pos:
                    all_false_positive = False
                    break
            
            if all_false_positive and packages:
                ctx.log(f"ℹ️ Integrity: All packages are FALSE_POSITIVE → suppressing comments")
                ctx["executor_comments"] = []
                return ctx
    
    # --------------------------------------------------
    # REFETCHED DATA: Filter out terminal state packages
    # --------------------------------------------------
    # After integrity returns SOLVED, we refetch LMP/RECCP to get updated status
    # Only comment on packages still not in terminal state
    blocker_packages = blocker.get("details", {}).get("packages", [])
    blocker_type = blocker.get("type")
    
    if solved_case_ids and blocker_type in ("LMP", "RECCP"):
        ctx.log(f"🔄 Filtering packages after integrity SOLVED status...")
        active_packages = []
        
        if blocker_type == "LMP":
            lmp_data = ctx.get("lmp_data", {})
            lmp_packages = lmp_data.get("packages", [])
            
            # Build set of tracking refs still not in terminal state
            active_tracking = set()
            for pkg in lmp_packages:
                state = pkg.get("state")
                tracking = pkg.get("packageTrackingReference")
                if tracking and state not in TERMINAL_STATES:
                    active_tracking.add(tracking)
            
            # Keep only active packages in comment
            for pkg in blocker_packages:
                if pkg.get("tracking") in active_tracking:
                    active_packages.append(pkg)
            
            if not active_packages:
                ctx.log(f"✅ All LMP packages reached terminal state after refetch")
                ctx["executor_comments"] = []
                return ctx
            
            ctx.log(f"📝 {len(active_packages)} packages still active from LMP")
        
        elif blocker_type == "RECCP":
            reccp_data = ctx.get("reccp_data", {})
            reccp_packages = reccp_data.get("packages", [])
            
            # Build set of tracking numbers still not in terminal state
            active_tracking = set()
            for pkg in reccp_packages:
                for td in pkg.get("trackingData", []):
                    status = td.get("status")
                    number = td.get("number")
                    if number and status not in TERMINAL_STATES:
                        active_tracking.add(number)
            
            # Keep only active packages in comment
            for pkg in blocker_packages:
                if pkg.get("tracking") in active_tracking:
                    active_packages.append(pkg)
            
            if not active_packages:
                ctx.log(f"✅ All RECCP packages reached terminal state after refetch")
                ctx["executor_comments"] = []
                return ctx
            
            ctx.log(f"📝 {len(active_packages)} packages still active from RECCP")
        
        # Update blocker with only active packages
        if active_packages:
            blocker["details"]["packages"] = active_packages

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

        # Group all LMP packages by executor with all details
        executor_packages = {}
        for p in packages:
            executor = p.get("executor")
            state = p.get("state")
            tracking = p.get("tracking")

            if not executor or state in ("DELIVERED", "CANCELLED"):
                continue

            actionable = True
            if executor not in executor_packages:
                executor_packages[executor] = []
            executor_packages[executor].append({
                "tracking": tracking,
                "state": state
            })

        if actionable:
            # Create single consolidated comment per executor with all packages and states
            for executor, pkgs in executor_packages.items():
                pkg_details = ", ".join([f"{p['tracking']} ({p['state']})" for p in pkgs])
                add(
                    executor,
                    f"LMP{f' - {lmp_id}' if lmp_id else ''} | "
                    f"{len(pkgs)} packages pending: {pkg_details}"
                )
        else:
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

        # Group all RECCP packages by executor (carrier) with all details
        executor_packages = {}
        for p in packages:
            executor = p.get("executor")
            task = p.get("task")
            tracking = p.get("tracking")
            status = p.get("status")

            if not executor or status in ("COMPLETED", "CANCELLED"):
                continue

            actionable = True
            if executor not in executor_packages:
                executor_packages[executor] = []
            executor_packages[executor].append({
                "tracking": tracking,
                "task": task,
                "status": status
            })

        if actionable:
            # Create single consolidated comment per executor with all packages and details
            for executor, pkgs in executor_packages.items():
                pkg_details = ", ".join([f"{p['tracking']} ({p['status']})" for p in pkgs])
                add(
                    executor,
                    f"RECCP{f' - {reccp_id}' if reccp_id else ''} | "
                    f"{len(pkgs)} packages pending: {pkg_details}"
                )
        else:
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

    elif t == "ASN_DO_INFO":
        movep_id = d.get("movep_id")
        add(
            "INFO",
            f"All ASN / DO reception and dispatch tasks are already completed for movement operation {movep_id}."
        )
        add(
            "INFO",
            "No operational action required."
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
