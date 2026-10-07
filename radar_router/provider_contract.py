"""Offline provider eligibility and conservative failover advice.

Only a trusted executor may supply capabilities, allowlists and outcomes. A plan
does not authenticate a caller, reserve money, dispatch a request or validate
model output.
"""
from dataclasses import dataclass

from .contracts import ContractError, identifier, integer


@dataclass(frozen=True)
class ProviderCapability:
    provider: str
    api_mode: str
    context_window: int
    max_output_tokens: int
    json_schema: bool
    streaming: bool

    def __post_init__(self):
        identifier(self.provider)
        identifier(self.api_mode)
        integer(self.context_window, 1, 10**7)
        integer(self.max_output_tokens, 1, 10**7)
        if type(self.json_schema) is not bool or type(self.streaming) is not bool:
            raise ContractError("capability_schema")
        if self.max_output_tokens > self.context_window:
            raise ContractError("capability_schema")


@dataclass(frozen=True)
class Plan:
    status: str
    reason: str
    provider: str | None
    # This never authorizes a paid operation or a network connection.
    paid_enabled: bool = False


def select_provider(candidates: tuple[ProviderCapability, ...], *,
                    allowed: tuple[str, ...], api_mode: str,
                    input_tokens: int, output_tokens: int,
                    json_schema: bool = False, streaming: bool = False,
                    failures: tuple[tuple[str, str], ...] = ()) -> Plan:
    """Select the first eligible provider or abstain, with fail-closed outcomes.

    A confirmed pre-dispatch failure can advance to another allowed provider.
    A timeout/unknown charge or an invalid output blocks failover: the executor
    must reconcile the original reservation and request review separately.
    """
    if not isinstance(candidates, tuple) or not candidates or not all(
        isinstance(c, ProviderCapability) for c in candidates
    ) or not isinstance(allowed, tuple) or not allowed:
        raise ContractError("provider_schema")
    names = tuple(c.provider for c in candidates)
    if len(set(names)) != len(names) or len(set(allowed)) != len(allowed):
        raise ContractError("provider_schema")
    for name in allowed:
        identifier(name)
    identifier(api_mode)
    integer(input_tokens, 0, 10**7)
    integer(output_tokens, 1, 10**7)
    if type(json_schema) is not bool or type(streaming) is not bool:
        raise ContractError("provider_schema")
    if not isinstance(failures, tuple) or any(
        not isinstance(f, tuple) or len(f) != 2 or f[0] not in names or
        f[1] not in ("pre_dispatch", "timeout_unknown", "quota_unknown", "invalid_output")
        for f in failures
    ) or len({f[0] for f in failures}) != len(failures):
        raise ContractError("failure_schema")
    outcomes = dict(failures)
    if any(reason != "pre_dispatch" for reason in outcomes.values()):
        return Plan("abstain", "outcome_requires_reconciliation", None)
    for cap in candidates:
        if cap.provider not in allowed or cap.provider in outcomes or cap.api_mode != api_mode:
            continue
        if input_tokens + output_tokens > cap.context_window or output_tokens > cap.max_output_tokens:
            continue
        if json_schema and not cap.json_schema or streaming and not cap.streaming:
            continue
        return Plan("selected", "eligible_offline", cap.provider)
    return Plan("abstain", "no_eligible_provider", None)
