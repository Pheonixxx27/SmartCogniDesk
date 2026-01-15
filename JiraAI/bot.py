# JiraAI/bot.py

from collections import defaultdict
from pathlib import Path
import yaml

from JiraAI.engine.util import normalize
from JiraAI.engine.engine import run
from JiraAI.engine.context import ExecutionContext
from JiraAI.engine.jira_scanner import scan_queue
from JiraAI.sops.steps.planner import plan_sop

# =====================================================
# GLOBAL STATS
# =====================================================

SOP_STATS = defaultdict(int)

# =====================================================
# PATHS
# =====================================================

BASE_DIR = Path(__file__).resolve().parent
SOP_DIR = BASE_DIR / "sops"

# =====================================================
# LOAD SOP DEFINITIONS
# =====================================================

def load_sops():
    registry_path = SOP_DIR / "registry.yaml"

    if not registry_path.exists():
        raise FileNotFoundError(f"❌ SOP registry not found: {registry_path}")

    with open(registry_path, "r") as f:
        reg = yaml.safe_load(f)

    if not reg or "sops" not in reg:
        raise ValueError("❌ Invalid registry.yaml (missing 'sops')")

    sops = {}

    for entry in reg["sops"]:
        sop_file = SOP_DIR / entry["file"]

        if not sop_file.exists():
            raise FileNotFoundError(f"❌ SOP file not found: {sop_file}")

        with open(sop_file, "r") as sf:
            sop_data = yaml.safe_load(sf)

        sops[sop_data["name"]] = sop_data

    print(f"✅ Loaded SOPs: {list(sops.keys())}")
    return sops


SOPS = load_sops()

# =====================================================
# TICKET HANDLER
# =====================================================

def handle_ticket(ticket, jira_session):
    """
    One Jira ticket → one ExecutionContext → one SOP execution
    """
    tier2 = normalize(ticket.tier2_text or "")
    sop_name = plan_sop(tier2, SOPS)

    if not sop_name:
        SOP_STATS["NO_MATCH"] += 1
        print(f"❌ No SOP matched → {ticket.key}")
        return

    print(f"✅ SOP matched → {sop_name} | Ticket: {ticket.key}")
    SOP_STATS[sop_name] += 1

    # --------------------------------------------------
    # Execution Context (AUTHORITATIVE STATE)
    # --------------------------------------------------
    ctx = ExecutionContext(
        issue_key=ticket.key,
        description=ticket.description or "",
        detail=ticket.detail or "",
        attachments=ticket.attachments or [],
        jira_session=jira_session,

        # Shared lifecycle state
        comments=[],
        intent=None,
        intent_confidence=None,
        intent_reason=None,
    )
    ctx["ticket"] = ticket.key
    ctx["jira"] = jira_session    # raw ticket object

    # --------------------------------------------------
    # Emit SOP_SELECTED (NOW ctx exists ✅)
    # --------------------------------------------------
    ctx.emit_event(
        "SOP_SELECTED",
        {
            "sop": sop_name,
        }
    )

    # --------------------------------------------------
    # Run SOP
    # --------------------------------------------------
    run(ctx, SOPS[sop_name])


# =====================================================
# MAIN
# =====================================================

def main():
    print("🔍 Fetching Jira queue...")

    tickets, jira_session = scan_queue()  # UPDATED CONTRACT

    for ticket in tickets:
        handle_ticket(ticket, jira_session)

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------
    print("\n🧠 AI Planner Summary")
    print("=" * 30)

    for sop, count in SOP_STATS.items():
        if sop == "NO_MATCH":
            print(f"❌ No SOP matched → {count} tickets")
        else:
            print(f"✅ {sop} → {count} tickets")


if __name__ == "__main__":
    main()
