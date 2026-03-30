# 📍 EXACT LOCATIONS OF ALL CHANGES

## 1️⃣ NEW FILE CREATED

### `JiraAI/sops/steps/check_integrity.py` (NEW)
- **Total Lines**: 283
- **Key Functions**:
  - `determine_panel()` - Lines 14-61
  - `collect_packages()` - Lines 64-111
  - `build_integrity_payload()` - Lines 114-159
  - `execute()` - Lines 162-283

---

## 2️⃣ FILE MODIFICATIONS

### A) `JiraAI/sops/cambio_estado.yaml`
**Location**: Lines 7-21 (steps section)

**BEFORE**:
```yaml
steps:
  - find_ids
  - detect_status_intent
  - handle_unknown_intent
  - dispatch_ids  
  - resolve_source_order
  - get_foorch
  - check_piddp
  - analyze_movep_estado
  - analyze_lmp
  - analyze_reccp
  - finalize_comment
  - finalize_comment
  - finalize_comment_parent
  - post_jira_comment
```

**AFTER** (Added line):
```yaml
steps:
  - find_ids
  - detect_status_intent
  - handle_unknown_intent
  - dispatch_ids  
  - resolve_source_order
  - get_foorch
  - check_piddp
  - analyze_movep_estado
  - analyze_lmp
  - analyze_reccp
  - check_integrity          ⭐ NEW LINE
  - finalize_comment
  - finalize_comment
  - finalize_comment_parent
  - post_jira_comment
```

---

### B) `JiraAI/sops/steps/analyze_lmp.py`
**Location**: After line 88 (in the "5️⃣ Actionable" section)

**BEFORE**:
```python
    # 5️⃣ Actionable
    if actionable:
        ctx["blocker"] = {
            "type": "LMP",
            "country": country,
            "details": {
                "lmp_id": lmp_id,
                "packages": actionable,
            },
        }

    return ctx
```

**AFTER** (Added lines):
```python
    # 5️⃣ Actionable
    if actionable:
        ctx["blocker"] = {
            "type": "LMP",
            "country": country,
            "details": {
                "lmp_id": lmp_id,
                "packages": actionable,
            },
        }
        # Store for integrity check
        ctx["lmp_blocker"] = ctx["blocker"]  ⭐ NEW LINES

    return ctx
```

---

### C) `JiraAI/sops/steps/analyze_reccp.py`
**Location**: After line 82 (in the "5️⃣ Actionable" section)

**BEFORE**:
```python
    # 5️⃣ Actionable
    if actionable:
        ctx["blocker"] = {
            "type": "RECCP",
            "country": country,
            "details": {
                "reccp_id": reccp_id,
                "packages": actionable,
            },
        }

    return ctx
```

**AFTER** (Added lines):
```python
    # 5️⃣ Actionable
    if actionable:
        ctx["blocker"] = {
            "type": "RECCP",
            "country": country,
            "details": {
                "reccp_id": reccp_id,
                "packages": actionable,
            },
        }
        # Store for integrity check
        ctx["reccp_blocker"] = ctx["blocker"]  ⭐ NEW LINES

    return ctx
```

---

### D) `JiraAI/sops/steps/finalize_comment.py`
**Location**: Lines 21-56 (NEW safety check before existing code)

**BEFORE**:
```python
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
```

**AFTER** (Added lines 21-56):
```python
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

    # --------------------------------------------------  ⭐ NEW SECTION START
    # INTEGRITY CHECK: Filter by FALSE_POSITIVE
    # --------------------------------------------------
    integrity_results = ctx.get("integrity_results", {})
    false_positives = integrity_results.get("FALSE_POSITIVE", [])
    
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
    # --------------------------------------------------  ⭐ NEW SECTION END

    t = blocker.get("type")
    d = blocker.get("details", {})
```

---

## 🔗 MODIFICATION SUMMARY TABLE

| File | Change Type | Lines | What Changed |
|------|------------|-------|--------------|
| `cambio_estado.yaml` | Modified | 7-21 | Added `check_integrity` step |
| `analyze_lmp.py` | Modified | ~88 | Added `ctx["lmp_blocker"]` assignment |
| `analyze_reccp.py` | Modified | ~82 | Added `ctx["reccp_blocker"]` assignment |
| `finalize_comment.py` | Modified | 21-56 | Added integrity FALSE_POSITIVE filter |
| `check_integrity.py` | Created | 1-283 | NEW step implementation |

---

## 🎯 DEPENDENCIES & FLOW

```
check_integrity.py reads from:
├─ ctx["lmp_blocker"]     (set by analyze_lmp.py)
├─ ctx["reccp_blocker"]   (set by analyze_reccp.py)
├─ ctx["foorch"]          (set by get_foorch.py)
└─ ctx["country"]         (set by resolve_source_order.py)

check_integrity.py writes to:
├─ ctx["integrity_packages"]
├─ ctx["integrity_responses"]
├─ ctx["integrity_results"]      ⭐ Used by finalize_comment.py
├─ ctx["carrier_derivations"]
└─ ctx["integrity_check"]

finalize_comment.py reads from:
└─ ctx["integrity_results"]      (set by check_integrity.py)
```

---

## 📊 EXECUTION ORDER (cambio_estado.yaml)

```
1. find_ids                    (Extracts IDs from description)
2. detect_status_intent        (LLM intent detection)
3. handle_unknown_intent       (Handles UNKNOWN intent)
4. dispatch_ids                (Parallel ID processing)
5. resolve_source_order        (Maps ID to FO)
6. get_foorch                  (Fetches fulfillment order)
7. check_piddp                 (Pick & dispatch check)
8. analyze_movep_estado        (Movement operation check)
9. analyze_lmp                 (Last-mile check) → Creates ctx["lmp_blocker"]
10. analyze_reccp              (Reception check) → Creates ctx["reccp_blocker"]
11. check_integrity ⭐         (NEW) (Calls integrity API)
12. finalize_comment           (Generates comments) → Uses ctx["integrity_results"]
13. finalize_comment           (Duplicate for parent context)
14. finalize_comment_parent    (Combines comments)
15. post_jira_comment          (Posts to JIRA)
```

---

## ✨ THAT'S IT!

All changes are in place. The system will now:
1. ✅ Collect non-terminal packages after LMP/RECCP analysis
2. ✅ Determine the correct panel value
3. ✅ Call the integrity endpoint
4. ✅ Filter FALSE_POSITIVE cases before generating comments
5. ✅ Log all operations with timestamps

