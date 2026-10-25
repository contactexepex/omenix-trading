"""Names why a database call failed (story P6, run 38436281593): "OperationalError" alone could be a firewall, TLS,
the password or a missing privilege. The class comes from psycopg's exception type, its SQLSTATE and libpq's message;
the message itself is never printed (it names the host and the user)."""

from __future__ import annotations

NETWORK = "network: TCP timeout or refused (firewall?)"
FIREWALL = "firewall: the server refused this client's address"
TLS = "TLS or certificate"
AUTHENTICATION = "authentication"
PRIVILEGE = "permission denied (privilege)"
OTHER = "other"

AUTHENTICATION_STATES = ("28000", "28P01")  # invalid authorization, invalid password
PRIVILEGE_STATE = "42501"  # insufficient privilege
MESSAGES = (  # (lower-case words in libpq's or the server's message, class): first match wins
    (("not allowed to access the server", "no pg_hba.conf entry"), FIREWALL),
    (("ssl", "certificate", "tls", "sslrootcert"), TLS),
    (("password authentication failed", "authentication failed", "role", "password"), AUTHENTICATION),
    (("permission denied",), PRIVILEGE),
    (("timeout", "connection refused", "could not connect", "no route to host", "network is unreachable",
      "could not translate host name", "name or service not known"), NETWORK),
)  # fmt: skip


def failure_class(exc: BaseException) -> str:
    """One of NETWORK, FIREWALL, TLS, AUTHENTICATION, PRIVILEGE or OTHER."""
    state = getattr(exc, "sqlstate", None)
    if state in AUTHENTICATION_STATES:
        return AUTHENTICATION
    if state == PRIVILEGE_STATE:
        return PRIVILEGE
    if type(exc).__name__ == "ConnectionTimeout":
        return NETWORK
    text = str(exc).lower()
    return next((kind for words, kind in MESSAGES if any(word in text for word in words)), OTHER)


def described(exc: BaseException) -> str:
    """The class with the exception's type and SQLSTATE, safe to print and post (no host, user or password)."""
    state = getattr(exc, "sqlstate", None)
    return f"{failure_class(exc)} ({type(exc).__name__}{f', SQLSTATE {state}' if state else ''})"
