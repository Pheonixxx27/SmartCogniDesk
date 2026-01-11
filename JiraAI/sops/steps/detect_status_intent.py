import ollama
import json
import re

ALLOWED_INTENTS = {
    "DELIVERED",
    "CANCELLED",
    "STATE_CHANGE",
    "UNKNOWN",
}

# -----------------------------------------
# Helpers
# -----------------------------------------

def extract_json_block(text: str):
    """Safely extract first JSON object from LLM output."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else None


def contains_review_language(text: str) -> bool:
    """
    Presence of these phrases FORBIDS STATE_CHANGE
    """
    text = text.lower()
    review_phrases = [
        # English
        "review",
        "investigate",
        "analyze",

        # Spanish
        "revisando",
        "revisar",
        "validar",
        "verificar",

        # Informational event mentions
        "event sent",
        "evento",
        "fulfilment_order_packages_annulled",
        "fo_items_annulled",
        "fulfilment_order_item_quantity_dispatched",
        "order_360_new_promise_date_event",
    ]
    return any(p in text for p in review_phrases)


# -----------------------------------------
# Main Step
# -----------------------------------------

def execute(ctx):
    ctx.log("🧠 STEP: DETECT_INTENT (LLM)")

    text = (
        ctx.get("description", "") + "\n" +
        ctx.get("detail", "")
    ).strip()

    if not text:
        ctx["intent"] = "UNKNOWN"
        ctx["intent_confidence"] = "HIGH"
        ctx["intent_reason"] = "No textual content available"
        ctx.log("⚠️ No text available → intent UNKNOWN")

        ctx.emit_event("INTENT_DETECTED", {
            "intent": "UNKNOWN",
            "confidence": "HIGH",
            "reason": "No textual content available",
        })
        return ctx

    # ------------------------------
    # Ask LLM (ADVISORY ONLY)
    # ------------------------------
    prompt = f"""
You are classifying the USER'S INTENT in a Jira ticket.

Rules:
- Reporting an incorrect event is NOT a state change
- Review / investigation → UNKNOWN
- Only STATE_CHANGE if user explicitly asks to change status

Return ONLY JSON. No text outside.

Format:
{{
  "intent": "DELIVERED | CANCELLED | STATE_CHANGE | UNKNOWN",
  "confidence": "HIGH | MEDIUM | LOW",
  "reason": "short explanation"
}}

Ticket text:
{text}
"""

    try:
        res = ollama.chat(
            model="llama3:8b",
            messages=[{"role": "user", "content": prompt}],
        )

        raw = res["message"]["content"].strip()
        ctx.log(f"🧠 LLM intent raw output → {raw}")

        json_block = extract_json_block(raw)
        if not json_block:
            raise ValueError("No JSON object found in LLM output")

        data = json.loads(json_block)
        llm_intent = data.get("intent", "UNKNOWN")

    except Exception as e:
        ctx.log(f"❌ LLM intent detection failed → {e}")
        ctx["intent"] = "UNKNOWN"
        ctx["intent_confidence"] = "LOW"
        ctx["intent_reason"] = "LLM failure"

        ctx.emit_event("INTENT_DETECTED", {
            "intent": "UNKNOWN",
            "confidence": "LOW",
            "reason": "LLM failure",
        })
        return ctx

    # ------------------------------
    # HARD RULE OVERRIDES (AUTHORITATIVE)
    # ------------------------------
    if llm_intent == "STATE_CHANGE" and contains_review_language(text):
        ctx.log("🚫 Review language detected → forcing UNKNOWN")

        ctx["intent"] = "UNKNOWN"
        ctx["intent_confidence"] = "HIGH"
        ctx["intent_reason"] = "Review / investigation request, not an action"

        ctx.emit_event("INTENT_DETECTED", {
            "intent": "UNKNOWN",
            "confidence": "HIGH",
            "reason": "Review language detected, STATE_CHANGE forbidden",
        })
        return ctx

    # ------------------------------
    # Final validation
    # ------------------------------
    if llm_intent not in ALLOWED_INTENTS:
        ctx.log(f"⚠️ Invalid intent from LLM → {llm_intent}")

        ctx["intent"] = "UNKNOWN"
        ctx["intent_confidence"] = "LOW"
        ctx["intent_reason"] = "Invalid intent value"

        ctx.emit_event("INTENT_DETECTED", {
            "intent": "UNKNOWN",
            "confidence": "LOW",
            "reason": "Invalid intent from LLM",
        })
        return ctx

    ctx["intent"] = llm_intent
    ctx["intent_confidence"] = data.get("confidence", "LOW")
    ctx["intent_reason"] = data.get("reason", "")

    ctx.log(f"✅ Intent accepted → {llm_intent}")

    # 🔔 INTENT EVENT
    ctx.emit_event("INTENT_DETECTED", {
        "intent": ctx["intent"],
        "confidence": ctx["intent_confidence"],
        "reason": ctx["intent_reason"],
    })

    return ctx
