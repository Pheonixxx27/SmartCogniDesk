# Integrity Check Update - SOLVED Status Refetch Logic

## Overview

Updated the integrity check implementation to:
1. **Correct Payload Format**: Changed to actual endpoint format with `type: "STATUS_FO"` field
2. **SOLVED Status Refetch**: When integrity returns `SOLVED` for packages, automatically refetch LMP/RECCP to get updated package states
3. **Terminal State Filtering**: Only include packages that haven't reached terminal states in final comments

---

## Changes Made

### 1. Updated Payload Format in check_integrity.py

**Function**: `build_integrity_payload()`

**Old Format**:
```json
{
  "caseId": "PKG00000FD4Q2",
  "terminal": false,
  "panel": "backstore",
  "actualStatus": "IN_TRANSIT",
  "country": "PE"
}
```

**New Format** (Corrected):
```json
{
  "type": "STATUS_FO",
  "panel": "backstore",
  "country": "PE",
  "caseId": "PKG00000FD4Q2"
}
```

### 2. New Function: refetch_lmp_reccp()

**Location**: `JiraAI/sops/steps/check_integrity.py` (lines ~202-274)

**Purpose**: Refetch fresh LMP and RECCP data after integrity service returns SOLVED status

**Logic**:
```python
def refetch_lmp_reccp(ctx):
    """
    Refetch LMP and RECCP data to check current status of packages.
    
    1. Extract LMP operation ID from ctx["operations"]
    2. Call: GET https://localhost:8082/last-mile/api/v1/last-mile-operations/{lmp_id}
    3. Update ctx["lmp_data"] with fresh response
    
    4. Extract RECCP operation ID from ctx["operations"]
    5. Call: GET https://localhost:8082/receive-and-collect/api/v1/receive-and-collect/{reccp_id}
    6. Update ctx["reccp_data"] with fresh response
    
    Handles errors gracefully, logs all operations
    """
```

**Implementation Details**:
- Locates LMP/RECCP operation IDs from `ctx["operations"]` (same structure as initial fetch)
- Calls each endpoint with headers: `x-commerce: FAL`, `x-country: {country}`
- Updates `ctx["lmp_data"]` and `ctx["reccp_data"]` with fresh API responses
- Timeout: 10 seconds per API call
- SSL: Disabled (local testing)

### 3. Updated execute() Function

**Changes**:
```python
# Track packages marked as SOLVED
solved_case_ids = set()

for response in responses:
    case_id = response.get("caseId")
    status = response.get("status")
    # ...
    if status == "SOLVED":
        solved_case_ids.add(case_id)

# ==================== REFETCH IF SOLVED ====================
if solved_case_ids:
    ctx.log(f"🔄 Refetching LMP/RECCP for {len(solved_case_ids)} SOLVED packages")
    refetch_lmp_reccp(ctx)

# Store solved case IDs for finalize_comment
ctx["solved_case_ids"] = solved_case_ids
```

### 4. Enhanced finalize_comment.py

**New Constants** (lines 1-10):
```python
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
```

**New Filtering Logic** (lines ~75-150):

```python
# After integrity returns SOLVED, filter out packages that reached terminal state
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
        
        # Keep only active packages
        for pkg in blocker_packages:
            if pkg.get("tracking") in active_tracking:
                active_packages.append(pkg)
    
    # Similar logic for RECCP...
    
    # If no active packages remain, suppress comment
    if not active_packages:
        ctx.log(f"✅ All packages reached terminal state after refetch")
        ctx["executor_comments"] = []
        return ctx
    
    # Update blocker with only active packages
    if active_packages:
        blocker["details"]["packages"] = active_packages
```

---

## Data Flow After SOLVED Status

```
Integrity Response: status = "SOLVED"
    ↓
check_integrity.py:
  - Adds caseId to solved_case_ids set
  - Calls refetch_lmp_reccp(ctx)
  - Updates ctx["lmp_data"] and ctx["reccp_data"]
  - Stores ctx["solved_case_ids"]
    ↓
finalize_comment.py:
  - Checks if solved_case_ids is not empty
  - Refetches LMP/RECCP data (already fresh from step above)
  - Compares active packages against refetched data
  - Filters blocker.details.packages to only active (non-terminal) packages
  - If all packages terminal, suppresses comment
  - If some active, includes only those in comment
    ↓
post_jira_comment:
  - Posts comment with only non-terminal packages
```

---

## Example Scenario

### Initial State
```
LMP Package: FAL-PKG-001, state: IN_TRANSIT
LMP Package: FAL-PKG-002, state: IN_TRANSIT
```

### Integrity Check Response
```json
[
  {
    "caseId": "FAL-PKG-001",
    "status": "SOLVED"
  },
  {
    "caseId": "FAL-PKG-002",
    "status": "PENDING"
  }
]
```

### Refetch LMP Data
```
LMP Package: FAL-PKG-001, state: DELIVERED (terminal)
LMP Package: FAL-PKG-002, state: IN_TRANSIT (still active)
```

### Final Comment
```
Only FAL-PKG-002 included (since FAL-PKG-001 reached DELIVERED)
```

---

## Context Variables Updated

### Set By check_integrity.py
```python
ctx["integrity_packages"]      # Payload sent to integrity API
ctx["integrity_responses"]     # Raw responses from integrity API
ctx["integrity_results"]       # Grouped by status
ctx["carrier_derivations"]     # Carrier info
ctx["solved_case_ids"]         # Set of caseIds marked SOLVED (NEW)
```

### Updated By refetch_lmp_reccp()
```python
ctx["lmp_data"]               # Refreshed LMP API response
ctx["reccp_data"]             # Refreshed RECCP API response
```

### Used By finalize_comment.py
```python
ctx["solved_case_ids"]        # To trigger refetch filtering
ctx["lmp_data"]               # For terminal state checking
ctx["reccp_data"]             # For terminal state checking
blocker["details"]["packages"] # Modified to contain only active packages
```

---

## API Refetch Details

### LMP Refetch
```
GET https://localhost:8082/last-mile/api/v1/last-mile-operations/{lmp_id}

Headers:
  x-commerce: FAL
  x-country: {country}

Response:
{
  "operationId": "LMP-123456",
  "executorRef": "FALABELLA_GROUP",
  "packages": [
    {
      "packageTrackingReference": "FAL-PKG-001",
      "state": "DELIVERED"  ← Updated from IN_TRANSIT
    }
  ]
}
```

### RECCP Refetch
```
GET https://localhost:8082/receive-and-collect/api/v1/receive-and-collect/{reccp_id}

Headers:
  x-commerce: FAL
  x-country: {country}

Response:
{
  "operationId": "RECCP-456789",
  "packages": [
    {
      "packageId": "PKG-789",
      "trackingData": [
        {
          "number": "CHX-123456",
          "status": "DELIVERED"  ← Updated from IN_TRANSIT
        }
      ]
    }
  ]
}
```

---

## Terminal States

Packages in these states are considered "resolved" and excluded from comments:

| State | Source | Meaning |
|-------|--------|---------|
| CANCELLED | LMP | Order cancelled |
| DELIVERED | LMP/RECCP | Package delivered |
| ANNULLED | LMP | Order annulled |
| EXCEPTION | LMP | Exception occurred |
| AUCTIONED | LMP | Auctioned (resolved) |
| RETURNED_TO_ORIGIN | LMP | Returned to origin |
| REPACKED | LMP | Repacked (resolved) |
| COMPLETED | RECCP | Task completed |

---

## Integrity Response Statuses

| Status | Action | Next Step |
|--------|--------|-----------|
| FALSE_POSITIVE | Skip comment for all packages (suppress) | No refetch needed |
| PENDING | Include in comment, keep monitoring | No refetch needed |
| SOLVED | Refetch to check if terminal | Conditional comment |
| NEW | Include in comment, new issue found | No refetch needed |

---

## Error Handling

### If Refetch Fails
- API error logged: "Failed to refetch LMP: HTTP 500"
- Workflow continues with stale data
- Graceful degradation: comments based on last known state

### If RECCP Not Found
- Logged: "No RECCP operation found"
- LMP refetch proceeds normally

### If No Solved Cases
- Refetch skipped
- Original blocker data used unchanged

---

## Testing Scenarios

### Scenario 1: All Packages Become Terminal After SOLVED
```
Before: LMP [PKG-001: IN_TRANSIT, PKG-002: IN_TRANSIT]
Integrity: PKG-001 → SOLVED, PKG-002 → PENDING
Refetch: LMP [PKG-001: DELIVERED, PKG-002: IN_TRANSIT]
Result: Comment includes only PKG-002
```

### Scenario 2: All Packages Terminal After SOLVED
```
Before: LMP [PKG-001: IN_TRANSIT]
Integrity: PKG-001 → SOLVED
Refetch: LMP [PKG-001: DELIVERED]
Result: Comment suppressed (no active packages)
```

### Scenario 3: FALSE_POSITIVE Overrides SOLVED
```
Before: LMP [PKG-001: IN_TRANSIT]
Integrity: PKG-001 → FALSE_POSITIVE
Result: Comment suppressed (no refetch, FALSE_POSITIVE wins)
```

---

## Workflow Summary

```
1. check_integrity step
   ├─ collect_packages() → LMP + RECCP non-terminal packages
   ├─ build_integrity_payload() → [{"type": "STATUS_FO", "caseId": ..., "panel": ..., "country": ...}]
   ├─ POST to /integrity/integrity/resolve
   ├─ Process responses → Group by status (FALSE_POSITIVE, PENDING, SOLVED, NEW)
   ├─ If SOLVED found → refetch_lmp_reccp()
   │   ├─ GET fresh LMP data
   │   └─ GET fresh RECCP data
   └─ Store: integrity_results, solved_case_ids

2. finalize_comment step
   ├─ Check integrity_results for FALSE_POSITIVE
   │  └─ If all packages FALSE_POSITIVE → suppress comment + return
   ├─ Check solved_case_ids
   │  ├─ If not empty, filter packages
   │  ├─ Compare against refetched LMP/RECCP data
   │  ├─ Keep only packages not in TERMINAL_STATES
   │  └─ If none remain → suppress comment + return
   └─ Generate comment with remaining packages

3. post_jira_comment step
   └─ Post comment to JIRA (may be empty if all filtered)
```

---

## Changes Summary

| File | Change | Lines |
|------|--------|-------|
| check_integrity.py | Corrected payload format | ~10 |
| check_integrity.py | Added refetch_lmp_reccp() | ~73 |
| check_integrity.py | Updated execute() for SOLVED | ~15 |
| finalize_comment.py | Added TERMINAL_STATES constant | 10 |
| finalize_comment.py | Enhanced filtering logic | ~85 |
| **Total** | | **~193** |

---

## Validation

✅ Payload format matches actual endpoint specification
✅ Refetch logic handles both LMP and RECCP
✅ Terminal state filtering works for both sources
✅ FALSE_POSITIVE still takes precedence
✅ Graceful error handling for API failures
✅ Context variables properly maintained
✅ Logging at each step for debugging
