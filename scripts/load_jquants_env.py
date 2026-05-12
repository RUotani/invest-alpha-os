#!/usr/bin/env python3
"""Load whitelisted J-Quants keys from a .env file without executing shell (no source/eval).

Parse KEY=VALUE lines only; ignore comments and blank lines; optional ``export`` prefix.
Values are never printed."""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

_ALLOWED_KEYS = frozenset(
    {
        "JQUANTS_ENABLED",
        "JQUANTS_ALLOW_LIVE_HTTP",
        "JQUANTS_API_VERSION",
        "JQUANTS_API_BASE_URL",
        "JQUANTS_API_KEY",
        "JQUANTS_DATA_AVAILABLE_FROM",
        "JQUANTS_DATA_AVAILABLE_TO",
        "JQUANTS_EMAIL",
        "JQUANTS_PASSWORD",
        "JQUANTS_REFRESH_TOKEN",
        "JQUANTS_ID_TOKEN",
    }
)


def _strip_matching_quotes(val: str) -> str:
    if len(val) >= 2 and val[0] == val[-1] and val[0] in {'"', "'"}:
        return val[1:-1]
    return val


def parse_jquants_env_file(path: Path) -> dict[str, str]:
    """Return whitelisted KEY -> raw value from *path* (no shell execution)."""

    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8", errors="replace")
    out: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, _, rest = line.partition("=")
        key = key.strip()
        if key not in _ALLOWED_KEYS:
            continue
        val = rest.rstrip("\r\n")
        val = _strip_matching_quotes(val.strip())
        out[key] = val
    return out


def _describe_boolish(name: str, raw: str) -> str:
    if not raw:
        return f"{name}: missing\n"
    v = raw.strip().lower()
    if v in {"true", "1", "yes"}:
        return f"{name}: true\n"
    if v in {"false", "0", "no"}:
        return f"{name}: false\n"
    return f"{name}: present (non-boolean literal; value hidden)\n"


def _describe_plain(name: str, raw: str) -> str:
    if not raw:
        return f"{name}: missing\n"
    return f"{name}: present (value hidden)\n"


_VARS_BOOLISH = (
    "JQUANTS_ENABLED",
    "JQUANTS_ALLOW_LIVE_HTTP",
)
_VARS_PLAIN = (
    "JQUANTS_API_VERSION",
    "JQUANTS_API_BASE_URL",
    "JQUANTS_API_KEY",
    "JQUANTS_DATA_AVAILABLE_FROM",
    "JQUANTS_DATA_AVAILABLE_TO",
    "JQUANTS_EMAIL",
    "JQUANTS_PASSWORD",
    "JQUANTS_REFRESH_TOKEN",
    "JQUANTS_ID_TOKEN",
)


def cmd_doctor(env_file: Path) -> int:
    parsed = parse_jquants_env_file(env_file)
    for name in _VARS_BOOLISH:
        sys.stdout.write(_describe_boolish(name, parsed.get(name, "")))
    for name in _VARS_PLAIN:
        sys.stdout.write(_describe_plain(name, parsed.get(name, "")))
    return 0


def _parse_set_args(pairs: list[str]) -> dict[str, str]:
    extra: dict[str, str] = {}
    for p in pairs:
        if "=" not in p:
            print(f"load_jquants_env: --set expects KEY=VALUE, got {p!r}", file=sys.stderr)
            raise SystemExit(2)
        k, _, v = p.partition("=")
        k = k.strip()
        if k not in _ALLOWED_KEYS:
            print(f"load_jquants_env: disallowed key in --set: {k}", file=sys.stderr)
            raise SystemExit(2)
        extra[k] = v
    return extra


def cmd_run(env_file: Path, extra_pairs: list[str], cmd_argv: list[str]) -> int:
    if not cmd_argv:
        print("load_jquants_env: run requires a command after --", file=sys.stderr)
        return 2
    parsed_file = parse_jquants_env_file(env_file)
    extra = _parse_set_args(extra_pairs)
    child_env = os.environ.copy()
    for k, v in parsed_file.items():
        child_env[k] = v
    for k, v in extra.items():
        child_env[k] = v
    proc = subprocess.run(cmd_argv, env=child_env)
    return int(proc.returncode)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: load_jquants_env.py {doctor|run ...}\n", file=sys.stderr)
        return 2

    cmd = argv[0]
    if cmd == "doctor":
        p = argparse.ArgumentParser(prog="load_jquants_env.py doctor")
        p.add_argument("--env-file", type=Path, default=Path(".env"))
        ns = p.parse_args(argv[1:])
        return cmd_doctor(ns.env_file)

    if cmd == "run":
        if "--" not in argv:
            print("load_jquants_env: run mode requires -- before the command", file=sys.stderr)
            return 2
        idx = argv.index("--")
        run_args = argv[1:idx]
        cmd_argv = argv[idx + 1 :]
        rparser = argparse.ArgumentParser(prog="load_jquants_env.py run")
        rparser.add_argument("--env-file", type=Path, default=Path(".env"))
        rparser.add_argument("--set", dest="extra_env", action="append", default=[])
        ns = rparser.parse_args(run_args)
        return cmd_run(ns.env_file, ns.extra_env, cmd_argv)

    print(f"load_jquants_env: unknown command {cmd!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
