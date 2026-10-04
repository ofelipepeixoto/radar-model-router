"""Original safe wrapper around attributed upstream numerical policy."""
from dataclasses import asdict, dataclass
from .contracts import Prediction, RouteInput, Scope, TASK_TIERS, TIERS
from .vendor import jev_policy

POLICY_VERSION = "radar-v1-local"

@dataclass(frozen=True)
class Decision:
    tier: int
    tier_name: str
    effort: str
    review_required: bool
    source: str
    policy: str = POLICY_VERSION
    shadow: bool = True
    paid_enabled: bool = False
    def to_dict(self):
        return asdict(self)

def decide(value: RouteInput, scope: Scope, prediction: Prediction | None = None) -> Decision:
    tier = TASK_TIERS[value.task]
    if value.continuation:
        tier = max(tier, value.current_tier)
    effort = ("low", "medium", "high", "xhigh")[tier]
    source = "static"
    predicted_risk = False
    if prediction is not None:
        proposed = jev_policy.decide(prediction.answers(), value.current_tier)
        tier, effort, source = proposed.tier, proposed.effort, "jev-policy-replay"
        predicted_risk = prediction.stakes >= jev_policy.STAKES_FLOOR
        if value.continuation:
            tier = max(tier, value.current_tier)
    tier = max(tier, scope.minimum_tier)
    effort = ("low", "medium", "high", "xhigh")[max(tier, ("low", "medium", "high", "xhigh").index(effort))]
    review = scope.require_review or value.risk == "high" or predicted_risk
    if review:
        tier, effort = 3, "xhigh"
    return Decision(tier, TIERS[tier], effort, review, source)
