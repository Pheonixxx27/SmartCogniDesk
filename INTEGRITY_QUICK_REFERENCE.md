# Integrity Check Implementation - Quick Reference

## Summary of Changes

### Files Created
✅ **JiraAI/sops/steps/check_integrity.py** (336 lines)
- Complete integrity validation orchestrator
- Panel determination logic for 5 panel types
- Package collection from LMP/RECCP APIs
- Integrity endpoint integration

### Files Modified

#### 1. JiraAI/sops/cambio_estado.yaml
**Line 10**: Added `- check_integrity` step after `analyze_reccp`

#### 2. JiraAI/sops/steps/analyze_lmp.py
**After line 41** (`data = resp.json()`):
```python
# Store raw API response for integrity checks
ctx["lmp_data"] = data
```

#### 3. JiraAI/sops/steps/analyze_reccp.py
**After line 34** (`data = resp.json()`):
```python
# Store raw API response for integrity checks
ctx["reccp_data"] = data
```

#### 4. JiraAI/sops/steps/finalize_comment.py
**Lines 21-56**: Added FALSE_POSITIVE filtering logic
```python
# Safety check: Don't comment if all packages are FALSE_POSITIVE from integrity
integrity_results = ctx.get("integrity_results", {})
false_positives = integrity_results.get("FALSE_POSITIVE", [])

if false_positives:
    # ... filtering logic to suppress comments if all packages are FALSE_POSITIVE
```

---

## Data Structures

### What `collect_packages()` Extracts

**From LMP** (`ctx["lmp_data"]`):
```python
{
    "caseId": "FAL-PKG-001",        # packageTrackingReference
    "state": "IN_TRANSIT",           # Package state
    "source": "LMP",
    "executor": "FALABELLA_GROUP",   # executorRef
    "tracking_ref": "FAL-PKG-001"
}
```

**From RECCP** (`ctx["reccp_data"]`):
```python
{
    "caseId": "CHX-123456",          # tracking number
    "state": "IN_TRANSIT",           # tracking status
    "source": "RECCP",
    "executor": "ChileExpress",      # carrierName
    "tracking_ref": "CHX-123456"
}
```

### Integrity Payload
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

### Integrity Response
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

---

## Key Context Variables

| Variable | Set By | Read By | Content |
|----------|--------|---------|---------|
| `ctx["lmp_data"]` | analyze_lmp | check_integrity | Raw LMP API response |
| `ctx["reccp_data"]` | analyze_reccp | check_integrity | Raw RECCP API response |
| `ctx["integrity_packages"]` | check_integrity | finalize_comment | Payload sent to integrity API |
| `ctx["integrity_responses"]` | check_integrity | finalize_comment | Raw responses from integrity API |
| `ctx["integrity_results"]` | check_integrity | finalize_comment | Responses grouped by status |
| `ctx["carrier_derivations"]` | check_integrity | (future use) | Carrier info for derivation |

---

## Panel Determination

| Commerce | LMP Executor | Result Panel |
|----------|-------------|--------------|
| IKEA | None/empty | `3pl-ikea` |
| IKEA | FALABELLA_GROUP | `trmg-ikea` |
| IKEA | Other | `3pl-ikea` |
| FALABELLA | None/empty | `backstore` |
| FALABELLA | FALABELLA_GROUP | `backstore` |
| FALABELLA | Other | `3pl-hd` |

---

## Integration Points

### SOP Workflow Flow
```
analyze_lmp (stores lmp_data) 
    ↓
analyze_reccp (stores reccp_data)
    ↓
check_integrity (reads both, validates, stores results)
    ↓
finalize_comment (reads results, suppresses if FALSE_POSITIVE)
    ↓
post_jira_comment
```

### API Integration
- **Endpoint**: `https://localhost:8082/integrity/integrity/resolve`
- **Method**: POST
- **Headers**: `x-country: {country}`, `Content-Type: application/json`
- **Timeout**: 15 seconds
- **SSL**: Disabled (local testing)

---

## Testing

### Quick Test Commands

1. **Check if changes were applied**:
   ```bash
   grep -n "check_integrity" JiraAI/sops/cambio_estado.yaml
   grep -n "ctx\[\"lmp_data\"\]" JiraAI/sops/steps/analyze_lmp.py
   grep -n "ctx\[\"reccp_data\"\]" JiraAI/sops/steps/analyze_reccp.py
   grep -n "integrity_results" JiraAI/sops/steps/finalize_comment.py
   ```

2. **Verify check_integrity.py exists**:
   ```bash
   ls -la JiraAI/sops/steps/check_integrity.py
   wc -l JiraAI/sops/steps/check_integrity.py
   ```

3. **Test with real JIRA ticket**:
   - Create a "Problema Cambio de Estado" JIRA ticket
   - Trigger SOP execution
   - Check logs for integrity validation messages

---

## Terminal States (Not Checked)

Packages in these states skip integrity check:
- CANCELLED
- DELIVERED
- ANNULLED
- EXCEPTION
- AUCTIONED
- RETURNED_TO_ORIGIN
- REPACKED

---

## Response Status Meanings

| Status | Meaning | Action |
|--------|---------|--------|
| `FALSE_POSITIVE` | Issue doesn't actually exist | Suppress comment |
| `PENDING` | Still being investigated | Add to comment |
| `SOLVED` | Issue was resolved | Add to comment |
| `NEW` | New issue discovered | Add to comment |

---

## Error Handling

### If Integrity API Fails
- Status code error: Logged, stored in `ctx["integrity_check"]["error"]`
- Timeout: Caught as exception, logged
- Workflow continues (graceful degradation)

### If Panel Cannot Be Determined
- Logged as warning
- Integrity check skipped
- Workflow continues

### If No Non-Terminal Packages
- Logged as info
- Integrity check skipped
- Workflow continues

---

## Future Work

- [ ] Add check_integrity to asn_do.yaml
- [ ] Implement parallel batch processing
- [ ] Add retry logic with exponential backoff
- [ ] Cache panel determination results
- [ ] Enhanced carrier-specific logic
- [ ] Performance metrics collection
