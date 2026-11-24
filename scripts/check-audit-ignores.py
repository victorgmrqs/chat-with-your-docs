#!/usr/bin/env python3
"""Fail when an accepted advisory in osv-scanner.toml lacks a reason or a valid expiry (CWYD-24).

osv-scanner itself treats an entry without `ignoreUntil` as permanent; this check makes every
exception temporary and justified. Usage: scripts/check-audit-ignores.py [path] (default:
osv-scanner.toml). Standard library only, so CI runs it with the runner's python3.
"""

import datetime as dt
import sys
import tomllib

MAX_DAYS = 90


def problems(config: dict, today: dt.date) -> list[str]:
    found = []
    for index, entry in enumerate(config.get("IgnoredVulns", []), start=1):
        label = entry.get("id") or f"entry {index}"
        if not entry.get("id"):
            found.append(f"{label}: missing id")
        if not str(entry.get("reason", "")).strip():
            found.append(f"{label}: missing reason")
        until = entry.get("ignoreUntil")
        if isinstance(until, dt.datetime):
            until = until.date()
        if not isinstance(until, dt.date):
            found.append(f"{label}: missing ignoreUntil date")
        elif until < today:
            found.append(f"{label}: expired on {until}; fix it or review it again")
        elif until > today + dt.timedelta(days=MAX_DAYS):
            found.append(f"{label}: ignoreUntil {until} is more than {MAX_DAYS} days away")
    return found


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else "osv-scanner.toml"
    with open(path, "rb") as file:
        config = tomllib.load(file)
    found = problems(config, dt.datetime.now(dt.UTC).date())
    for problem in found:
        print(f"::error file={path}::{problem}")
    count = len(config.get("IgnoredVulns", []))
    print(f"{count} accepted advisories, {len(found)} problems")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
