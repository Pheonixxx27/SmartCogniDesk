import ollama
from JiraAI.engine.util import normalize

def plan_sop(tier2_text: str, sops: dict, logger=print):
    """
    SOP planner:
    1️⃣ Rule-based match (authoritative)
    2️⃣ AI suggestion (LOGGING ONLY, never execution)
    """

    tier2 = normalize(tier2_text)
    logger(f"🧭 SOP Planner | Normalized Tier2 = '{tier2}'")

    # --------------------------------------------------
    # 1️⃣ RULE-BASED MATCH (AUTHORITATIVE)
    # --------------------------------------------------
    sop = rule_based_match(tier2, logger)
    if sop:
        logger(f"✅ SOP selected by RULE → {sop}")
        return sop

    # --------------------------------------------------
    # 2️⃣ AI PLANNER (ADVISORY ONLY)
    # --------------------------------------------------
    logger("ℹ️ No rule-based SOP matched")
    logger("🧠 Invoking AI planner (advisory only)")

    sop_names = ", ".join(sops.keys())

    prompt = f"""
You are ONLY suggesting, not deciding.

Category:
"{tier2}"

Valid SOPs:
{ sop_names }

Rules:
- Return EXACTLY one SOP name OR NONE
- No explanations
"""

    try:
        res = ollama.chat(
            model="llama3:8b",
            messages=[{"role": "user", "content": prompt}],
        )
        suggestion = res["message"]["content"].strip()
        logger(f"🧠 AI suggestion → '{suggestion}'")

    except Exception as e:
        logger(f"❌ AI planner error → {e}")
        return None

    # --------------------------------------------------
    # 3️⃣ STRICT IGNORE FOR EXECUTION
    # --------------------------------------------------
    if suggestion not in sops and suggestion != "NONE":
        logger("⚠️ AI suggestion ignored (invalid SOP)")
    else:
        logger("ℹ️ AI suggestion logged for analysis only")

    return None

def rule_based_match(tier2: str, logger=print):
    """
    Deterministic SOP routing.
    This is the ONLY authority for execution.
    """
    if "asn do de crossdock con problemas" in tier2:
        logger("🔎 Rule hit → ASN / DO de Crossdock con Problemas")
        return "ASN / DO de Crossdock con Problemas"

    if "problema cambio de estado" in tier2:
        logger("🔎 Rule hit → Problema Cambio de Estado")
        return "Problema Cambio de Estado"

    return None
