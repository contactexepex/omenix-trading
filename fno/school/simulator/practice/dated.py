"""The configuration of one practice session (story MS-SIM-d2, criterion 11): the pilot's `cfg` with the charges in
force on that date (EDGE1's dated STT), never today's. Nothing else in `cfg` changes."""

from datetime import date

from ..terms import DatedTerms


def cfg_on(cfg: dict, terms: DatedTerms, session: date) -> dict:
    return {**cfg, "charges": dict(terms.charges(session))}
