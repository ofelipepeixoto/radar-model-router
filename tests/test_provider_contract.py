import unittest

from radar_router.contracts import ContractError
from radar_router.provider_contract import ProviderCapability, select_provider


class ProviderContract(unittest.TestCase):
    def setUp(self):
        self.small = ProviderCapability("small", "chat", 100, 30, False, False)
        self.large = ProviderCapability("large", "chat", 1000, 300, True, True)

    def select(self, **changes):
        args = dict(candidates=(self.small, self.large), allowed=("small", "large"),
                    api_mode="chat", input_tokens=50, output_tokens=20)
        args.update(changes)
        return select_provider(**args)

    def test_first_eligible_and_no_paid_authorization(self):
        result = self.select()
        self.assertEqual((result.status, result.provider), ("selected", "small"))
        self.assertFalse(result.paid_enabled)

    def test_context_and_schema_requirements_skip_incapable(self):
        self.assertEqual(self.select(input_tokens=90).provider, "large")
        self.assertEqual(self.select(json_schema=True, streaming=True).provider, "large")

    def test_disallowed_and_unsupported_abstain(self):
        for changes in (dict(allowed=("other",)), dict(api_mode="responses"),
                        dict(input_tokens=990),
                        dict(allowed=("small",), json_schema=True)):
            with self.subTest(changes=changes):
                result = self.select(**changes)
                self.assertEqual((result.status, result.provider), ("abstain", None))

    def test_confirmed_pre_dispatch_can_fail_over(self):
        self.assertEqual(self.select(failures=(("small", "pre_dispatch"),)).provider, "large")

    def test_uncertain_or_invalid_outcome_never_fails_over(self):
        for reason in ("timeout_unknown", "quota_unknown", "invalid_output"):
            with self.subTest(reason=reason):
                result = self.select(failures=(("small", reason),))
                self.assertEqual((result.status, result.provider, result.reason),
                                 ("abstain", None, "outcome_requires_reconciliation"))

    def test_reject_ambiguous_or_malformed_metadata(self):
        for changes in (dict(candidates=(self.small, self.small)),
                        dict(allowed=("small", "small")),
                        dict(output_tokens=True),
                        dict(failures=(("unknown", "pre_dispatch"),)),
                        dict(failures=(("small", "pre_dispatch"), ("small", "pre_dispatch")))):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                self.select(**changes)
        with self.assertRaises(ContractError):
            ProviderCapability("bad", "chat", 100, 101, False, False)


if __name__ == "__main__":
    unittest.main()
