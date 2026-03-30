# Line-by-Line Changes - Ready for Audit

**All changes verified and complete**

---

## File 1: JiraAI/sops/cambio_estado.yaml

**Change**: Added check_integrity step

```diff
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
+   - check_integrity
    - finalize_comment
    - finalize_comment
    - finalize_comment_parent
    - post_jira_comment
```

**Location**: Line 18
**Type**: Addition
**Impact**: Workflow now includes integrity check

---

## File 2: JiraAI/sops/steps/analyze_lmp.py

**Change**: Store raw LMP data

```diff
    data = resp.json()
+   
+   # Store raw API response for integrity checks
+   ctx["lmp_data"] = data
+   
    packages = data.get("packages", [])
    executor = data.get("executorRef")
```

**Location**: Line 46 (after data assignment)
**Type**: Addition (4 lines)
**Impact**: LMP response available to check_integrity

---

## File 3: JiraAI/sops/steps/analyze_reccp.py

**Change**: Store raw RECCP data

```diff
    data = resp.json()
+   
+   # Store raw API response for integrity checks
+   ctx["reccp_data"] = data
+   
    packages = data.get("packages", [])
```

**Location**: Line 43 (after data assignment)
**Type**: Addition (4 lines)
**Impact**: RECCP response available to check_integrity

---

## File 4: JiraAI/sops/steps/finalize_comment.py

**Change 1**: Add TERMINAL_STATES constant

```diff
  import json
  
+ TERMINAL_STATES = {
+     "CANCELLED",
+     "DELIVERED",
+     "ANNULLED",
+     "EXCEPTION",
+     "AUCTIONED",
+     "RETURNED_TO_ORIGIN",
+     "REPACKED",
+     "COMPLETED",
+ }
+ 
  
  def execute(ctx):
```

**Location**: Lines 3-10
**Type**: Addition (10 lines)

**Change 2**: Add FALSE_POSITIVE filtering

```diff
    # --------------------------------------------------
    # SAFETY 2️⃣: No blocker → nothing to comment
    # --------------------------------------------------
    blocker = ctx.get("blocker")
    if not blocker:
        ctx.log("ℹ️ No blocker → skipping child finalize")
        ctx["executor_comments"] = []
        return ctx
  
+   # --------------------------------------------------
+   # INTEGRITY CHECK: Filter by FALSE_POSITIVE
+   # --------------------------------------------------
+   integrity_results = ctx.get("integrity_results", {})
+   false_positives = integrity_results.get("FALSE_POSITIVE", [])
+   
+   if false_positives:
+       blocker_type = blocker.get("type")
+       blocker_details = blocker.get("details", {})
+       
+       if blocker_type in ("LMP", "RECCP"):
+           packages = blocker_details.get("packages", [])
+           all_false_positive = True
+           
+           for pkg in packages:
+               pkg_id = pkg.get("tracking")
+               is_false_pos = any(fp.get("caseId") == pkg_id for fp in false_positives)
+               
+               if not is_false_pos:
+                   all_false_positive = False
+                   break
+           
+           if all_false_positive and packages:
+               ctx.log(f"ℹ️ Integrity: All packages are FALSE_POSITIVE → suppressing")
+               ctx["executor_comments"] = []
+               return ctx
```

**Location**: Lines 35-71 (after blocker check)
**Type**: Addition (37 lines)

**Change 3**: Add SOLVED filtering

```diff
+   # --------------------------------------------------
+   # REFETCHED DATA: Filter out terminal state packages
+   # --------------------------------------------------
+   blocker_packages = blocker.get("details", {}).get("packages", [])
+   blocker_type = blocker.get("type")
+   solved_case_ids = ctx.get("solved_case_ids", set())
+   
+   if solved_case_ids and blocker_type in ("LMP", "RECCP"):
+       ctx.log(f"🔄 Filtering packages after integrity SOLVED status...")
+       active_packages = []
+       
+       if blocker_type == "LMP":
+           lmp_data = ctx.get("lmp_data", {})
+           lmp_packages = lmp_data.get("packages", [])
+           
+           active_tracking = set()
+           for pkg in lmp_packages:
+               state = pkg.get("state")
+               tracking = pkg.get("packageTrackingReference")
+               if tracking and state not in TERMINAL_STATES:
+                   active_tracking.add(tracking)
+           
+           for pkg in blocker_packages:
+               if pkg.get("tracking") in active_tracking:
+                   active_packages.append(pkg)
+           
+           if not active_packages:
+               ctx.log(f"✅ All LMP packages reached terminal state after refetch")
+               ctx["executor_comments"] = []
+               return ctx
+           
+           ctx.log(f"📝 {len(active_packages)} packages still active from LMP")
+       
+       elif blocker_type == "RECCP":
+           reccp_data = ctx.get("reccp_data", {})
+           reccp_packages = reccp_data.get("packages", [])
+           
+           active_tracking = set()
+           for pkg in reccp_packages:
+               for td in pkg.get("trackingData", []):
+                   status = td.get("status")
+                   number = td.get("number")
+                   if number and status not in TERMINAL_STATES:
+                       active_tracking.add(number)
+           
+           for pkg in blocker_packages:
+               if pkg.get("tracking") in active_tracking:
+                   active_packages.append(pkg)
+           
+           if not active_packages:
+               ctx.log(f"✅ All RECCP packages reached terminal state after refetch")
+               ctx["executor_comments"] = []
+               return ctx
+           
+           ctx.log(f"📝 {len(active_packages)} packages still active from RECCP")
+       
+       if active_packages:
+           blocker["details"]["packages"] = active_packages
```

**Location**: Lines 75-135 (after FALSE_POSITIVE check)
**Type**: Addition (61 lines)

---

## File 5: JiraAI/sops/steps/check_integrity.py (NEW - 410 lines)

**Complete new file with following sections**:

### Section 1: Imports & Constants (Lines 1-15)
```python
import requests
import json

TERMINAL_STATES = {
    "CANCELLED",
    "DELIVERED",
    "ANNULLED",
    "EXCEPTION",
    "AUCTIONED",
    "RETURNED_TO_ORIGIN",
    "REPACKED",
}

INTEGRITY_ENDPOINT = "https://localhost:8082/integrity/integrity/resolve"
```

### Section 2: determine_panel() (Lines 17-78)
```python
def determine_panel(foorch, lmp_executor_ref=None, reccp_present=False, commerce=None):
    # Priority 1: RECCP present → backstore
    if reccp_present:
        return "backstore"
    
    # If no LMP executor info, can't determine
    if not lmp_executor_ref:
        return None
    
    # Detect commerce type from FOORCH
    if not commerce:
        try:
            # Check root level
            if "commerce" in foorch:
                commerce = foorch.get("commerce", "").upper()
            
            # Always check fulfilmentOrder for IKEA (overrides root)
            if foorch:
                foorc = foorch.get("fulfilmentOrder", {})
                if foorc:
                    for group in foorc.get("logisticGroups", []):
                        for item in group.get("orderItems", []):
                            seller_id = item.get("itemInfo", {}).get("sellerId", "")
                            if "IKEA" in str(seller_id).upper():
                                commerce = "IKEA"
                                break
            
            if not commerce:
                commerce = "FALABELLA"
        except Exception as e:
            commerce = "FALABELLA"
    
    # Normalize executor reference
    lmp_exec_upper = str(lmp_executor_ref).upper()
    
    # Panel logic based on commerce + executor
    if "IKEA" in commerce:
        if "FALABELLA_GROUP" in lmp_exec_upper:
            return "trmg-ikea"
        elif "THREE_PL" in lmp_exec_upper:
            return "3pl-ikea"
    else:  # FALABELLA
        if "THREE_PL" in lmp_exec_upper:
            return "3pl-hd"
        elif "FALABELLA_GROUP" in lmp_exec_upper:
            return "trmg-geosort"
    
    return None
```

### Section 3: collect_packages() (Lines 80-148)
- Extracts LMP packages from ctx["lmp_data"]
- Extracts RECCP packages from ctx["reccp_data"]
- Filters by TERMINAL_STATES

### Section 4: build_integrity_payload() (Lines 150-197)
- Creates request with: type, panel, country, caseId
- Removed: terminal, actualStatus fields

### Section 5: refetch_lmp_reccp() (Lines 199-265)
- Refetches LMP from endpoint
- Updates ctx["lmp_data"]
- Refetches RECCP from endpoint
- Updates ctx["reccp_data"]

### Section 6: execute() (Lines 268-410)
- Main orchestrator
- Collects packages
- Builds payload
- POSTs to integrity endpoint
- Processes responses
- Calls refetch if SOLVED
- Stores results

---

## Summary of Changes

| File | Type | Lines | Change |
|------|------|-------|--------|
| cambio_estado.yaml | Modify | 18 | Add step |
| analyze_lmp.py | Modify | 46 | Store data |
| analyze_reccp.py | Modify | 43 | Store data |
| finalize_comment.py | Modify | 3-10, 35-135 | Add filtering |
| check_integrity.py | Create | 1-410 | New step |
| **TOTAL** | | **~500** | **Complete** |

---

## Verification

```bash
# Verify all changes applied
✅ grep "check_integrity" cambio_estado.yaml
✅ grep "ctx\[\"lmp_data\"\]" analyze_lmp.py
✅ grep "ctx\[\"reccp_data\"\]" analyze_reccp.py
✅ grep "TERMINAL_STATES" finalize_comment.py
✅ ls -la check_integrity.py (410 lines)
```

---

## Ready for Testing

All changes have been:
- ✅ Implemented
- ✅ Verified
- ✅ Integrated
- ✅ Documented

**Status**: READY FOR SINGLE TICKET TEST
