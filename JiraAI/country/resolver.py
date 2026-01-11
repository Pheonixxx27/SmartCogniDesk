def detect_country_from_fo(fo_id: str):
    """
    Extract country from FO id.
    Example: FOFPE000013700523 → PE
    """
    if not fo_id.startswith("FOF") or len(fo_id) < 5:
        return None

    cc = fo_id[3:5]
    if cc in {"CL", "PE", "CO"}:
        return cc

    return None


def country_fallback_order(primary=None):
    order = ["CL", "PE", "CO"]
    if primary and primary in order:
        order.remove(primary)
        return [primary] + order
    return order
