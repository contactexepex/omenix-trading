"""Protocol v4's pricing number (section 1.4): every v4 Black-76 runs at 6.5%, the pack's IV30, the EOD IV30 proxy of
the premium ratio window, and V4's and V5's leg IVs and parity forward. Never `config.yaml`'s `risk_free_rate`, which
other stories read and may move. Kept out of `terms.py`, whose bytes are in M1's method hash."""

V4_RISK_FREE_RATE = 0.065
