# sops/steps/handle_unknown_intent.py

from JiraAI.engine.reporting.daily_report import write_unknown_intent

def execute(ctx):
    """
    Handle UNKNOWN intent cases.

    Responsibilities:
    - Write UNKNOWN intent report
    - Stop SOP execution
    """

    ctx.log("🟡 STEP: HANDLE_UNKNOWN_INTENT")

    if ctx.get("intent") != "UNKNOWN":
        ctx.log("ℹ️ Intent is not UNKNOWN → skipping handler")
        return ctx

    # ✅ WRITE UNKNOWN REPORT (ONCE)
    write_unknown_intent(ctx)

    ctx.log("📝 UNKNOWN intent recorded for daily report")

    ctx.stop()
    return ctx
