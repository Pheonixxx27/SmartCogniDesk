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


def determine_panel(foorch, lmp_executor_ref=None, reccp_present=False, commerce=None):
    """
    Determine panel value based on commerce, executor, and operation type.
    
    Logic:
    - backstore: RECCP present
    - trmg-ikea: IKEA commerce + LMP with FALABELLA_GROUP
    - 3pl-ikea: IKEA commerce + LMP with THREE_PL
    - 3pl-hd: LMP with THREE_PL (non-IKEA)
    - trmg-geosort: LMP with FALABELLA_GROUP (non-IKEA)
    """
    
    # Priority 1: RECCP present → backstore
    if reccp_present:
        return "backstore"
    
    # If no LMP executor info, can't determine
    if not lmp_executor_ref:
        return None
    
    # Detect commerce type from FOORCH if not provided
    if not commerce:
        try:
            # Check FOORCH root level for commerce
            if "commerce" in foorch:
                commerce = foorch.get("commerce", "").upper()
            
            # Always check fulfilmentOrder for IKEA (overrides root commerce)
            if foorch:
                foorc = foorch.get("fulfilmentOrder", {})
                if foorc:
                    # Check for IKEA in items (even if commerce already set to FALABELLA)
                    for group in foorc.get("logisticGroups", []):
                        for item in group.get("orderItems", []):
                            seller_id = item.get("itemInfo", {}).get("sellerId", "")
                            if "IKEA" in str(seller_id).upper():
                                commerce = "IKEA"
                                break
            
            # Fallback if still not determined
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


def collect_packages(ctx):
    """
    Collect all non-terminal packages from LMP and RECCP operations.
    
    From LMP API response: Extract packages array
    From RECCP API response: Extract packages array
    
    Returns list of packages with their metadata.
    """
    packages = []
    
    # ==================== LMP PACKAGES ====================
    # LMP is fetched during analyze_lmp step
    # Structure: {packages: [{packageTrackingReference, state, executorRef}]}
    lmp_data = ctx.get("lmp_data")  # Raw LMP API response
    if lmp_data:
        lmp_packages = lmp_data.get("packages", [])
        lmp_executor = lmp_data.get("executorRef")
        lmp_id = lmp_data.get("operationId")
        
        for pkg in lmp_packages:
            state = pkg.get("state")
            tracking = pkg.get("packageTrackingReference")
            
            if tracking and state not in TERMINAL_STATES:
                packages.append({
                    "caseId": tracking,
                    "state": state,
                    "source": "LMP",
                    "executor": lmp_executor,
                    "lmp_id": lmp_id,
                    "tracking_ref": tracking,
                })
                ctx.log(f"  📌 LMP Package: {tracking} (state: {state})")
    
    # ==================== RECCP PACKAGES ====================
    # RECCP is fetched during analyze_reccp step
    # Structure: {packages: [{packageId, status, trackingData[{number, carrierName, status}]}]}
    reccp_data = ctx.get("reccp_data")  # Raw RECCP API response
    if reccp_data:
        reccp_packages = reccp_data.get("packages", [])
        reccp_id = reccp_data.get("operationId")
        
        for pkg in reccp_packages:
            pkg_status = pkg.get("status")
            pkg_id = pkg.get("packageId")
            
            # RECCP can have multiple tracking entries (per carrier)
            tracking_data = pkg.get("trackingData", [])
            
            for track in tracking_data:
                track_status = track.get("status")
                track_number = track.get("number")
                carrier_name = track.get("carrierName")
                
                if track_number and track_status not in TERMINAL_STATES:
                    packages.append({
                        "caseId": track_number,
                        "state": track_status,
                        "source": "RECCP",
                        "executor": carrier_name,
                        "reccp_id": reccp_id,
                        "package_id": pkg_id,
                        "tracking_ref": track_number,
                    })
                    ctx.log(f"  📌 RECCP Package: {track_number} (carrier: {carrier_name}, state: {track_status})")
    
    return packages


def build_integrity_payload(packages, foorch, country, ctx):
    """
    Build integrity API payload for /integrity/integrity/resolve endpoint.
    
    Each request object contains:
    {
        "type": "STATUS_FO",
        "caseId": tracking number or package ID,
        "panel": panel type (backstore|trmg-ikea|3pl-ikea|3pl-hd|trmg-geosort),
        "country": country code (CL, PE, etc)
    }
    
    Returns:
        list of integrity check requests
    """
    if not packages:
        ctx.log("ℹ️ No non-terminal packages to check")
        return []
    
    payload = []
    
    # Get executor ref from LMP or RECCP data (not from FOORCH)
    lmp_executor_ref = None
    lmp_data = ctx.get("lmp_data")
    if lmp_data:
        lmp_executor_ref = lmp_data.get("executorRef")
    
    reccp_executor_ref = None
    reccp_data = ctx.get("reccp_data")
    if reccp_data:
        reccp_executor_ref = reccp_data.get("executorRef")
    
    # Use LMP executor if available, otherwise RECCP
    executor_ref = lmp_executor_ref or reccp_executor_ref
    
    commerce = foorch.get("commerce", "").upper()
    reccp_present = bool(ctx.get("reccp_data"))
    
    # Determine panel once for all packages (same FOORCH/commerce context)
    panel = determine_panel(foorch, executor_ref, reccp_present, commerce)
    
    if not panel:
        ctx.log(f"⚠️ Could not determine panel for integrity check")
        ctx.log(f"   Executor ref: {executor_ref}, Commerce: {commerce}, RECCP: {reccp_present}")
        return []
    
    ctx.log(f"✅ Panel determined: {panel} (executor={executor_ref})")
    
    # Build request for each package
    for pkg in packages:
        case_id = pkg.get("caseId")
        
        request = {
            "type": "STATUS_FO",
            "panel": panel,
            "country": country,
            "caseId": case_id,
        }
        payload.append(request)
        ctx.log(f"  📤 Integrity request: caseId={case_id}, panel={panel}, country={country}")
    
    return payload


def refetch_lmp_reccp(ctx):
    """
    Refetch LMP and RECCP data to check current status of packages.
    Called when integrity returns SOLVED status for some packages.
    
    Updates:
    - ctx["lmp_data"] with fresh data
    - ctx["reccp_data"] with fresh data
    """
    country = ctx.get("country")
    operations = ctx.get("operations", [])
    
    if not country:
        ctx.log("⚠️ Country missing, cannot refetch LMP/RECCP")
        return
    
    # ==================== REFETCH LMP ====================
    lmp_op = None
    for group in operations:
        for op in group.get("operationsInfo", []):
            if op.get("operationCode") == "LMP":
                lmp_op = op
                break
        if lmp_op:
            break
    
    if lmp_op and lmp_op.get("operationCreated") == "SUCCESS":
        lmp_id = lmp_op.get("operationId")
        if lmp_id:
            try:
                url = f"https://localhost:8082/last-mile/api/v1/last-mile-operations/{lmp_id}"
                headers = {"x-commerce": "FAL", "x-country": country}
                resp = requests.get(url, headers=headers, timeout=10, verify=False)
                
                if resp.status_code == 200:
                    ctx["lmp_data"] = resp.json()
                    ctx.log(f"✅ Refetched LMP data: {lmp_id}")
                else:
                    ctx.log(f"⚠️ Failed to refetch LMP: HTTP {resp.status_code}")
            except Exception as e:
                ctx.log(f"⚠️ Error refetching LMP: {e}")
    
    # ==================== REFETCH RECCP ====================
    reccp_id = None
    reccp_op = None
    for group in operations:
        for op in group.get("operationsInfo", []):
            if op.get("operationCode") == "RECCP":
                reccp_id = op.get("operationId")
                reccp_op = op
                break
        if reccp_id:
            break
    
    if reccp_id and reccp_op and reccp_op.get("operationCreated") == "SUCCESS":
        try:
            url = f"https://localhost:8082/receive-and-collect/api/v1/receive-and-collect/{reccp_id}"
            headers = {"x-commerce": "FAL", "x-country": country}
            resp = requests.get(url, headers=headers, timeout=10, verify=False)
            
            if resp.status_code == 200:
                ctx["reccp_data"] = resp.json()
                ctx.log(f"✅ Refetched RECCP data: {reccp_id}")
            else:
                ctx.log(f"⚠️ Failed to refetch RECCP: HTTP {resp.status_code}")
        except Exception as e:
            ctx.log(f"⚠️ Error refetching RECCP: {e}")


def execute(ctx):
    ctx.log("🔍 STEP: CHECK_INTEGRITY")
    
    country = ctx.get("country")
    foorch = ctx.get("foorch", {})
    
    if not country or not foorch:
        ctx.log("⚠️ Country or FOORCH missing → skipping integrity check")
        return ctx
    
    # ==================== COLLECT PACKAGES ====================
    packages = collect_packages(ctx)
    
    if not packages:
        ctx.log("ℹ️ No packages to check for integrity")
        ctx["integrity_check"] = {
            "total_checked": 0,
            "skipped": True,
            "reason": "No non-terminal packages",
        }
        return ctx
    
    ctx.log(f"📦 Collected {len(packages)} non-terminal packages for integrity check")
    
    # ==================== BUILD PAYLOAD ====================
    payload = build_integrity_payload(packages, foorch, country, ctx)
    
    if not payload:
        ctx.log("⚠️ Failed to build integrity payload")
        return ctx
    
    ctx.log(f"📨 Sending {len(payload)} packages to integrity endpoint")
    ctx.log(f"   Endpoint: {INTEGRITY_ENDPOINT}")
    ctx.log(f"   Payload: {json.dumps(payload, indent=2)[:200]}...")  # First 200 chars
    
    # ==================== CALL INTEGRITY API ====================
    headers = {
        "x-country": country,
        "Content-Type": "application/json",
    }
    
    try:
        ctx.log(f"🚀 Making POST request to integrity endpoint...")
        resp = requests.post(
            INTEGRITY_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=15,
            verify=False,
        )
        
        ctx.log(f"✅ Integrity endpoint responded with HTTP {resp.status_code}")
        
        if resp.status_code != 200:
            ctx.log(f"❌ Integrity API error {resp.status_code}: {resp.text[:500]}")
            ctx["integrity_check"] = {
                "total_checked": len(payload),
                "status": "FAILED",
                "error": f"HTTP {resp.status_code}",
                "endpoint_hit": True,
            }
            return ctx
        
        responses = resp.json()
        ctx.log(f"✅ Received {len(responses)} integrity responses")
        ctx.log(f"   Responses: {json.dumps(responses, indent=2)[:200]}...")
        
    except requests.exceptions.Timeout as e:
        ctx.log(f"⏱️ Integrity API TIMEOUT after 15s: {e}")
        ctx.log(f"   This means the endpoint WAS HIT but didn't respond in time")
        ctx["integrity_check"] = {
            "total_checked": len(payload),
            "status": "TIMEOUT",
            "error": str(e),
            "endpoint_hit": True,
        }
        return ctx
        
    except requests.exceptions.ConnectionError as e:
        ctx.log(f"❌ Integrity API CONNECTION ERROR: {e}")
        ctx.log(f"   This means the endpoint was NOT reachable")
        ctx["integrity_check"] = {
            "total_checked": len(payload),
            "status": "CONNECTION_ERROR",
            "error": str(e),
            "endpoint_hit": False,
        }
        return ctx
        
    except Exception as e:
        ctx.log(f"❌ Integrity API exception: {type(e).__name__}: {e}")
        ctx["integrity_check"] = {
            "total_checked": len(payload),
            "status": "ERROR",
            "error": str(e),
            "endpoint_hit": False,
        }
        return ctx
    
    # ==================== PROCESS RESPONSES ====================
    ctx.log(f"✅ Processing integrity responses...")
    
    integrity_results = {
        "FALSE_POSITIVE": [],
        "PENDING": [],
        "SOLVED": [],
        "NEW": [],
    }
    
    carrier_derivations = []
    solved_case_ids = set()
    
    for response in responses:
        case_id = response.get("caseId")
        status = response.get("status")
        
        ctx.log(f"  📌 {case_id}: {status}")
        
        if status in integrity_results:
            integrity_results[status].append(response)
            if status == "SOLVED":
                solved_case_ids.add(case_id)
        
        # Capture carrier info for derivation
        carrier_name = response.get("carrierName")
        if carrier_name and carrier_name.lower() in ("blueexpress", "chilexpress"):
            carrier_derivations.append({
                "case_id": case_id,
                "carrier": carrier_name,
                "carrier_status": response.get("carrierStatus"),
                "root_cause": response.get("rootCause"),
            })
    
    # ==================== REFETCH IF SOLVED ====================
    # If integrity returns SOLVED, refetch LMP/RECCP to get updated status
    if solved_case_ids:
        ctx.log(f"🔄 Refetching LMP/RECCP for {len(solved_case_ids)} SOLVED packages")
        refetch_lmp_reccp(ctx)
    
    # ==================== STORE RESULTS ====================
    ctx["integrity_packages"] = payload
    ctx["integrity_responses"] = responses
    ctx["integrity_results"] = integrity_results
    ctx["carrier_derivations"] = carrier_derivations
    ctx["solved_case_ids"] = solved_case_ids  # For finalize_comment.py
    
    ctx["integrity_check"] = {
        "total_checked": len(payload),
        "false_positives": len(integrity_results["FALSE_POSITIVE"]),
        "pending": len(integrity_results["PENDING"]),
        "solved": len(integrity_results["SOLVED"]),
        "new": len(integrity_results["NEW"]),
    }
    
    ctx.emit_event(
        "INTEGRITY_CHECK",
        {
            "packages_checked": len(payload),
            "false_positives": len(integrity_results["FALSE_POSITIVE"]),
            "pending": len(integrity_results["PENDING"]),
            "solved": len(integrity_results["SOLVED"]),
            "country": country,
        },
    )
    
    ctx.log(
        f"✅ Integrity check complete → "
        f"FALSE_POSITIVE={len(integrity_results['FALSE_POSITIVE'])}, "
        f"PENDING={len(integrity_results['PENDING'])}, "
        f"SOLVED={len(integrity_results['SOLVED'])}"
    )
    
    return ctx
