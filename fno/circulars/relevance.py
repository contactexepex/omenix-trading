"""Which circulars matter to the F&O desk (story A20b): the strategy deciding which files are kept. It only flags a
row; every circular is listed whatever it says."""

from __future__ import annotations

from .model import NSE, SEBI, Circular

NSE_FNO_DEPARTMENTS = ("Futures & Options",)  # NSE Clearing's F&O margin circulars carry it too (NCL/CMPT/76975)
# NSE: keywords only for other departments (its Commodity and Currency Derivatives departments also say "derivative")
NSE_KEYWORDS = ("f&o", "lot size", "position limit", "mwpl", "ban period", "equity derivative", "index derivative")
SEBI_KEYWORDS = ("derivative", "f&o", "lot size", "position limit", "mwpl", "margin", "expiry", "index option")
KEYWORDS = {NSE: NSE_KEYWORDS, SEBI: SEBI_KEYWORDS}


class FnoRelevance:
    def __call__(self, circular: Circular) -> bool:
        if circular.source == NSE and any(d in NSE_FNO_DEPARTMENTS for d in circular.departments):
            return True
        subject = circular.subject.lower()
        return any(word in subject for word in KEYWORDS[circular.source])
