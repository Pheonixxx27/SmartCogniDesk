# Commerce Detection Logic - Final Update

## Problem
Previously, IKEA detection in fulfilmentOrder only happened if the root commerce field was empty. But IKEA might be present in seller info even when root commerce is FALABELLA.

## Solution
Always check fulfilmentOrder for IKEA, allowing it to override root commerce field.

---

## Logic Flow

```
Step 1: Check root-level commerce
  ├─ If present: commerce = foorch["commerce"].upper()
  └─ If not: commerce = None

Step 2: Always check fulfilmentOrder (NEW)
  ├─ Iterate logisticGroups
  ├─ Iterate orderItems
  ├─ Check itemInfo.sellerId for "IKEA"
  ├─ If found: commerce = "IKEA" (OVERRIDES root)
  └─ If not found: keep existing commerce

Step 3: Fallback
  └─ If still None: commerce = "FALABELLA"
```

---

## Example Scenarios

### Scenario 1: Root is FALABELLA, but seller is IKEA
```json
{
  "commerce": "FALABELLA",  // Root level
  "fulfilmentOrder": {
    "logisticGroups": [{
      "orderItems": [{
        "itemInfo": {
          "sellerId": "IKEA_CHILE"  // Contains IKEA
        }
      }]
    }]
  }
}
```

**Result**: commerce = "IKEA" ✓ (corrected from root)

### Scenario 2: Root is IKEA
```json
{
  "commerce": "IKEA",  // Root level
  "fulfilmentOrder": { ... }
}
```

**Result**: commerce = "IKEA" ✓ (confirmed at root)

### Scenario 3: No root commerce, IKEA in seller
```json
{
  "fulfilmentOrder": {
    "logisticGroups": [{
      "orderItems": [{
        "itemInfo": {
          "sellerId": "IKEA_PERU"  // Contains IKEA
        }
      }]
    }]
  }
}
```

**Result**: commerce = "IKEA" ✓ (detected in seller)

### Scenario 4: No IKEA anywhere
```json
{
  "fulfilmentOrder": {
    "logisticGroups": [{
      "orderItems": [{
        "itemInfo": {
          "sellerId": "FAL_STORE"  // No IKEA
        }
      }]
    }]
  }
}
```

**Result**: commerce = "FALABELLA" ✓ (default fallback)

---

## Code Change

```python
# BEFORE: Only check if commerce not set
if not commerce:
    if not commerce:  # Redundant check
        foorc = foorch.get("fulfilmentOrder", {})
        for group in foorc.get("logisticGroups", []):
            for item in group.get("orderItems", []):
                seller_id = item.get("itemInfo", {}).get("sellerId", "")
                if "IKEA" in str(seller_id).upper():
                    commerce = "IKEA"
    if not commerce:
        commerce = "FALABELLA"

# AFTER: Always check for IKEA override
if not commerce:
    if "commerce" in foorch:
        commerce = foorch.get("commerce", "").upper()

# Always check fulfilmentOrder for IKEA (overrides)
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
```

---

## Key Improvements

✅ **IKEA Override**: Seller IKEA always takes precedence
✅ **Robust Detection**: Works with multiple fallback locations
✅ **Cleaner Logic**: Removed redundant nested `if not commerce` checks
✅ **Better Error Handling**: Exception handling still present
✅ **Correct Panel Mapping**: Now correctly determines IKEA vs FALABELLA panels

---

## Impact on Panel Determination

| Scenario | Old Result | New Result | Impact |
|----------|-----------|-----------|--------|
| Root FALABELLA + Seller IKEA | FALABELLA (wrong) | IKEA (correct) | ✅ Fixed |
| Root empty + Seller IKEA | IKEA (correct) | IKEA (same) | ✓ Maintained |
| Root IKEA + any seller | IKEA (correct) | IKEA (same) | ✓ Maintained |
| No commerce info | FALABELLA (correct) | FALABELLA (same) | ✓ Maintained |

---

## Testing

```python
def test_commerce_detection():
    # Test 1: FALABELLA root with IKEA seller
    foorch = {
        "commerce": "FALABELLA",
        "fulfilmentOrder": {
            "logisticGroups": [{
                "orderItems": [{
                    "itemInfo": {"sellerId": "IKEA_CHILE"}
                }]
            }]
        }
    }
    result = determine_panel(foorch, "FALABELLA_GROUP", False, None)
    assert result == "trmg-ikea"  # IKEA detected from seller
    
    # Test 2: No root commerce, IKEA seller
    foorch = {
        "fulfilmentOrder": {
            "logisticGroups": [{
                "orderItems": [{
                    "itemInfo": {"sellerId": "IKEA_PERU"}
                }]
            }]
        }
    }
    result = determine_panel(foorch, "FALABELLA_GROUP", False, None)
    assert result == "trmg-ikea"  # IKEA detected from seller
    
    # Test 3: FALABELLA with no IKEA
    foorch = {
        "commerce": "FALABELLA",
        "fulfilmentOrder": {
            "logisticGroups": [{
                "orderItems": [{
                    "itemInfo": {"sellerId": "FAL_STORE"}
                }]
            }]
        }
    }
    result = determine_panel(foorch, "FALABELLA_GROUP", False, None)
    assert result == "trmg-geosort"  # FALABELLA with FALABELLA_GROUP
```

---

## Summary

The updated logic now **always checks for IKEA in the seller info**, allowing it to override the root commerce field. This ensures more accurate panel determination regardless of how the FOORCH data is structured.
