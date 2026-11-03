#!/usr/bin/env python3
"""Validate a Cloudflare Turnstile token for an authorized integration test."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def verify_token(secret: str, token: str, remote_ip: str | None = None) -> dict:
    """Submit one token to Cloudflare's official Siteverify endpoint."""
    fields = {"secret": secret, "response": token}
    if remote_ip:
        fields["remoteip"] = remote_ip

    body = urllib.parse.urlencode(fields).encode("utf-8")
    request = urllib.request.Request(
        SITEVERIFY_URL,
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Siteverify returned HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"Could not reach Siteverify: {error.reason}") from error


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate one Turnstile token for an authorized integration test."
    )
    parser.add_argument("--token", required=True, help="Token returned by your own widget")
    parser.add_argument("--hostname", help="Expected hostname returned by Siteverify")
    parser.add_argument("--action", help="Expected action returned by Siteverify")
    parser.add_argument("--remote-ip", help="Optional visitor IP used by your integration")
    args = parser.parse_args()

    secret = os.environ.get("TURNSTILE_SECRET_KEY")
    if not secret:
        print("TURNSTILE_SECRET_KEY is not set", file=sys.stderr)
        return 2

    try:
        result = verify_token(secret, args.token, args.remote_ip)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 1

    valid = bool(result.get("success"))
    if valid and args.hostname and result.get("hostname") != args.hostname:
        valid = False
        result.setdefault("local_errors", []).append("hostname mismatch")
    if valid and args.action and result.get("action") != args.action:
        valid = False
        result.setdefault("local_errors", []).append("action mismatch")

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
