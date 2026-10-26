#!/bin/sh
# Regenerates the hashed lock files from their editable inputs (story SEC1). Run by a maintainer, never by a job:
#
#     sh ops/relock.sh            # then review `git diff -- '*.lock'` and commit the inputs and locks together
#
# requirements.txt        -> requirements.lock        (the 14 workflows; installed with --only-binary :all:)
# requirements.txt + requirements-groww.txt -> requirements-groww.lock   (the Groww routine session)
# requirements-oauth.txt  -> requirements-oauth.lock  (ops/gdrive_oauth_setup.py, run on the owner's computer)
#
# `uv` asks PyPI for every file's SHA-256 here, so uv is the trust root of the hashes: install it from astral.sh (the
# maintainer's own machine, never a job) and read the diff of every bump (a hash proves the file is the one locked, not that it is safe).
# `--universal` resolves once for every platform; `--python-version 3.11` keeps every pin installable on the oldest
# interpreter the routines use (3.11 and 3.13 give identical pins). Lock files are never edited by hand.
set -eu
cd "$(git rev-parse --show-toplevel)"
command -v uv >/dev/null 2>&1 || { echo "relock FAILED: uv is not installed (see astral.sh)" >&2; exit 1; }

uv_version=$(uv --version | cut -d' ' -f2)
lock() {
    output=$1
    shift
    uv pip compile --generate-hashes --universal --python-version 3.11 --quiet -o "$output" "$@"
    # The version of uv that made the hashes is part of the evidence, so the next bump can compare (story SEC1, claim 3)
    sed -i.bak "1i # uv-version: $uv_version" "$output" && rm -f "$output.bak"
    echo "wrote $output ($(grep -c '^[A-Za-z0-9]' "$output") packages, $(grep -c -- '--hash=sha256:' "$output") hashes)"
}

lock requirements.lock requirements.txt
lock requirements-groww.lock requirements.txt requirements-groww.txt
lock requirements-oauth.lock requirements-oauth.txt
