"""Persistent decisions and conservative budget reservations; no provider calls.

    Unknown paid outcomes remain reserved. Never expire/release them automatically.
"""
import hmac
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time
from contextlib import contextmanager
from .contracts import ContractError, identifier, integer

class LedgerError(RuntimeError):
    pass

class Ledger:
    def __init__(self, directory, retention_seconds=7*86400):
        integer(retention_seconds, 60, 30*86400)
        root = Path(directory)
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if root.is_symlink() or not root.is_dir():
            raise LedgerError("unsafe_state_directory")
        os.chmod(root, 0o700)
        key_path = root / "identity.key"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        try:
            fd = os.open(key_path, flags, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(fd, "wb") as stream:
                stream.write(secrets.token_bytes(32))
        if key_path.is_symlink() or not key_path.is_file():
            raise LedgerError("unsafe_identity_key")
        self._key = key_path.read_bytes()
        if len(self._key) != 32:
            raise LedgerError("invalid_identity_key")
        os.chmod(key_path, 0o600)
        self.path = root / "ledger.sqlite3"
        if self.path.is_symlink():
            raise LedgerError("unsafe_database")
        self.retention = retention_seconds
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS decisions (
                    identity TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
                    result TEXT NOT NULL, expires INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS reservations (
                    identity TEXT PRIMARY KEY, tenant TEXT NOT NULL, day TEXT NOT NULL,
                    maximum INTEGER NOT NULL CHECK(maximum > 0),
                    actual INTEGER CHECK(actual >= 0),
                    state TEXT NOT NULL CHECK(state IN ('reserved','unknown','settled')));
                CREATE INDEX IF NOT EXISTS budget_period ON reservations(tenant, day);
            ''')
        os.chmod(self.path, 0o600)
    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        try:
            db.execute("PRAGMA busy_timeout=5000")
            yield db
        finally:
            db.close()
    def identity(self, *parts):
        for value in parts:
            identifier(value)
        raw = json.dumps(parts, separators=(",", ":")).encode()
        return hmac.new(self._key, raw, hashlib.sha256).hexdigest()
    def get_or_create(self, identity, request_fingerprint, factory):
        now = int(time.time())
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute("DELETE FROM decisions WHERE expires <= ?", (now,))
                old = db.execute("SELECT fingerprint,result FROM decisions WHERE identity=?", (identity,)).fetchone()
                if old:
                    if old[0] != request_fingerprint:
                        raise LedgerError("idempotency_conflict")
                    result = json.loads(old[1])
                else:
                    result = factory()
                    raw = json.dumps(result, sort_keys=True, allow_nan=False)
                    db.execute("INSERT INTO decisions VALUES(?,?,?,?)", (identity, request_fingerprint, raw, now+self.retention))
                db.execute("COMMIT")
                return result
            except BaseException:
                db.execute("ROLLBACK")
                raise
    def reserve(self, tenant, operation, maximum_micro, daily_limit_micro, *, paid_enabled=False):
        # This is a building block, not authorization. Only a trusted executor may set these.
        if paid_enabled is not True:
            raise LedgerError("paid_disabled")
        integer(maximum_micro, 1, 10**12)
        integer(daily_limit_micro, 1, 10**12)
        identity, owner = self.identity(tenant, operation), self.identity(tenant)
        day = time.strftime("%Y-%m-%d", time.gmtime())
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                old = db.execute("SELECT maximum,state FROM reservations WHERE identity=?", (identity,)).fetchone()
                if old:
                    raise LedgerError("duplicate_reservation")
                used = db.execute("SELECT COALESCE(SUM(CASE WHEN state='settled' THEN actual ELSE maximum END),0) FROM reservations WHERE tenant=? AND day=?", (owner, day)).fetchone()[0]
                if used+maximum_micro > daily_limit_micro:
                    raise LedgerError("budget_exceeded")
                db.execute("INSERT INTO reservations VALUES(?,?,?,?,NULL,'reserved')", (identity,owner,day,maximum_micro))
                db.execute("COMMIT")
                return identity
            except BaseException:
                db.execute("ROLLBACK")
                raise
    def reconcile(self, identity, actual_micro=None):
        # None means outcome unknown, not zero charge.
        if actual_micro is not None:
            integer(actual_micro, 0, 10**12)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                old = db.execute("SELECT maximum,actual,state FROM reservations WHERE identity=?", (identity,)).fetchone()
                if not old:
                    raise LedgerError("unknown_reservation")
                if old[2] == "settled":
                    if actual_micro != old[1]:
                        raise LedgerError("reconciliation_conflict")
                elif actual_micro is None:
                    db.execute("UPDATE reservations SET state='unknown' WHERE identity=?", (identity,))
                else:
                    db.execute("UPDATE reservations SET state='settled',actual=? WHERE identity=?", (actual_micro,identity))
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise
        if actual_micro is not None and actual_micro > old[0]:
            raise LedgerError("reservation_overrun_recorded")
