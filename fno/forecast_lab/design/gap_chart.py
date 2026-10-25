"""Chart 2: how far off. The gap (actual close minus the forecast middle) in points, one dot per session joined by
a thin line, a zero line, and dashed step lines on each side for the edges of "most likely" and "almost
certainly" (they vary by day). Above zero = closed higher than forecast. Dot colour = the result; every miss and
the last day written with its signed gap, so a red dot says how big and which way."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .formats import RED, signed
from .lines_chart import label_every
from .values import Day


@dataclass(frozen=True)
class GapLayout:
    width: int
    grid_step: int
    plot_height: int = 220
    top: int = 16
    axis_width: int = 54
    bottom: int = 34


class GapChart:
    def __init__(self, days: list[Day], layout: GapLayout, date_every: int = 1):
        self.days, self.lay, self.date_every = days, layout, date_every
        values = [v for d in days for v in (d.lo90 - d.mid, d.hi90 - d.mid, d.gap)]
        step = layout.grid_step
        self.low = math.floor((min(values) - step * 0.5) / step) * step
        self.high = math.ceil((max(values) + step * 0.5) / step) * step
        self.slot = (layout.width - layout.axis_width - 20) / len(days)
        self.height = layout.top + layout.plot_height + layout.bottom
        self.label_every = label_every(layout.plot_height * step / (self.high - self.low))

    def y(self, value: float) -> float:
        return self.lay.top + self.lay.plot_height * (self.high - value) / (self.high - self.low)

    def x(self, i: int) -> float:
        return self.lay.axis_width + 10 + self.slot * (i + 0.5)

    def _grid(self) -> list[str]:
        out, right = [], self.lay.width - 10
        for k, v in enumerate(range(int(self.low), int(self.high) + 1, self.lay.grid_step)):
            y, cls = self.y(v), "zero" if v == 0 else "grid"
            out.append(f'<line class="{cls}" x1="{self.lay.axis_width}" x2="{right}" y1="{y:.1f}" y2="{y:.1f}"/>')
            if k % self.label_every == 0 or v == 0:
                out.append(
                    f'<text class="ax" x="{self.lay.axis_width - 6}" y="{y + 3.5:.1f}">{signed(v) if v else "0"}</text>'
                )
        return out

    def _step(self, key: str, cls: str) -> str:
        pts = []
        for i, d in enumerate(self.days):
            y = self.y(getattr(d, key) - d.mid)
            pts.append(f"{self.x(i) - self.slot / 2:.1f},{y:.1f} {self.x(i) + self.slot / 2:.1f},{y:.1f}")
        return f'<polyline class="edge {cls}" points="{" ".join(pts)}"/>'

    def _dots(self) -> list[str]:
        gaps = " ".join(f"{self.x(i):.1f},{self.y(d.gap):.1f}" for i, d in enumerate(self.days))
        parts, placed, n = [f'<polyline class="gapline" points="{gaps}"/>'], [], len(self.days)
        for i, d in enumerate(self.days):
            x, yg = self.x(i), self.y(d.gap)
            tip = f"{d.date_long}: closed {signed(d.gap)} points from the forecast middle ({d.result})"
            parts.append(
                f'<g><title>{tip}</title><circle class="pc {d.result}" cx="{x:.1f}" cy="{yg:.1f}" r="4.5"/></g>'
            )
            if d.result == RED or i == n - 1:
                y = yg - 9 if d.gap >= 0 else yg + 16
                for px, py in placed:
                    if abs(px - x) < 40 and abs(py - y) < 12:
                        y = py - 13 if d.gap >= 0 else py + 13
                placed.append((x, y))
                parts.append(
                    f'<text class="gv {d.result}" x="{min(x, self.lay.width - 34):.1f}" y="{y:.1f}">'
                    f"{signed(d.gap)}</text>"
                )
        return parts

    def _dates(self) -> list[str]:
        base, n = self.lay.top + self.lay.plot_height, len(self.days)
        parts = []
        for i, d in enumerate(self.days):
            if (n - 1 - i) % self.date_every == 0:
                last = i == n - 1
                parts.append(
                    f'<text class="day" style="text-anchor:{"end" if last else "middle"}" '
                    f'x="{self.x(i) + (6 if last else 0):.1f}" y="{base + 16}">{d.date}</text>'
                )
        return parts

    def svg(self, aria: str) -> str:
        edges = [
            self._step("hi90", "r90"),
            self._step("lo90", "r90"),
            self._step("hi50", "r50"),
            self._step("lo50", "r50"),
        ]
        body = self._grid() + edges + self._dots() + self._dates()
        return (
            f'<svg class="gap" viewBox="0 0 {self.lay.width} {self.height}" role="img" aria-label="{aria}">'
            + "".join(body)
            + "</svg>"
        )
