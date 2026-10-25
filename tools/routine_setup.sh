#!/bin/sh
# One setup for every scheduled routine (story O7). On 15 Oct bare `pip` filled Python 3.13 while `python` and
# `python3` were 3.11, and the 3 pm recorder lost 14 minutes. This installs into every interpreter the routines and
# the commit hook can call, proves each one imports the packages, and stops loudly within seconds when it cannot.
#
#     sh tools/routine_setup.sh            # requirements.txt
#     sh tools/routine_setup.sh --groww    # plus requirements-groww.txt (the 3 pm recorder)
set -eu
cd "$(git rev-parse --show-toplevel)"
started=$(date +%s)

requirements="-r requirements.txt"
modules="numpy, requests, yaml"
if [ "${1:-}" = "--groww" ]; then
    requirements="$requirements -r requirements-groww.txt"
    modules="$modules, growwapi"
fi

# Install through each name's own executable (a virtual environment's python keeps its packages); the real path
# only spots two names that are one interpreter.
interpreters=""
seen=""
for name in python3 python; do
    path=$(command -v "$name" 2>/dev/null) || continue
    probe=$("$path" -c 'import os, sys; print(sys.executable, os.path.realpath(sys.executable))') || {
        echo "routine setup FAILED: '$name' ($path) does not run" >&2
        exit 1
    }
    executable=${probe% *}
    real=${probe##* }
    case " $seen " in *" $real "*) continue ;; esac
    seen="$seen $real"
    interpreters="$interpreters $executable"
done
[ -n "$interpreters" ] || { echo "routine setup FAILED: no python3 or python on PATH" >&2; exit 1; }

# A package the container's own installer (Debian's apt) put there has no RECORD file, so pip cannot uninstall it to
# upgrade it ("Cannot uninstall cryptography 41.0.7"): on 23 Oct the 13:52 recorder fire hit that after
# requirements.txt asked for cryptography>=42, stopped here, and no part of the system noticed. The first try is the
# plain install (seconds when everything is present); only when it fails is it repeated over the system copies.
install() {
    # shellcheck disable=SC2086  # requirements holds several words on purpose
    "$1" -m pip install -q --root-user-action=ignore --use-pep517 $2 $requirements
}
for py in $interpreters; do
    install "$py" "" || {
        echo "routine setup: plain install failed in $py, repeating over the system packages" >&2
        install "$py" "--ignore-installed" || {
            echo "routine setup FAILED: installing into $py" >&2
            exit 1
        }
    }
done
for name in python3 python; do
    command -v "$name" >/dev/null 2>&1 || continue
    "$name" -c "import $modules" || {
        echo "routine setup FAILED: '$name' ($(command -v "$name")) cannot import $modules" >&2
        exit 1
    }
done
git config core.hooksPath .githooks
echo "routine setup ok:$interpreters ($(( $(date +%s) - started ))s, $(TZ=Asia/Kolkata date +%H:%M:%S) IST)"
