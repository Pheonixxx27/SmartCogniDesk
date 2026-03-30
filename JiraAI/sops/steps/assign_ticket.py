import os
from urllib.parse import urljoin
from collections import Counter

JIRA_BASE_URL = os.getenv("JIRA_URL")
JIRA_USERNAME = os.getenv("JIRA_USERNAME")

# ──────────────────────────────────────────────────────────────
# Executor → Resolving Team mapping
# ──────────────────────────────────────────────────────────────
EXECUTOR_TO_TEAM = {
    "THREE_PL":        "Dfl-3PI Aggregator",
    "FALABELLA_GROUP": "Geo-Dfl Support",
    "BKST":            "Backstore Support",
    "BACKSTORE":       "Backstore Support",
    "BKSM":            "Backstore Support",
    "WHS":             "WHS",   # special: comment + close
}

# Executors that use trackingId instead of packageTrackingRef
TRACKING_ID_EXECUTORS = {"BKST", "BACKSTORE", "BKSM"}

# Display names used in "Dear <team>" comment
EXECUTOR_TEAM_DISPLAY = {
    "THREE_PL":        "3PL",
    "FALABELLA_GROUP": "GeoSort",
    "BKST":            "BackStore",
    "BACKSTORE":       "BackStore",
    "BKSM":            "BackStore",
}

# Jira custom field ID for "Holding Equipo Resolutor" (Holding Resolving Team)
HOLDING_RESOLVING_TEAM_FIELD = "customfield_30027"


# ──────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────

def _normalize_executor(raw):
    """Map raw executor strings to known keys."""
    upper = str(raw).upper()
    if "THREE_PL" in upper or "3PL" in upper:
        return "THREE_PL"
    if "FALABELLA_GROUP" in upper or "FALABELLA GROUP" in upper or "GEO" in upper:
        return "FALABELLA_GROUP"
    if "BKSM" in upper:
        return "BKSM"
    if "BKST" in upper or "BACKSTORE" in upper:
        return "BKST"
    if "WHS" in upper or "WAREHOUSE" in upper:
        return "WHS"
    return upper


def _get_majority_executor(ctx):
    """
    Collect all executors across LMP + RECCP packages.
    Returns the majority executor type (normalized key).
    """
    executor_counts = Counter()

    # ── LMP ──
    lmp_data = ctx.get("lmp_data") or {}
    lmp_executor = lmp_data.get("executorRef", "")
    if lmp_executor:
        normalized = _normalize_executor(lmp_executor)
        packages = lmp_data.get("packages", [])
        executor_counts[normalized] += len(packages) if packages else 1

    # ── RECCP ──
    reccp_data = ctx.get("reccp_data") or {}
    for pkg in reccp_data.get("packages", []):
        carrier = pkg.get("carrier") or pkg.get("executorRef") or ""
        if carrier:
            executor_counts[_normalize_executor(carrier)] += 1

    # ── Blocker packages (fallback) ──
    blocker = ctx.get("blocker") or {}
    for pkg in blocker.get("details", {}).get("packages", []):
        ex = pkg.get("executor", "")
        if ex:
            executor_counts[_normalize_executor(ex)] += 1

    if not executor_counts:
        return None

    majority = executor_counts.most_common(1)[0][0]
    ctx.log(f"📊 Executor counts: {dict(executor_counts)} → majority: {majority}")
    return majority


def _collect_tracking_refs(ctx, executor_key):
    """Collect all tracking refs/ids for the majority executor."""
    refs = []
    use_tracking_id = executor_key in TRACKING_ID_EXECUTORS

    # From LMP
    lmp_data = ctx.get("lmp_data") or {}
    for pkg in lmp_data.get("packages", []):
        if use_tracking_id:
            ref = pkg.get("trackingId") or pkg.get("packageTrackingReference")
        else:
            ref = pkg.get("packageTrackingReference")
        if ref:
            refs.append(ref)

    # From RECCP
    reccp_data = ctx.get("reccp_data") or {}
    for pkg in reccp_data.get("packages", []):
        for td in pkg.get("trackingData", []):
            number = td.get("number")
            if number:
                refs.append(number)

    # From blocker packages (fallback)
    blocker = ctx.get("blocker") or {}
    for pkg in blocker.get("details", {}).get("packages", []):
        ref = pkg.get("trackingId") if use_tracking_id else pkg.get("tracking")
        if ref and ref not in refs:
            refs.append(ref)

    return list(dict.fromkeys(refs))  # deduplicate, preserve order


def _build_assignment_comment(executor_key, tracking_refs):
    """Build the 'Dear <team>' assignment comment."""
    display = EXECUTOR_TEAM_DISPLAY.get(executor_key, executor_key)
    ref_label = "trackingIds" if executor_key in TRACKING_ID_EXECUTORS else "packageTrackingRefs"
    refs_str = "\n".join(f"  - {r}" for r in tracking_refs) if tracking_refs else "  - N/A"

    return (
        f"Dear {display} team,\n\n"
        f"Please help with the status of the following {ref_label}:\n"
        f"{refs_str}\n\n"
        f"Thank you."
    )


def _post_comment(jira, issue_key, comment, ctx):
    """Post a comment to the Jira ticket."""
    try:
        url = urljoin(JIRA_BASE_URL, f"/rest/api/2/issue/{issue_key}/comment")
        resp = jira.post(url, json={"body": comment})
        if resp.status_code in (200, 201):
            ctx.log("✅ Comment posted successfully")
        else:
            ctx.log(f"❌ Failed to post comment: {resp.status_code} {resp.text}")
    except Exception as e:
        ctx.log(f"❌ Exception posting comment: {e}")


def _assign_to_me(jira, issue_key, ctx):
    """Assign ticket to the configured JIRA user."""
    try:
        url = urljoin(JIRA_BASE_URL, f"/rest/api/2/issue/{issue_key}/assignee")
        resp = jira.put(url, json={"name": JIRA_USERNAME})
        if resp.status_code in (200, 201, 204):
            ctx.log(f"✅ Ticket assigned to {JIRA_USERNAME}")
        else:
            ctx.log(f"❌ Failed to assign ticket: {resp.status_code} {resp.text}")
    except Exception as e:
        ctx.log(f"❌ Exception assigning ticket: {e}")


def _transition_ticket(jira, issue_key, transition_name, ctx):
    """Transition the Jira ticket to a given state by name."""
    try:
        url = urljoin(JIRA_BASE_URL, f"/rest/api/2/issue/{issue_key}/transitions")
        resp = jira.get(url)
        if resp.status_code != 200:
            ctx.log(f"❌ Failed to get transitions: {resp.status_code}")
            return False

        transitions = resp.json().get("transitions", [])
        match = next(
            (t for t in transitions if t["name"].lower() == transition_name.lower()),
            None
        )

        if not match:
            available = [t["name"] for t in transitions]
            ctx.log(f"⚠️ Transition '{transition_name}' not found. Available: {available}")
            return False

        t_resp = jira.post(url, json={"transition": {"id": match["id"]}})
        if t_resp.status_code in (200, 201, 204):
            ctx.log(f"✅ Ticket transitioned to '{transition_name}'")
            return True
        else:
            ctx.log(f"❌ Transition failed: {t_resp.status_code} {t_resp.text}")
            return False

    except Exception as e:
        ctx.log(f"❌ Exception transitioning ticket: {e}")
        return False


def _update_resolving_team(jira, issue_key, team_name, ctx):
    """Update the Holding Resolving Team custom field."""
    try:
        url = urljoin(JIRA_BASE_URL, f"/rest/api/2/issue/{issue_key}")
        payload = {"fields": {HOLDING_RESOLVING_TEAM_FIELD: {"value": team_name}}}
        resp = jira.put(url, json=payload)
        if resp.status_code in (200, 201, 204):
            ctx.log(f"✅ Holding Resolving Team set to '{team_name}'")
        else:
            ctx.log(f"⚠️ Could not set Holding Resolving Team: {resp.status_code} {resp.text}")
    except Exception as e:
        ctx.log(f"⚠️ Exception updating Holding Resolving Team: {e}")


def _close_ticket(jira, issue_key, ctx):
    """Full close flow: Assign to me → In Progress → Cancelled."""
    ctx.log("🔒 Close flow: Assign → In Progress → Cancelled")
    _assign_to_me(jira, issue_key, ctx)
    _transition_ticket(jira, issue_key, "In Progress", ctx)
    _transition_ticket(jira, issue_key, "Cancelled", ctx)


# ──────────────────────────────────────────────────────────────
# Main step entry point
# ──────────────────────────────────────────────────────────────

def execute(ctx):
    ctx.log("🎯 STEP: ASSIGN_TICKET")

    jira = ctx.get("jira")
    issue_key = ctx.get("issue_key")

    if not jira or not issue_key:
        ctx.log("⚠️ Missing jira or issue_key → skipping")
        return ctx

    # ── CASE 1: FO already in terminal state ──────────────────
    blocker = ctx.get("blocker") or {}
    if blocker.get("type") == "FOORCH_TERMINAL":
        fo_id = blocker.get("details", {}).get("fo_id", "")
        status = blocker.get("details", {}).get("status", "")
        ctx.log(f"⚠️ FO {fo_id} is terminal ({status}) → comment + close")

        comment = (
            f"Dear Team,\n\n"
            f"The Fulfillment Order *{fo_id}* is already in a terminal state: *{status}*.\n"
            f"No further operational action is required.\n\n"
            f"This ticket will be closed automatically."
        )
        _post_comment(jira, issue_key, comment, ctx)
        _close_ticket(jira, issue_key, ctx)
        ctx["ticket_assigned"] = "CLOSED_TERMINAL"
        return ctx

    # ── CASE 2: Determine majority executor ───────────────────
    executor_key = _get_majority_executor(ctx)

    if not executor_key:
        ctx.log("⚠️ No executor found in context → skipping assignment")
        return ctx

    team = EXECUTOR_TO_TEAM.get(executor_key)
    ctx.log(f"🏷️ Majority executor: {executor_key} → Resolving team: {team}")

    # ── CASE 3: WHS → comment + close ────────────────────────
    if executor_key == "WHS":
        ctx.log("🏭 WHS executor → posting warehouse comment and closing ticket")
        comment = (
            "Dear Team,\n\n"
            "This order is being handled by the *Warehouse (WHS)* team.\n"
            "Please contact the Warehouse team directly for further assistance.\n\n"
            "This ticket will be closed automatically."
        )
        _post_comment(jira, issue_key, comment, ctx)
        _close_ticket(jira, issue_key, ctx)
        ctx["ticket_assigned"] = "CLOSED_WHS"
        return ctx

    # ── CASE 4: Assign to team + post Dear comment ────────────
    tracking_refs = _collect_tracking_refs(ctx, executor_key)
    comment = _build_assignment_comment(executor_key, tracking_refs)

    ctx.log(f"📝 Posting assignment comment to {team}...")
    _post_comment(jira, issue_key, comment, ctx)

    ctx.log(f"🔧 Updating Holding Resolving Team → '{team}'...")
    _update_resolving_team(jira, issue_key, team, ctx)

    ctx["ticket_assigned"] = team
    ctx.log(f"✅ Ticket assigned to '{team}'")

    return ctx
