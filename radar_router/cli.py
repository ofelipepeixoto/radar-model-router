"""Local CLI, single metadata JSON input. Output never echoes input or exceptions."""
import argparse
import json
import sqlite3
import sys
from .contracts import ContractError, Scope, parse_json
from .ledger import Ledger, LedgerError
from .service import Router

def main(argv=None):
    parser = argparse.ArgumentParser(description="Local shadow routing: no prompts, no paid API")
    parser.add_argument("--state-dir", default=".router-state")
    parser.add_argument("--tenant", default="local-lab")
    parser.add_argument("--minimum-tier", type=int, choices=range(4), default=0)
    parser.add_argument("--require-review", action="store_true")
    args = parser.parse_args(argv)
    try:
        payload = parse_json(sys.stdin.buffer.read(8193))
        scope = Scope(args.tenant, args.minimum_tier, args.require_review)
        result = Router(Ledger(args.state_dir)).route(payload, scope)
        print(json.dumps(result, sort_keys=True, allow_nan=False))
        return 0
    except (ContractError, LedgerError, OSError, sqlite3.Error):
        print('{"error":"routing_rejected"}', file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
