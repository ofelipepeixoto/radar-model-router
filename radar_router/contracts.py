"""Strict, metadata-only contracts. No prompt, key or transport belongs here."""
from dataclasses import dataclass
import hashlib
import json
import math
import re

class ContractError(ValueError):
    pass

TIERS = ("leve", "padrao", "pesado", "maximo")
TASK_TIERS = {"lookup": 0, "draft": 1, "analysis": 2, "architecture": 3}
RISKS = {"low", "high"}
IDENTIFIER = re.compile(r"[a-zA-Z0-9_.:-]{1,64}\Z")

def identifier(value):
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ContractError("invalid_identifier")
    return value

def integer(value, lower, upper):
    if type(value) is not int or not lower <= value <= upper:
        raise ContractError("invalid_integer")
    return value

def number(value, lower, upper):
    if type(value) not in (int, float) or not math.isfinite(value) or not lower <= value <= upper:
        raise ContractError("invalid_number")
    return float(value)

def parse_json(raw, maximum=8192):
    if not isinstance(raw, bytes) or len(raw) > maximum:
        raise ContractError("payload_limit")
    def reject_constant(_):
        raise ContractError("nonfinite_json")
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ContractError("duplicate_json_key")
            result[key] = value
        return result
    try:
        return json.loads(raw, parse_constant=reject_constant, object_pairs_hook=unique)
    except (ValueError, UnicodeDecodeError, RecursionError) as exc:
        raise ContractError("invalid_json") from exc

@dataclass(frozen=True)
class Scope:
    """Constructed by a trusted caller, never deserialized from remote user input.

    CLI is a local laboratory; this dataclass does not authenticate anyone.
    """
    tenant: str
    minimum_tier: int = 0
    require_review: bool = False
    def __post_init__(self):
        identifier(self.tenant)
        integer(self.minimum_tier, 0, 3)
        if type(self.require_review) is not bool:
            raise ContractError("invalid_scope")

@dataclass(frozen=True)
class RouteInput:
    session: str
    turn: str
    task: str
    risk: str
    current_tier: int
    continuation: bool
    @classmethod
    def from_dict(cls, value):
        fields = {"session", "turn", "task", "risk", "current_tier", "continuation"}
        if not isinstance(value, dict) or set(value) != fields:
            raise ContractError("input_schema")
        identifier(value["session"])
        identifier(value["turn"])
        if not isinstance(value["task"], str) or value["task"] not in TASK_TIERS:
            raise ContractError("unknown_task")
        if not isinstance(value["risk"], str) or value["risk"] not in RISKS:
            raise ContractError("unknown_risk")
        integer(value["current_tier"], 0, 3)
        if type(value["continuation"]) is not bool:
            raise ContractError("invalid_continuation")
        return cls(**value)
    def metadata(self):
        return {"task": self.task, "risk": self.risk, "current_tier": self.current_tier,
                "continuation": self.continuation}

@dataclass(frozen=True)
class Prediction:
    probabilities: tuple
    effort: float
    continuation: float
    stakes: float
    def __post_init__(self):
        if not isinstance(self.probabilities, tuple) or len(self.probabilities) != 4:
            raise ContractError("prediction_schema")
        values = [number(x, 0, 1) for x in self.probabilities]
        if not math.isclose(sum(values), 1, rel_tol=0, abs_tol=1e-9):
            raise ContractError("probability_sum")
        number(self.effort, 0, 3)
        number(self.continuation, 0, 1)
        number(self.stakes, 0, 1)
    def record(self):
        return {"probabilities": list(self.probabilities), "effort": self.effort,
                "continuation": self.continuation, "stakes": self.stakes}
    def answers(self):
        return {"tier": {"probabilities": dict(zip(TIERS, self.probabilities))},
                "effort": {"score": self.effort},
                "continuation": {"noul": self.continuation}, "stakes": {"noul": self.stakes}}

def fingerprint(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()
