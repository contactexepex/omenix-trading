"""Story DR1's levels, paths and printed lines. No line holds a data value (a level or a price): the lines reach public
run logs; the values stay in Drive."""

from __future__ import annotations

PROVISIONAL, CERTIFIED = "provisional", "certified"
LEVELS = (PROVISIONAL, CERTIFIED)
DATA_AREA = "data"  # O9's Drive area (fno/storage/data_wiring.py)
STAGING_ROOT = "staging"  # data/staging/<dataset>/<session>/<fetched_at>_<run_id><suffix>
RECORDS_FOLDER = "receipts/records"  # receipts/records/<dataset>/<yyyy>/<mm>/<session>.<level>.json, in git
STAGED_NAME = "{fetched_at:%Y%m%dT%H%M%S%fZ}_{run_id}{suffix}"
INTEGRITY = "integrity"

CERTIFIED_LINE = "{dataset} {session} {level}: recorded {sha}, {passed} of {total} version(s) passed; {reason}"
NOT_CERTIFIED = "{dataset} {session} {level}: NOT recorded: {reason}"
ALREADY = "{dataset} {session} {level}: already recorded {sha}"
CONFLICT = "{dataset} {session} {level}: conflict: the record names {held}, this run chose {sha}; a person decides"
NOT_PUSHED = "{dataset} {session} {level}: record NOT pushed: {why}; the next run pushes it again"
ALERT = "Omenix F&O records: {line}"
UNREADABLE_LINE = "{dataset} {session} {level}: NOT recorded: a source could not be read: {why}; nothing is certified"
NO_VERSIONS = "no staged version"
NONE_PASSED = "no version passed: {failures}"
NOT_RECORDED = "{dataset} {session}: no {level} record"
NOT_READABLE = "{dataset} {session}: the {level} record's file is {why}"
SEEN_LINE = "{dataset} {session} {level}: {path} sha256 {sha}"
RECORDS_MESSAGE = "Records: DR1 certification ({what})"
RECORDS_LABEL = "records"
