"""Pure adapter contracts. Nothing authenticates, executes or calls a provider."""
from dataclasses import dataclass
from copy import deepcopy
from .contracts import ContractError, TIERS, identifier, integer

@dataclass(frozen=True)
class Capabilities:
    provider: str
    api_mode: str
    models: tuple
    output_caps: tuple
    def __post_init__(self):
        identifier(self.provider)
        identifier(self.api_mode)
        if not isinstance(self.models, tuple) or len(self.models) != 4:
            raise ContractError("capabilities_schema")
        for model in self.models:
            identifier(model)
        if not isinstance(self.output_caps, tuple) or len(self.output_caps) != 4:
            raise ContractError("capabilities_schema")
        for cap in self.output_caps:
            integer(cap, 1, 1000000)

def hermes_request(decision, *, provider, api_mode, request, capabilities, enabled=False):
    # Opt-in only; review-required decisions NEVER modify a live request.
    if not isinstance(decision, dict):
        raise ContractError("decision_schema")
    if enabled is not True or decision.get("review_required") is not False:
        return None
    if provider != capabilities.provider or api_mode != capabilities.api_mode:
        return None
    if not isinstance(request, dict) or request.get("model") not in capabilities.models:
        return None
    tier = integer(decision.get("tier"), 0, 3)
    if decision.get("tier_name") != TIERS[tier] or decision.get("policy") != "radar-v1-local":
        raise ContractError("decision_schema")
    result = deepcopy(request)
    result["model"] = capabilities.models[tier]
    cap = capabilities.output_caps[tier]
    if "max_tokens" in result:
        result["max_tokens"] = min(integer(result["max_tokens"], 1, 1000000), cap)
    else:
        result["max_tokens"] = cap
    # Effort parameters are provider-specific. Do not assume OAuth/Anthropic shapes.
    return {"request": result, "source": "radar-model-router", "reason": decision["tier_name"]}
