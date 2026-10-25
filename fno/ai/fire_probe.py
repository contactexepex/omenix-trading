"""Story G11 fire probe (orchestrator, 25 Oct 2026): proves once, before the first v4 fire, that the routine API's
`/fire` takes a text the size of a v4 pointer (about 18-19 KB; `ROUTINE_POINTER_MAX_BYTES` was never confirmed
against the API). It fires Book 3's routine through the same trigger as v4-fire with a harmless text: one line,
ending in exactly one single quote. The stored prompt's step 2 stops on that quote before anything runs ("pointer
refused (not one line of JSON)"); a truncated text has lost the quote and `brief` refuses it instead. Either way
nothing is committed, no fire log is written and no slot is touched. It prints the API's answer and the session link
only, never the token."""

from __future__ import annotations

import json

from ..constants_operations import ROUTINE_POINTER_MAX_BYTES
from ..pipeline.trigger import FireFailed, RoutineTrigger

PROBE_BYTES = 24 * 1024  # the v4 pointer's size with about 25% margin, well under the cap
PROBE_NOTE = "routine fire size probe (G11, 25 Oct 2026): not a forecast; the routine stops at its step 2"
FIRED = "Omenix F&O fire probe: fired {bytes:,} bytes to {routine}: {link}"
NOT_FIRED = "Omenix F&O fire probe: NOT fired ({bytes:,} bytes to {routine}): {reason}"
NO_LINK = "no session link in the API's answer"


class ProbeText:
    """The probe's fired text: compact JSON padded to exactly `PROBE_BYTES`, then one single quote."""

    def to_text(self) -> str:
        head = json.dumps({"note": PROBE_NOTE, "pad": ""}, separators=(",", ":"))
        pad = "x" * (PROBE_BYTES - len(head) - 1)
        return json.dumps({"note": PROBE_NOTE, "pad": pad}, separators=(",", ":")) + "'"


def fire_probe(trigger: RoutineTrigger) -> tuple[bool, str]:
    """One fire with the probe text: (fired, the line to print)."""
    size = len(ProbeText().to_text().encode("utf-8"))
    if size > ROUTINE_POINTER_MAX_BYTES:
        return False, NOT_FIRED.format(bytes=size, routine=trigger.name, reason="over the pointer cap")
    try:
        link = trigger.fire(ProbeText())
    except FireFailed as failed:
        return False, NOT_FIRED.format(bytes=size, routine=trigger.name, reason=failed)
    return True, FIRED.format(bytes=size, routine=trigger.name, link=link or NO_LINK)
