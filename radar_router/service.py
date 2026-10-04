"""Metadata-only local service; no network server or model execution."""
from .contracts import RouteInput, Scope, Prediction, fingerprint
from .ledger import Ledger
from .policy import POLICY_VERSION, decide

class Router:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger
    def route(self, payload: dict, scope: Scope, prediction: Prediction | None = None):
        value = RouteInput.from_dict(payload)
        key = self.ledger.identity(scope.tenant, value.session, value.turn)
        fp = fingerprint({"metadata": value.metadata(), "minimum_tier": scope.minimum_tier,
                          "review": scope.require_review, "policy": POLICY_VERSION,
                          "prediction": prediction.record() if prediction is not None else None})
        return self.ledger.get_or_create(key, fp, lambda: decide(value, scope, prediction).to_dict())
