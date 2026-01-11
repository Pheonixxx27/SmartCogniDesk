from sops.steps.find_ids import step_find_ids
from sops.steps.get_foorch import step_get_foorch
from sops.steps.validate_movep import step_validate_movep
from sops.steps.analyze_movep import step_analyze_movep

STEP_REGISTRY = {
    "find_ids": step_find_ids,
    "get_foorch": step_get_foorch,
    "validate_movep": step_validate_movep,
    "analyze_movep": step_analyze_movep,
}
