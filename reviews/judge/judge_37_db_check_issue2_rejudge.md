# Judge 37: omenix-dashboard issue #2 re-judged (round 2), scheduled database check

**Verdict: PASS for the builder's work, with one owner decision.**
- **Judge 36's findings:** both should-fix findings and both minors are ACCEPTED as fixed.
- **The residual risk the builder states:** a second copy of the F&O Slack bot token in a public repository's Actions
  secrets. This is a credential-placement choice, **not mine or the builder's to accept: it needs the owner.** A
  smaller-blast-radius option is recommended below.

**What I judged**
- **Repository:** `exepex/omenix-dashboard` at b1f3abf (merge of 11849f9).
- **Answer:** `reviews/claude/response_14_db_check_issue2.md`.
- **Repository visibility:** public. The orchestrator confirmed this through the GitHub API; I could not see it
  myself.

## Checks run by the judge

### Platform CI locally (fresh postgres:16, a throwaway container removed afterwards): `ci.sh` exit 0, step 7

```
ok: clean server: OK, nothing raised or sent
ok: 640 kB of large objects in postgres: alert raised in public with counts only; details went to the Slack sender
ok: persistent statement_timeout = 0 on dashboard_app: alert raised in public with counts only; details went to the Slack sender
ok: a CREATE grant on schema stock (Slack refusing): alert raised in public with counts only; ...
ok: when Slack refuses, the public alert says the details were not delivered
ok: an unreachable server (UNKNOWN): alert raised in public with counts only; ...
ok: no secret and not enabled: a notice only
ok: a lost secret while DB_CHECK_ENABLED=true: alert raised in public with counts only; ...
ok: the weekly heartbeat names the last successful check
ok: the Slack token travels on stdin, never on curl's command line
ok: keep-alive commits after 50 idle days / does nothing when the repository is active
X1 platform tests: all passed
```

### My own run of `monitor/run.sh`

I used a stub `db_check.sh` whose report names `dashboard_app`, `statement_timeout`, database `postgres` and a byte
count. The Slack address was unreachable, `gh` was faked, and the token was a fake `xoxb-…`.

| Case | Public log | Issue body (`gh` call) | Exit |
|---|---|---|---|
| ALERT | `Database check ALERT: 2 finding(s), unknown parts: 0, checked …`, plus "details sent privately …: no (curl …)" | the same summary, the run link, and "Details are never posted here" | **1** |
| Lost secret, `DB_CHECK_ENABLED=true` | `Database check UNKNOWN: 0 finding(s), unknown parts: 1 …` | an alert issue opened | **2** |
| Lost secret, not enabled | a notice only | none | 0 |

`grep` for `dashboard_app|statement_timeout|postgres|999999|large object|xoxb` in the public output and in the `gh`
calls: **0 hits in both.**

### Code read

- **`notify_slack.sh`:** the channel is fixed to `C0C89E8QCCD` (#fno-desk). The token is sent as a header read from
  stdin (`-H @-`), and Slack's answer is checked (`.ok`).
- **The workflow:** no new trigger and no new permission (`contents: read`, `issues: write`).
- **`keepalive.yml`:** a separate workflow with `contents: write`, so `db-check` never holds write access.

## Judge 36's findings: decisions

| # | Finding | Fix | Judge's evidence | Decision |
|---|---|---|---|---|
| 1 | Should fix: a missing secret passed green | The repository variable `DB_CHECK_ENABLED=true` (set by `setup_monitor.sh`); a missing secret then gives UNKNOWN, exit 2, with the alert | My run above; CI test | ACCEPTED |
| 2 | Should fix: the report was public | Only the one-line summary in the log and the issue; details only to Slack #fno-desk | My run above (0 sensitive hits); CI tests for every plant | ACCEPTED |
| 3 | Minor: the 60-day pause | A weekly heartbeat to #fno-desk, and a monthly keep-alive commit after 45 idle days | CI tests. Whether a bot commit counts as activity is untested (the builder says so). The heartbeat makes a stop visible either way. | ACCEPTED |
| 4 | Minor: "no data access" wording | The README now says: no row data; catalog metadata (names, row counts) visible | Read | ACCEPTED |

## The residual risk: owner decision

**What changes.** `FNO_SLACK_BOT_TOKEN`, today held by exepex/trading, gets a second copy in the Actions secrets of
**public** exepex/omenix-dashboard.
- Anyone with write access can add a workflow that exfiltrates it. GitHub masks secrets in logs, but an encoded copy
  defeats the mask.
- **Who has write access:** the owner, and the Claude sessions that push to `main` directly. An agent misled by
  injected text is the realistic path, not an outside attacker.
- **What a leaked token allows:** whatever the bot's scopes allow, at least posting as the F&O bot. If the bot can
  also read #fno-desk's history (I did not check its scopes), that history would be readable too.

**My view (reasoning only).**
- The risk is real, but bounded: no money, no broker access, and no market-moving power. The research-only hard
  lines are not crossed.
- It is still the owner's credential and the owner's call.
- **A strictly smaller option exists:** a Slack **incoming webhook** bound to #fno-desk. It can only post to that one
  channel and can read nothing, so it is worth less if leaked than the bot token. It would replace
  `FNO_SLACK_BOT_TOKEN` in this repository with a single-purpose secret.
- **The alternative the builder names:** make the repository private, which removes both the exposure and the need.

**Recommendation for the owner:** either the webhook, or a private repository. If the owner accepts the bot token as
built, record it in `docs/DESK_DECISIONS.md` like the X1 exceptions.

## Addendum: the owner's decision applied (omenix-dashboard b6b3e7a)

**ACCEPTED.** Issue #2's owner decision is closed.
- **The owner chose the webhook.** It is recorded in `docs/DESK_DECISIONS.md` (13 Oct 2026, owner: "webhook").
- **`FNO_SLACK_BOT_TOKEN` is gone from the repository.** It is no longer in the workflow, the monitor or the owner
  script. The only remaining mention is the checklist's instruction to delete the old secret. The web app's own
  `SLACK_BOT_TOKEN` test fakes are unrelated.

**Checks:**
- **The full platform CI** (`platform/tests/ci.sh`) on a disposable Postgres 16 (never Azure): **all passed**,
  including the 4 new webhook tests.
- **`owner_scripts_test.sh`:** all passed.

**My own probes of `notify_slack.sh`, with a fake curl that logs its arguments and stdin and writes the config back on
stderr:**

| Webhook secret | Result |
|---|---|
| A valid `https://hooks.slack.com/services/…`, Slack answers `ok` | exit 0. The URL appears only in curl's stdin config, never on its command line. Curl's stderr, which quoted the URL, is not shown. |
| The same, Slack answers an error body that contains a URL | exit 1, "Slack refused the message: invalid_tokenhttpshooksslackcomservices". The upper-case secret part is stripped. See the note below. |
| The same, curl fails (exit 6) | "Slack could not be reached (curl exit 6)". Nothing else is printed. |
| A config injection: `…SECRETX"` followed by a new line and `output = "/tmp/pwn"` | **refused** ("characters a URL cannot hold"). Curl is never called. |
| A trailing backslash | **refused** |
| `https://hooks.slack.com.evil.com/…` or `http://hooks.slack.com/…` | **refused** ("not a Slack incoming webhook") |
| A path holding "@" and another host name after `/services/` | accepted, which is safe: the "@" is in the path, so the host stays `hooks.slack.com` |

**Note (reasoning only, not a finding):**
- A refusal prints up to 40 lower-case letters and underscores from Slack's answer. If Slack ever echoed the webhook
  URL, the lower-case letters of its secret part could appear in the public log.
- Slack's webhook errors are fixed codes (`invalid_payload`, `no_service`, …), so I see no realistic path for that.
- Printing the answer only when it matches `^[a-z_]{1,40}$`, and otherwise a fixed "unexpected answer", would remove
  even that path.

**Residual risk, as the README now states:** a leaked webhook can post to #fno-desk and read nothing. That is
strictly less than the bot token's exposure.
