"""Story REH1: rehearsal mode. A recorded day replayed through every real step, safe by construction: one replay
clock, inputs only from the day's receipted data, writes only under Drive's `dryrun/<run_id>/` and a
`rehearsal/<day>-<run_id>` branch, every Slack post labelled. Only the composition roots and this package know the
mode (a test pins it)."""
