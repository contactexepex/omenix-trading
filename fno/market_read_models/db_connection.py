"""The publisher's database connection (story P6): always TLS with the server verified against the pinned Azure root
CAs in `db/fno/azure-postgres-roots.pem`, whatever the URL says. Not `sslrootcert=system`: psycopg-binary's bundled
OpenSSL looks for system roots in its build machine's folder (/host/tmp/libpq.build), so "system" trusts nothing
(response 50, addendum 4). The URL holds the credential: never printed."""

from __future__ import annotations

from pathlib import Path

VERIFIED = "verify-full"
CONNECT_TIMEOUT_SECONDS = "15"  # a firewall that drops packets fails fast, named "network" (libpq waits forever)


class VerifiedConnection:
    """A `connect(url)` callable for PostgresPublisher and DatabaseCheck."""

    def __init__(self, roots: Path):
        self.roots = Path(roots)

    def options(self) -> dict[str, str]:
        """Connection options that override the URL's own (libpq takes the later value)."""
        return {"sslmode": VERIFIED, "sslrootcert": str(self.roots), "connect_timeout": CONNECT_TIMEOUT_SECONDS}

    def __call__(self, url: str):
        import psycopg

        return psycopg.connect(url, autocommit=False, **self.options())
