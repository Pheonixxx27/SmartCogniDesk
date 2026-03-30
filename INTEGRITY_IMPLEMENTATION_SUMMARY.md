# Integrity Check Implementation - Complete Summary

## Overview
Implemented end-to-end integrity validation for the "Problema Cambio de Estado" (Status Change Problem) SOP workflow, integrating with the external `/integrity/integrity/resolve` endpoint to validate package states and identify FALSE_POSITIVE cases.

---

## Files Modified

### 1. **JiraAI/sops/steps/check_integrity.py** (NEW - 336 lines)

**Purpose**: Orchestrate integrity validation after LMP/RECCP analysis

**Key Functions**:

#### `determine_panel(foorch, lmp_executor_ref, reccp_present, commerce)`
- Maps commerce type + executor reference to one of 5 panel types
- Detects commerce from multiple FOORCH JSON paths:
  - Root-level: `foorch.get("commerce")`
  - Nested: `foorch.get("fulfilmentOrder").logisticGroups[].orderItems[].itemInfo.sellerId`
- Returns panel type: `backstore`, `trmg-ikea`, `3pl-ikea`, `3pl-hd`, or `trmg-geosort`

#### `collect_packages(ctx)`
- Extracts non-terminal packages from both LMP and RECCP API responses
- **LMP Processing** (from `ctx["lmp_data"]`):
  - Iterates `packages[]` array
  - Uses `packageTrackingReference` as caseId
  - Checks `state` against TERMINAL_STATES
  - Stores `executorRef` as executor
- **RECCP Processing** (from `ctx["reccp_data"]`):
  - Iterates `packages[]` then `trackingData[]` arrays
  - Uses `number` (tracking number) as caseId
  - Checks `status` against TERMINAL_STATES
  - Uses `carrierName` as executor
- Returns list of package objects with metadata

#### `build_integrity_payload(packages, foorch, country, ctx)`
- Creates request payload for `/integrity/integrity/resolve` endpoint
- For each package, builds object:
  ```json
  {
    "caseId": "tracking-number",
    "terminal": false,
    "panel": "trmg-ikea",
    "actualStatus": "PENDING",
    "country": "CL"
  }
  ```
- Determines panel once for all packages (same FOORCH context)

#### `execute(ctx)` - Main Orchestrator
1. Validates country and FOORCH exist
2. Collects non-terminal packages
3. Builds integrity API payload
4. Calls `/integrity/integrity/resolve` endpoint with:
   - Method: POST
   - Headers: `x-country`, `Content-Type: application/json`
   - Timeout: 15 seconds
   - SSL: Disabled for local testing
5. Processes responses and groups by status:
   - `FALSE_POSITIVE`: Packages incorrectly reported as issues
   - `PENDING`: Still being investigated
   - `SOLVED`: Issues resolved
   - `NEW`: Newly discovered issues
6. Captures carrier derivations for BlueExpress/ChileExpress
7. Stores all results in context for downstream steps
8. Emits `INTEGRITY_CHECK` event for monitoring

**Constants**:
```python
TERMINAL_STATES = {"CANCELLED", "DELIVERED", "ANNULLED", "EXCEPTION", "AUCTIONED", "RETURNED_TO_ORIGIN", "REPACKED"}
INTEGRITY_ENDPOINT = "https://localhost:8082/integrity/integrity/resolve"
```

---

### 2. **JiraAI/sops/cambio_estado.yaml** (MODIFIED)

**Change**: Added `check_integrity` step to workflow

**Location**: Line 10, after `analyze_reccp` step

**Workflow Order**:
```yaml
- find_ids                # Extract IDs from JIRA ticket
- detect_status_intent    # Determine if it's status change problem
- get_foorch              # Fetch fulfillment order info
- get_movep               # Fetch movement operations
- check_piddp             # Check pick/dispatch status
- get_lmp                 # Get last-mile operations
- analyze_lmp             # Analyze last-mile packages
- get_reccp               # Get reception/collection data
- analyze_reccp           # Analyze reception packages
- check_integrity         # ← NEW: Validate integrity
- finalize_comment        # Generate executor-specific comments
- post_jira_comment       # Post comment to JIRA ticket
- resolve_source_order    # Update source order if all resolved
```

---

### 3. **JiraAI/sops/steps/analyze_lmp.py** (MODIFIED)

**Change**: Store raw LMP API response for integrity checks

**Location**: After `data = resp.json()` (line ~41)

**Added Code**:
```python
# Store raw API response for integrity checks
ctx["lmp_data"] = data
```

**Purpose**: Makes full LMP response available to `check_integrity.py` for package extraction

**Data Structure**:
```json
{
  "operationId": "LMP-123456",
  "executorRef": "FALABELLA_GROUP",
  "packages": [
    {
      "packageTrackingReference": "FAL-PKG-001",
      "state": "IN_TRANSIT",
      "...": "..."
    }
  ]
}
```

---

### 4. **JiraAI/sops/steps/analyze_reccp.py** (MODIFIED)

**Change**: Store raw RECCP API response for integrity checks

**Location**: After `data = resp.json()` (line ~34)

**Added Code**:
```python
# Store raw API response for integrity checks
ctx["reccp_data"] = data
```

**Purpose**: Makes full RECCP response available to `check_integrity.py` for package extraction

**Data Structure**:
```json
{
  "operationId": "RECCP-456789",
  "packages": [
    {
      "packageId": "PKG-789",
      "status": "RECEIVED",
      "trackingData": [
        {
          "number": "CHX-123456",
          "carrierName": "ChileExpress",
          "status": "IN_TRANSIT"
        }
      ]
    }
  ]
}
```

---

### 5. **JiraAI/sops/steps/finalize_comment.py** (MODIFIED)

**Change**: Add FALSE_POSITIVE filtering logic

**Location**: Lines 21-56 (after integrity results are available)

**Added Logic**:
```python
# Safety check: Don't comment if all packages are FALSE_POSITIVE from integrity
integrity_results = ctx.get("integrity_results", {})
false_positives = integrity_results.get("FALSE_POSITIVE", [])

if false_positives:
    blocker = ctx.get("blocker", {})
    blocker_packages = set()
    
    # Collect package IDs/tracking numbers from blocker
    for pkg in blocker.get("details", {}).get("packages", []):
        blocker_packages.add(pkg.get("tracking"))
    
    # Check if all blocker packages are FALSE_POSITIVE
    fp_tracking = {fp.get("caseId") for fp in false_positives}
    
    if blocker_packages and blocker_packages.issubset(fp_tracking):
        ctx.log("✅ All packages flagged as FALSE_POSITIVE - suppressing comment")
        ctx["executor_comments"] = []
        return ctx
```

**Purpose**: Suppress unnecessary JIRA comments when integrity check determines the reported issue is FALSE_POSITIVE (not actually a problem)

---

## Data Flow

```
JIRA Ticket
    ↓
[find_ids] → Extract package IDs
    ↓
[detect_status_intent] → Confirm "Status Change" problem
    ↓
[get_foorch] → Fetch fulfillment order
    ↓
[analyze_lmp] → Extract LMP data → Store in ctx["lmp_data"]
    ↓
[analyze_reccp] → Extract RECCP data → Store in ctx["reccp_data"]
    ↓
[check_integrity] ← NEW STEP
    ├─ collect_packages() → Reads ctx["lmp_data"] & ctx["reccp_data"]
    ├─ build_integrity_payload() → Creates request
    ├─ POST /integrity/integrity/resolve
    ├─ Process responses
    └─ Store: ctx["integrity_results"]
    ↓
[finalize_comment]
    ├─ Check ctx["integrity_results"]["FALSE_POSITIVE"]
    └─ Suppress comment if all packages are FALSE_POSITIVE
    ↓
[post_jira_comment] → Post to JIRA (if not suppressed)
```

---

## Integration Points

### Context Variables Used

**Read By `check_integrity.py`**:
- `ctx["country"]` - Country code for API headers
- `ctx["foorch"]` - Fulfillment order data (for panel determination)
- `ctx["lmp_data"]` - Raw LMP API response (from analyze_lmp)
- `ctx["reccp_data"]` - Raw RECCP API response (from analyze_reccp)

**Written By `check_integrity.py`**:
- `ctx["integrity_packages"]` - Payload sent to integrity endpoint
- `ctx["integrity_responses"]` - Raw responses from integrity endpoint
- `ctx["integrity_results"]` - Grouped responses by status
- `ctx["carrier_derivations"]` - Carrier info for carriers needing derivation
- `ctx["integrity_check"]` - Summary stats (total_checked, false_positives, pending, solved)

**Read By `finalize_comment.py`**:
- `ctx["integrity_results"]` - To check for FALSE_POSITIVE flags
- `ctx["blocker"]` - To get package list for suppression check

---

## API Endpoint Specifications

### Integrity Endpoint

**URL**: `https://localhost:8082/integrity/integrity/resolve`

**Method**: POST

**Headers**:
```
x-country: CL
Content-Type: application/json
```

**Request Payload** (array of objects):
```json
[
  {
    "caseId": "FAL-PKG-001",
    "terminal": false,
    "panel": "trmg-ikea",
    "actualStatus": "IN_TRANSIT",
    "country": "CL"
  }
]
```

**Response Payload** (array of objects):
```json
[
  {
    "caseId": "FAL-PKG-001",
    "status": "FALSE_POSITIVE|PENDING|SOLVED|NEW",
    "carrierName": "ChileExpress",
    "carrierStatus": "...",
    "rootCause": "..."
  }
]
```

**Response Statuses**:
- `FALSE_POSITIVE` - Package incorrectly reported as issue
- `PENDING` - Still being investigated by integrity service
- `SOLVED` - Issue has been resolved
- `NEW` - Newly discovered issue

---

## Panel Determination Logic

### 5 Panel Types

| Panel | Description | Commerce | Executor Pattern |
|-------|-------------|----------|------------------|
| `backstore` | Internal warehouse | FALABELLA | FALABELLA_GROUP |
| `trmg-ikea` | IKEA last-mile | IKEA | Any IKEA executor |
| `3pl-ikea` | 3PL for IKEA | IKEA | Non-FALABELLA executor |
| `3pl-hd` | 3PL for other | FALABELLA | Non-FALABELLA, non-IKEA executor |
| `trmg-geosort` | Geosort terminal | IKEA or OTHER | Any executor |

### Detection Algorithm

```python
# 1. Detect commerce from FOORCH
commerce = foorch.get("commerce") or 
           detect_from_fulfilmentOrder(foorch)

# 2. Check LMP executor reference
if commerce == "IKEA":
    if not lmp_executor_ref:
        panel = "3pl-ikea"
    elif lmp_executor_ref == "FALABELLA_GROUP":
        panel = "trmg-ikea"
    else:
        panel = "3pl-ikea"
else:  # FALABELLA
    if not lmp_executor_ref:
        panel = "backstore"
    elif lmp_executor_ref == "FALABELLA_GROUP":
        panel = "backstore"
    else:
        panel = "3pl-hd"

# 3. Geosort override (if RECCP present and commerce is mixed)
if reccp_present and specific_conditions:
    panel = "trmg-geosort"
```

---

## Terminal States

Packages in these states are NOT sent to integrity check:
- `CANCELLED` - Order cancelled
- `DELIVERED` - Package delivered to customer
- `ANNULLED` - Order annulled
- `EXCEPTION` - Exception occurred (usually resolved)
- `AUCTIONED` - Package auctioned (resolved)
- `RETURNED_TO_ORIGIN` - Returned to origin point
- `REPACKED` - Package repacked (resolved)

---

## Testing Checklist

- [ ] LMP/RECCP data correctly extracted from API responses
- [ ] `collect_packages()` returns correct package list for integrity check
- [ ] Panel determination logic correctly identifies panel from FOORCH + LMP data
- [ ] Integrity endpoint called with correct payload format
- [ ] Response parsing correctly groups by status (FALSE_POSITIVE, PENDING, SOLVED, NEW)
- [ ] FALSE_POSITIVE filtering correctly suppresses JIRA comments
- [ ] Context variables properly populated throughout workflow
- [ ] INTEGRITY_CHECK event emitted with correct metrics
- [ ] Error handling works for API failures/timeouts
- [ ] Terminal states correctly filtered out
- [ ] Works for both "Problema Cambio de Estado" SOP

---

## Future Enhancements

1. **ASN/DO Integration**: Add `check_integrity` to `asn_do.yaml` workflow
2. **Carrier-Specific Logic**: Enhanced carrier derivation for additional carriers
3. **Performance**: Batch integrity checks in parallel (ThreadPoolExecutor)
4. **Caching**: Cache panel determination results to reduce redundant calculations
5. **Monitoring**: Enhanced logging and metrics collection
6. **Retry Logic**: Implement exponential backoff for failed integrity API calls

---

## Debugging Tips

**Enable verbose logging**:
```python
ctx.log(f"LMP Data: {ctx.get('lmp_data')}")
ctx.log(f"RECCP Data: {ctx.get('reccp_data')}")
ctx.log(f"Integrity Results: {ctx.get('integrity_results')}")
```

**Check integrity response parsing**:
```python
# In check_integrity.py execute() function
for response in responses:
    print(f"Response: {response}")
    print(f"Status: {response.get('status')}")
```

**Verify panel determination**:
```python
# Test commerce detection from FOORCH
foorch = ctx.get("foorch")
commerce = foorch.get("commerce")
print(f"Detected commerce: {commerce}")
```
