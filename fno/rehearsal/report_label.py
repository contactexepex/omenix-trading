"""The forecast lab's editions in a rehearsal start with the label (story REH1), chosen by `build_forecast_poster`
(the composer is the lab's own `build_composer`, agreed with its owner)."""

from __future__ import annotations

import os
from collections.abc import Mapping

from ..forecast_lab.delivery import ReportPoster
from .mode import labelled, rehearsal


class LabelledReportPoster(ReportPoster):
    def __init__(self, inner: ReportPoster, label: str):
        self.inner, self.label = inner, label

    def post(self, text: str, attachments):
        return self.inner.post(labelled(self.label, text), attachments)


def rehearsed_report_poster(poster: ReportPoster, env: Mapping[str, str] = os.environ) -> ReportPoster:
    mode = rehearsal(env)
    return poster if mode is None else LabelledReportPoster(poster, mode.label)
