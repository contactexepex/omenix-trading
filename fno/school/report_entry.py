"""The school's report inputs for the forecast lab's composition root (story MS-P1j; orchestrator's ruling, 22 Oct
2026): the lab passes this builder to g's guard, so g's reports never import the fleet. It imports nothing at load
time, as the guard does, so nothing of the school can fail the lab's own import; the guard runs it inside its
isolation, and only with `school.reports` on."""


def school_report_inputs(config: dict):
    """(08:50 inputs, 20:05 inputs): the previous slot's indicative plan, and the session's sealed record and counts."""
    from .wiring import build_report_inputs

    return build_report_inputs(config)
