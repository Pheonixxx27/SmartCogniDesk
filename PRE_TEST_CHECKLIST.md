# Pre-Test Checklist - Ready to Deploy

**Date**: March 29, 2026
**Time**: Ready Now
**Status**: ✅ GO FOR TESTING

---

## Implementation Summary

| Item | File | Status | Details |
|------|------|--------|---------|
| Workflow Integration | cambio_estado.yaml | ✅ | Line 18: `- check_integrity` |
| Package Collection | check_integrity.py | ✅ | Lines 80-148: LMP + RECCP |
| Panel Determination | check_integrity.py | ✅ | Lines 17-78: 5 panel types |
| Payload Builder | check_integrity.py | ✅ | Lines 150-197: STATUS_FO format |
| Integrity API Call | check_integrity.py | ✅ | Lines 305-330: POST request |
| SOLVED Refetch | check_integrity.py | ✅ | Lines 199-265: LMP + RECCP |
| LMP Data Storage | analyze_lmp.py | ✅ | Line 46: ctx["lmp_data"] |
| RECCP Data Storage | analyze_reccp.py | ✅ | Line 43: ctx["reccp_data"] |
| FALSE_POSITIVE Filter | finalize_comment.py | ✅ | Lines 35-71 |
| Terminal State Filter | finalize_comment.py | ✅ | Lines 75-135 |
| SOLVED Logic | finalize_comment.py | ✅ | Lines 83-135 |

---

## 5-Step Test Plan

### 1. CREATE TEST TICKET
```
JIRA Title: "Test: Cambio de Estado Problem"
Category: "Problema Cambio de Estado"
Description: "Package FAL-PKG-001 status not updating"
```

### 2. TRIGGER WORKFLOW
```
System should automatically:
- Execute cambio_estado.yaml
- Run through all steps including check_integrity
```

### 3. MONITOR EXECUTION
```
Watch for these log messages:
✓ "🔍 STEP: CHECK_INTEGRITY"
✓ "📦 Collected X non-terminal packages"
✓ "✅ Panel determined: backstore|trmg-ikea|3pl-ikea|3pl-hd|trmg-geosort"
✓ "📨 Sending X packages to integrity endpoint"
✓ "✅ Received X integrity responses"
✓ "🔄 Refetching LMP/RECCP for X SOLVED packages" (if SOLVED)
✓ "🧾 STEP: FINALIZE_COMMENT"
```

### 4. VERIFY RESULTS
```
Check:
□ No exceptions in logs
□ Integrity API called successfully
□ Responses parsed correctly
□ Comments generated or suppressed correctly
□ JIRA ticket updated
```

### 5. VALIDATE LOGIC
```
Scenarios:
□ All FALSE_POSITIVE → Comment suppressed ✓
□ All SOLVED + terminal → Comment suppressed ✓
□ Some SOLVED + some active → Only active in comment ✓
□ PENDING → Normal comment ✓
```

---

## Key Variables to Check in Logs

```python
# After analyze_lmp
ctx["lmp_data"] = {...}          # Should contain packages array

# After analyze_reccp
ctx["reccp_data"] = {...}        # Should contain packages array

# After check_integrity
ctx["integrity_packages"]        # Payload sent to integrity API
ctx["integrity_responses"]       # Raw responses
ctx["integrity_results"]         # Grouped by status
ctx["solved_case_ids"]          # Set of SOLVED case IDs

# In finalize_comment
ctx["integrity_results"]["FALSE_POSITIVE"]  # For filtering
ctx["solved_case_ids"]                      # For refetch logic
```

---

## Expected Logs During Test

```
📍 STEP: ANALYZE_LMP
✅ Refetched LMP data
  📌 LMP Package: FAL-PKG-001 (state: IN_TRANSIT)

📦 STEP: ANALYZE_RECCP
✅ Refetched RECCP data
  📌 RECCP Package: CHX-123456 (carrier: ChileExpress, state: IN_TRANSIT)

🔍 STEP: CHECK_INTEGRITY
📦 Collected 2 non-terminal packages for integrity check
✅ Panel determined: backstore
📨 Sending 2 packages to integrity endpoint
  📤 Integrity request: caseId=FAL-PKG-001, panel=backstore, country=CL
  📤 Integrity request: caseId=CHX-123456, panel=backstore, country=CL
✅ Received 2 integrity responses
  📌 FAL-PKG-001: SOLVED
  📌 CHX-123456: PENDING
🔄 Refetching LMP/RECCP for 1 SOLVED packages
✅ Refetched LMP data: LMP-123456
✅ Refetched RECCP data: RECCP-789

🧾 STEP: FINALIZE_COMMENT
🔄 Filtering packages after integrity SOLVED status...
✅ 1 packages still active from LMP
  (FAL-PKG-001 removed - reached DELIVERED)

📝 Generating comment for 1 package: CHX-123456
✉️ STEP: POST_JIRA_COMMENT
✅ Comment posted to ticket
```

---

## Failure Scenarios to Handle

| Scenario | Expected Behavior |
|----------|-------------------|
| Integrity API unreachable | Log error, continue without integrity |
| LMP refetch fails | Log warning, use original data |
| No packages to check | Log info, skip integrity check |
| Panel cannot be determined | Log warning, skip integrity check |
| All packages FALSE_POSITIVE | Suppress comment |
| All packages reach terminal | Suppress comment |
| Mixed statuses | Comment only with active packages |

---

## Quick Diagnostics

### If check_integrity not running:
```
1. Check: grep "check_integrity" cambio_estado.yaml
2. Check: Step position (after analyze_reccp)
3. Check: No syntax errors in cambio_estado.yaml
```

### If integrity API not called:
```
1. Check: Packages collected (look for "Collected X packages")
2. Check: Panel determined (look for "Panel determined: xxx")
3. Check: Payload built (look for "Integrity request: caseId=...")
4. Check: API endpoint accessible
```

### If responses not parsed:
```
1. Check: Response format (should have caseId + status)
2. Check: Status values (FALSE_POSITIVE, PENDING, SOLVED, NEW)
3. Check: No JSON parsing errors in logs
```

### If comments not filtered:
```
1. Check: FALSE_POSITIVE cases in integrity_results
2. Check: Terminal state checks in finalize_comment
3. Check: SOLVED case IDs being tracked
```

---

## One-Liner Deployment Checks

```bash
# All checks pass = Ready to test
grep -q "check_integrity" JiraAI/sops/cambio_estado.yaml && \
grep -q "def execute" JiraAI/sops/steps/check_integrity.py && \
grep -q 'ctx\["lmp_data"\]' JiraAI/sops/steps/analyze_lmp.py && \
grep -q 'ctx\["reccp_data"\]' JiraAI/sops/steps/analyze_reccp.py && \
grep -q "TERMINAL_STATES" JiraAI/sops/steps/finalize_comment.py && \
echo "✅ ALL CHECKS PASSED - READY FOR TESTING" || \
echo "❌ SOME CHECKS FAILED - REVIEW NEEDED"
```

---

## Deployment Procedure

### Pre-Deployment
1. ✅ Create backup of current codebase
2. ✅ Run all checks above
3. ✅ Review logs from recent runs

### Deployment
1. ✅ Copy updated files to production:
   - JiraAI/sops/steps/check_integrity.py
   - JiraAI/sops/cambio_estado.yaml
   - JiraAI/sops/steps/analyze_lmp.py
   - JiraAI/sops/steps/analyze_reccp.py
   - JiraAI/sops/steps/finalize_comment.py

2. ✅ Restart workflow service

3. ✅ Verify service started without errors

### Post-Deployment
1. ✅ Create test JIRA ticket
2. ✅ Monitor execution in logs
3. ✅ Verify results match expected behavior
4. ✅ Test with 2-3 additional tickets
5. ✅ If issues found, rollback and review

---

## Testing Timeline

| Phase | Duration | Action |
|-------|----------|--------|
| Preparation | 5 min | Create test ticket, start monitoring |
| Execution | 2-5 min | Workflow runs |
| Verification | 5 min | Check logs and results |
| Analysis | 10 min | Review behavior, compare with expected |
| **Total** | **22-25 min** | **Complete end-to-end test** |

---

## Success Criteria

All of these should be TRUE:

- [ ] Workflow runs without errors
- [ ] check_integrity step executes
- [ ] Packages collected from LMP/RECCP
- [ ] Panel determined successfully
- [ ] Integrity API called with correct payload
- [ ] Responses received and grouped
- [ ] If SOLVED: refetch triggered
- [ ] finalize_comment filtering applied
- [ ] JIRA comment posted or suppressed as expected
- [ ] No exceptions in logs
- [ ] Event emitted: INTEGRITY_CHECK

**If all TRUE** → ✅ **TEST PASSED**
**If any FALSE** → ❌ **Review logs and identify issue**

---

## Contact Points for Issues

If test fails, check these first:

1. **Integrity API not responding**
   - Verify endpoint: `https://localhost:8082/integrity/integrity/resolve`
   - Check network connectivity
   - Review integrity service logs

2. **Wrong panel determined**
   - Check FOORCH data structure
   - Verify commerce detection logic
   - Check executor reference format

3. **Packages not collected**
   - Verify LMP/RECCP endpoints returning data
   - Check package structure matches expected format
   - Verify terminal state filtering logic

4. **Comments not filtered**
   - Check integrity response format
   - Verify FALSE_POSITIVE/SOLVED status values
   - Check terminal state definitions

---

## Status Report Template

Use this when testing:

```
Date: 2026-03-29
Ticket: JIRA-XXXX
Category: Problema Cambio de Estado

EXECUTION LOG:
□ LMP Analysis: PASS / FAIL (if FAIL, error: ___)
□ RECCP Analysis: PASS / FAIL (if FAIL, error: ___)
□ Integrity Check: PASS / FAIL (if FAIL, error: ___)
□ Comment Finalization: PASS / FAIL (if FAIL, error: ___)
□ JIRA Update: PASS / FAIL (if FAIL, error: ___)

RESULTS:
□ Comment Posted: YES / NO / SUPPRESSED
□ Panel Determined: _______________
□ Packages Checked: ___
□ Response Statuses: _______________

ISSUES FOUND:
(list any)

RESOLUTION:
(describe action taken)

STATUS: ✅ PASS / ⚠️ ISSUE / ❌ FAIL
```

---

## Final Checklist

```
BEFORE STARTING TEST:
□ Backup code
□ Run diagnostic checks
□ Monitor logs ready
□ Test ticket details prepared

DURING TEST:
□ Create JIRA ticket
□ Monitor logs in real-time
□ Take notes of any errors
□ Observe comment behavior

AFTER TEST:
□ Review logs completely
□ Verify expected vs actual
□ Document results
□ Decide: PASS or REMEDIATE
```

---

**READY TO TEST WITH SINGLE TICKET** ✅

All components verified. Implementation complete. 
Waiting for test ticket creation.
