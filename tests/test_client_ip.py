"""Hardening tests for `get_client_ip` + the `_coerce_ip` helper.

Regression coverage for the rate-limit DoS vector:

  Pre-hardening, `get_client_ip` would return any string from
  `X-Forwarded-For` unchanged. `app/services/ai/rate_limit.py::_bump`
  then did `CAST(:ip AS inet)`, which Postgres rejects with
  `InvalidTextRepresentation` on anything that isn't a parseable
  IP literal. An attacker sending `X-Forwarded-For: garbage` would
  500 the request, abort the transaction, AND skip the counter
  increment — fully bypassing the throttle.

The fix (this file's subject) validates every candidate via
`ipaddress.ip_address(...)`, strips IPv4 / IPv6 port suffixes, and
falls through to `request.client.host` (also validated) or the
`0.0.0.0` sentinel.
"""
import pytest
from starlette.datastructures import Headers
from starlette.requests import Request

from app.core.deps import _coerce_ip, get_client_ip

# ---------------------------------------------------------------------------
# _coerce_ip — the lowest-level validator. Pure function; exhaustive
# boundary coverage so the helper can't drift into accepting unsafe
# inputs without a test failing.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        # Plain IPv4 / IPv6 — passes through unchanged.
        ("1.2.3.4", "1.2.3.4"),
        ("203.0.113.45", "203.0.113.45"),
        ("::1", "::1"),
        ("2001:db8::1", "2001:db8::1"),
        # Whitespace is trimmed (Cloudflare sometimes pads with spaces).
        ("  1.2.3.4  ", "1.2.3.4"),
        # IPv4 with port suffix (misconfigured proxies do this).
        ("1.2.3.4:5678", "1.2.3.4"),
        # IPv6 in bracketed form, with and without port.
        ("[2001:db8::1]:443", "2001:db8::1"),
        ("[::1]", "::1"),
    ],
)
def test_coerce_ip_accepts_valid(raw: str, expected: str) -> None:
    assert _coerce_ip(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        # The DoS vector: arbitrary garbage that Postgres would 500 on.
        "garbage",
        "unknown",
        "not an ip",
        # Empty / whitespace-only / None — fall-through, not a crash.
        "",
        "   ",
        None,
        # Looks-IP-ish but isn't (octet overflow, trailing dot, etc.).
        "256.256.256.256",
        "1.2.3",
        # SQL-injection-shaped (defense in depth — the parameterised
        # query already prevents injection, but the validator should
        # still reject this so the cast doesn't fail).
        "1.2.3.4'; DROP TABLE users; --",
        # Multi-IP value that wasn't pre-split (caller error).
        "1.2.3.4, 5.6.7.8",
    ],
)
def test_coerce_ip_rejects_invalid(raw: str | None) -> None:
    assert _coerce_ip(raw) is None


# ---------------------------------------------------------------------------
# get_client_ip — the integration point. Builds a minimal Starlette
# Request scope so we exercise the full dependency, not just _coerce_ip.
# ---------------------------------------------------------------------------


def _request(headers: dict[str, str] | None = None, client: tuple[str, int] | None = None) -> Request:
    """Build a Starlette Request with the given X-headers and client peer.

    Mirrors what FastAPI gives `Depends(get_client_ip)` at runtime.
    """
    scope: dict = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": Headers(headers or {}).raw,
        "query_string": b"",
    }
    if client is not None:
        scope["client"] = client
    return Request(scope)


def test_returns_forwarded_when_valid() -> None:
    req = _request(headers={"x-forwarded-for": "203.0.113.45"})
    assert get_client_ip(req) == "203.0.113.45"


def test_takes_leftmost_hop_of_xff() -> None:
    # `X-Forwarded-For` is a comma-separated chain: client, proxy1, proxy2.
    # We want the ORIGINAL client (leftmost), not the nearest proxy.
    req = _request(headers={"x-forwarded-for": "203.0.113.45, 10.0.0.1, 10.0.0.2"})
    assert get_client_ip(req) == "203.0.113.45"


def test_falls_through_to_socket_peer_when_xff_garbage() -> None:
    # The CRITICAL regression: malicious / malformed XFF must not
    # propagate into the inet cast. Fall through to the real socket
    # peer (the proxy's IP) instead — under-attributing the request
    # to the proxy is far better than crashing the throttle.
    req = _request(
        headers={"x-forwarded-for": "garbage"},
        client=("10.0.0.1", 12345),
    )
    assert get_client_ip(req) == "10.0.0.1"


def test_falls_through_to_socket_peer_when_xff_missing() -> None:
    req = _request(client=("10.0.0.1", 12345))
    assert get_client_ip(req) == "10.0.0.1"


def test_returns_sentinel_when_nothing_valid() -> None:
    # No XFF, no client tuple — the dependency must still produce a
    # string that Postgres' inet type accepts, otherwise `_bump`
    # would 500 on any locally-issued request without a client peer
    # (some test harnesses, some service workers).
    req = _request(headers={"x-forwarded-for": "completely bogus"})
    assert get_client_ip(req) == "0.0.0.0"


def test_strips_port_from_xff_ipv4() -> None:
    req = _request(headers={"x-forwarded-for": "1.2.3.4:8080"})
    assert get_client_ip(req) == "1.2.3.4"


def test_strips_brackets_and_port_from_xff_ipv6() -> None:
    req = _request(headers={"x-forwarded-for": "[2001:db8::1]:443"})
    assert get_client_ip(req) == "2001:db8::1"


def test_socket_peer_is_also_validated() -> None:
    # Defense in depth: even the socket peer string is run through
    # `_coerce_ip`. If a future ASGI server emits something like
    # `("unknown", 0)` we don't want to push that into the inet cast.
    req = _request(
        headers={"x-forwarded-for": "also garbage"},
        client=("not-an-ip", 0),
    )
    assert get_client_ip(req) == "0.0.0.0"
