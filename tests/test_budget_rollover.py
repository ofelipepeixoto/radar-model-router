"""Synthetic UTC rollover tests; no provider or external service is called."""
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from radar_router.ledger import Ledger, LedgerError


class BudgetRollover(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = Ledger(self.tmp.name)

    def utc(self, value):
        # reserve() reads gmtime(), not time.time(): advance its actual clock input.
        return patch("radar_router.ledger.time.gmtime",
                     return_value=time.strptime(value, "%Y-%m-%d %H:%M:%S"))

    def reserve(self, operation, maximum, tenant="synthetic"):
        return self.ledger.reserve(tenant, operation, maximum, 100, paid_enabled=True)

    def rows(self):
        with self.ledger.connect() as db:
            return db.execute(
                "SELECT day,maximum,actual,state FROM reservations ORDER BY day"
            ).fetchall()

    def test_unresolved_reservations_survive_midnight_and_restart(self):
        for state in ("reserved", "unknown"):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as directory:
                ledger = Ledger(directory)
                with self.utc("2026-10-10 23:59:59"):
                    key = ledger.reserve(state, "before", 100, 100, paid_enabled=True)
                    if state == "unknown":
                        ledger.reconcile(key)
                restarted = Ledger(directory)
                for day in ("2026-10-11", "2026-11-11"):
                    with self.utc(day + " 00:00:00"):
                        with self.assertRaisesRegex(LedgerError, "^budget_exceeded$"):
                            restarted.reserve(state, "after", 1, 100, paid_enabled=True)
                with restarted.connect() as db:
                    self.assertEqual(db.execute(
                        "SELECT day,maximum,actual,state FROM reservations"
                    ).fetchall(), [("2026-10-10", 100, None, state)])

    def test_previous_unknown_100_blocks_another_100(self):
        with self.utc("2026-10-10 23:59:59"):
            key = self.reserve("before", 100)
            self.ledger.reconcile(key)
        with self.utc("2026-10-11 00:00:00"):
            with self.assertRaisesRegex(LedgerError, "^budget_exceeded$"):
                self.reserve("after", 100)
        self.assertEqual(self.rows(), [("2026-10-10", 100, None, "unknown")])

    def test_carryover_and_current_settled_spend_share_the_limit(self):
        with self.utc("2026-10-09 23:59:59"):
            self.reserve("old-reserved", 30)
        with self.utc("2026-10-10 23:59:59"):
            key = self.reserve("old-unknown", 30)
            self.ledger.reconcile(key)
        with self.utc("2026-10-11 00:00:00"):
            key = self.reserve("today-settled", 30)
            self.ledger.reconcile(key, 20)
            self.reserve("remaining", 20)
            with self.assertRaisesRegex(LedgerError, "^budget_exceeded$"):
                self.reserve("excess", 1)

    def test_settled_spend_remains_on_its_original_utc_day(self):
        with self.utc("2026-10-10 23:59:59"):
            key = self.reserve("yesterday", 100)
            self.ledger.reconcile(key, 100)
        with self.utc("2026-10-11 00:00:00"):
            self.reserve("today", 100)
        self.assertEqual(self.rows(), [
            ("2026-10-10", 100, 100, "settled"),
            ("2026-10-11", 100, None, "reserved"),
        ])

    def test_late_reconciliation_releases_carryover_without_rebooking_day(self):
        for actual in (0, 25, 150):
            with self.subTest(actual=actual), tempfile.TemporaryDirectory() as directory:
                self.ledger = Ledger(directory)
                with self.utc("2026-10-10 23:59:59"):
                    key = self.reserve("old", 100)
                    self.ledger.reconcile(key)
                with self.utc("2026-10-11 00:00:00"):
                    self.ledger.reconcile(key)  # Unknown is still not zero.
                    with self.assertRaisesRegex(LedgerError, "^budget_exceeded$"):
                        self.reserve("blocked", 1)
                    if actual > 100:
                        with self.assertRaisesRegex(LedgerError, "^reservation_overrun_recorded$"):
                            self.ledger.reconcile(key, actual)
                    else:
                        self.ledger.reconcile(key, actual)
                    self.assertEqual(self.rows(), [("2026-10-10", 100, actual, "settled")])
                    self.reserve("new", 100)
                    with self.assertRaisesRegex(LedgerError, "^duplicate_reservation$"):
                        self.reserve("old", 1)

    def test_carryover_is_scoped_to_tenant(self):
        with self.utc("2026-10-10 23:59:59"):
            key = self.reserve("same-operation", 100)
            self.ledger.reconcile(key)
        with self.utc("2026-10-11 00:00:00"):
            self.reserve("same-operation", 100, tenant="other")
            with self.assertRaisesRegex(LedgerError, "^budget_exceeded$"):
                self.reserve("new", 1)

    def test_concurrent_admission_accounts_for_carried_reservation(self):
        with self.utc("2026-10-10 23:59:59"):
            key = self.reserve("old", 60)
            self.ledger.reconcile(key)

        def attempt(index):
            try:
                self.reserve("new-" + str(index), 40)
                return True
            except LedgerError as error:
                if str(error) != "budget_exceeded":
                    raise
                return False

        with self.utc("2026-10-11 00:00:00"):
            with ThreadPoolExecutor(max_workers=8) as pool:
                accepted = list(pool.map(attempt, range(12)))
        self.assertEqual(sum(accepted), 1)
        self.assertEqual(sum(row[1] for row in self.rows()), 100)

    def test_decision_retention_does_not_release_carried_reservations(self):
        with self.utc("2026-10-10 23:59:59"):
            key = self.reserve("pending", 100)
            self.ledger.reconcile(key)
        with patch("radar_router.ledger.time.time", return_value=100):
            self.ledger.get_or_create("decision", "old", lambda: {"tier": 1})
        with self.utc("2026-11-11 00:00:00"), patch(
                "radar_router.ledger.time.time", return_value=100 + 31 * 86400):
            self.ledger.get_or_create("decision", "new", lambda: {"tier": 2})
            with self.assertRaisesRegex(LedgerError, "^budget_exceeded$"):
                self.reserve("new", 1)
        self.assertEqual(self.rows(), [("2026-10-10", 100, None, "unknown")])
