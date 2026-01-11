import importlib
import time

from JiraAI.engine.storage.mongo import save_events, save_logs
from JiraAI.engine.reporting.daily_report import (
    write_daily_failure,
    write_unknown_intent,
    write_business_comment,
)


def run(ctx, sop):
    steps = sop.get("steps", [])
    ctx["__sop_name__"] = sop.get("name")
    ctx["__sop_steps__"] = steps

    start_time = time.time()
    stopped = False
    stop_reason = None
    execution_error = None

    # =====================================================
    # SOP STEP EXECUTION LOOP
    # =====================================================
    for idx, step_name in enumerate(steps):
        if ctx.should_stop():
            stopped = True
            stop_reason = ctx.get("intent_reason") or "Execution stopped"
            break

        # ✅ AUTHORITATIVE STEP METADATA
        ctx["__step_index__"] = idx
        ctx["__current_step__"] = step_name

        try:
            mod = importlib.import_module(f"JiraAI.sops.steps.{step_name}")
            ctx = mod.execute(ctx)

        except Exception as e:
            # ❗ Execution error ≠ intent error
            ctx.log(f"❌ Exception in step {step_name} → {e}")
            execution_error = str(e)
            ctx["execution_error"] = execution_error

            stopped = True
            stop_reason = execution_error
            break

        finally:
            # Logs are ephemeral
            if ctx.logs:
                save_logs(ctx.logs)
                ctx.logs.clear()

    duration_ms = int((time.time() - start_time) * 1000)

    # =====================================================
    # SOP LIFECYCLE EVENT
    # =====================================================
    if stopped:
        ctx.emit_event(
            "SOP_STOPPED",
            {
                "ticket": ctx["issue_key"],
                "sop": ctx.get("__sop_name__"),
                "step": ctx.get("__current_step__"),
                "duration_ms": duration_ms,
                "reason": stop_reason,
            },
        )

        # ✅ Execution failure report (NOT intent-based)
        if execution_error:
            write_daily_failure(ctx)

    else:
        ctx.emit_event(
            "SOP_COMPLETED",
            {
                "ticket": ctx["issue_key"],
                "sop": ctx.get("__sop_name__"),
                "duration_ms": duration_ms,
            },
        )

    # =====================================================
    # FINAL COMMENT (AUTHORITATIVE)
    # =====================================================
    if ctx.get("final_comment"):
        event = {
            "type": "FINAL_COMMENT",
            "ticket": ctx["issue_key"],
            "payload": {
                "comment": ctx["final_comment"],
                "blocked_by": ctx.get("blocked_by"),
                "country": ctx.get("country"),
                "sop": ctx.get("__sop_name__"),
            },
        }

        # 1️⃣ Persist event (UI reads this)
        ctx.emit_event(event["type"], event["payload"])

        # 2️⃣ Business report (CSV)
        write_business_comment(event)

    # =====================================================
    # PERSIST EVENTS (ONCE)
    # =====================================================
    if ctx.events:
        save_events(ctx.events)
        ctx.events.clear()

    # =====================================================
    # UNKNOWN INTENT REPORT (LLM ONLY)
    # =====================================================
    if ctx.get("intent") == "UNKNOWN" and not ctx.get("execution_error"):
        write_unknown_intent(ctx)

    return ctx
