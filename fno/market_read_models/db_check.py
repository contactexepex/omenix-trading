"""`market db-check` (story P6): connects as the publisher would and reads only who it is and what it may do, so the
owner and the orchestrator can retry a connection without a full archive run. Prints yes/no answers and the failure
class, never the URL, host, user or password."""

from __future__ import annotations

from collections.abc import Callable

WHO_AND_WHAT = """
select current_user = %(user)s,
       has_table_privilege('fno.pages_history', 'INSERT'), has_table_privilege('fno.pages_history', 'SELECT'),
       has_table_privilege('fno.current_publication', 'INSERT'),
       has_table_privilege('fno.current_publication', 'UPDATE'),
       has_table_privilege('fno.current_publication', 'SELECT')
"""
ANSWERS = (
    "current_user is the URL's user", "pages_history INSERT", "pages_history SELECT", "current_publication INSERT",
    "current_publication UPDATE", "current_publication SELECT",
)  # fmt: skip
CONNECTED = "database check: connected with TLS ({sslmode}, pinned Azure roots)"
FAILED = "database check FAILED: {cause}"


class DatabaseCheck:
    def __init__(self, url: str, connect: Callable, user_of: Callable[[str], str | None]):
        self._url, self._connect, self._user_of = url, connect, user_of  # the URL holds the credential

    def run(self) -> tuple[int, list[str]]:
        """(exit code, lines): 0 only when connected and every privilege the publisher needs is granted."""
        from psycopg import Error

        from .db_errors import described

        try:
            with self._connect(self._url) as connection:
                answers = connection.execute(WHO_AND_WHAT, {"user": self._user_of(self._url)}).fetchone()
                sslmode = connection.info.get_parameters().get("sslmode") or "TLS"
        except Error as exc:
            return 1, [FAILED.format(cause=described(exc))]
        lines = [CONNECTED.format(sslmode=sslmode)]
        lines += [f"    {name}: {'yes' if answer else 'NO'}" for name, answer in zip(ANSWERS, answers)]
        return (0 if all(answers) else 1), lines


def url_user(url: str) -> str | None:
    from psycopg.conninfo import conninfo_to_dict

    return conninfo_to_dict(url).get("user")
