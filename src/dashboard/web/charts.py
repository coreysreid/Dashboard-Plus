"""Draw small charts as SVG on the server: labelled bars and dated dots, each with a title and description, no scripts."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

from markupsafe import Markup, escape

# The drawing is sized for a phone: a 340-unit-wide picture stays readable when shrunk to a 320px screen,
# and the page caps how wide it grows (base.html, .chart svg). Nothing is animated.
WIDTH = 340
FONT = 14
SMALL = 12
BAR_ROW = 46  # height of one bar: its name above, the bar and its value below
MAX_LABEL = 38  # characters of a name drawn on a bar; the full name is in the link's title and the table


@dataclass
class Bar:
    """One bar: what it is, its value and the words printed beside it, and the row of the table it matches."""
    label: str
    value: float
    text: str
    href: str


@dataclass
class Dot:
    """One reading: its date, value and words, and the row of the table it matches."""
    day: date
    value: float
    text: str
    href: str


def number_text(value: float) -> str:
    """12.5 not 12.50, 3 not 3.0."""
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-0") else "0"


def axis_steps(value: float, most: int = 5) -> tuple[float, float]:
    """The end of an axis that starts at zero and a round step between its labels: 21.3 -> (25, 5), 4.1 -> (5, 1)."""
    if value <= 0:
        return 1.0, 1.0
    power = 10 ** math.floor(math.log10(value / most))
    for size in (1, 2, 2.5, 5, 10):
        step = size * power
        if math.ceil(value / step - 1e-9) <= most:
            return math.ceil(value / step - 1e-9) * step, step
    return 10 * power * most, 10 * power


def _short(text: str) -> str:
    return text if len(text) <= MAX_LABEL else text[:MAX_LABEL - 1].rstrip() + "…"


def _svg(chart_id: str, height: float, title: str, description: str, body: list[str]) -> Markup:
    """The picture: a group named by its title and described by its description, for screen readers."""
    return Markup(
        f'<svg class="chart-svg" viewBox="0 0 {WIDTH} {height:.0f}" width="{WIDTH}" height="{height:.0f}" '
        f'role="group" aria-labelledby="{chart_id}-title" aria-describedby="{chart_id}-desc" '
        f'xmlns="http://www.w3.org/2000/svg" font-size="{FONT}">'
        f'<title id="{chart_id}-title">{escape(title)}</title>'
        f'<desc id="{chart_id}-desc">{escape(description)}</desc>' + "".join(body) + "</svg>")


def bar_chart(chart_id: str, title: str, description: str, bars: list[Bar], axis_label: str, unit: str) -> Markup:
    """Horizontal bars from zero, each named above and with its value printed beside it; the axis says its unit."""
    top, _ = axis_steps(max((b.value for b in bars), default=0), most=2)
    left, right = 4, 72  # room on the right for the longest value, like "1250 L"
    span = WIDTH - left - right
    body = []
    for i, bar in enumerate(bars):
        y = i * BAR_ROW + 4
        length = max(2.0, span * bar.value / top) if bar.value > 0 else 0
        body.append(
            f'<a href="{escape(bar.href)}" class="chart-mark" aria-label="{escape(bar.label)}: {escape(bar.text)}">'
            f'<title>{escape(bar.label)}: {escape(bar.text)}</title>'
            f'<text x="{left}" y="{y + FONT:.0f}" class="chart-label">{escape(_short(bar.label))}</text>'
            f'<rect class="chart-bar" x="{left}" y="{y + FONT + 6:.0f}" width="{length:.1f}" height="16" rx="2"/>'
            f'<text x="{left + length + 6:.1f}" y="{y + FONT + 19:.0f}" class="chart-value">{escape(bar.text)}</text>'
            f'</a>')
    axis = len(bars) * BAR_ROW + 8
    body.append(f'<line class="chart-axis" x1="{left}" x2="{left + span}" y1="{axis}" y2="{axis}"/>')
    for value, anchor, x in ((0, "start", left), (top / 2, "middle", left + span / 2), (top, "end", left + span)):
        body.append(f'<line class="chart-axis" x1="{x:.1f}" x2="{x:.1f}" y1="{axis}" y2="{axis + 5}"/>'
                    f'<text x="{x:.1f}" y="{axis + 5 + SMALL + 2}" font-size="{SMALL}" text-anchor="{anchor}">'
                    f'{number_text(value)}{escape(" " + unit if unit else "")}</text>')
    body.append(f'<text x="{left + span / 2:.1f}" y="{axis + 2 * SMALL + 14}" font-size="{SMALL}" '
                f'text-anchor="middle" class="chart-axis-title">{escape(axis_label)}</text>')
    return _svg(chart_id, axis + 2 * SMALL + 22, title, description, body)


def fitted_steps(low: float, high: float, most: int = 5) -> tuple[float, float, float]:
    """A value axis around the readings only, for a chart that asks for it (decision 0119): a round start below the
    lowest reading, a round end above the highest and the step between labels. 4.4 to 4.8 -> (4.3, 4.8, 0.1)."""
    if high <= low:
        low, high = low - max(abs(low) * 0.1, 0.5), high + max(abs(high) * 0.1, 0.5)
    span = high - low
    power = 10 ** math.floor(math.log10(span / most))
    for size in (1, 2, 2.5, 5, 10):
        step = size * power
        bottom = math.floor(low / step + 1e-9) * step
        if bottom >= low - 1e-9:
            bottom -= step  # the lowest dot sits above the axis, never on it
        top = math.ceil(high / step - 1e-9) * step
        if round((top - bottom) / step) <= most + 1:
            return round(max(bottom, 0.0) if low >= 0 else bottom, 9), round(top, 9), step
    return low, high, span


def dot_chart(chart_id: str, title: str, description: str, dots: list[Dot], axis_label: str, unit: str,
              show_date, line: bool = False, gap_days: int | None = None, fitted: bool = False) -> Markup:
    """Dots by date from the first reading to the last; the value axis starts at zero.
    Readings on the same day sit side by side so each one can be seen and chosen. Only when the declaration allows
    (decision 0119): a thin line between readings next to each other in time, broken where they are more than
    `gap_days` apart, and a fitted scale whose start is written on the chart."""
    left, right, top_pad, bottom = 46, 18, 26, 52
    height = 240
    plot_w, plot_h = WIDTH - left - right, height - top_pad - bottom
    top, step = axis_steps(max((d.value for d in dots), default=0))
    floor = 0.0
    if fitted and dots:
        floor, top, step = fitted_steps(min(d.value for d in dots), max(d.value for d in dots))
    first = min((d.day for d in dots), default=date.today())
    last = max((d.day for d in dots), default=first)
    days = max(1, (last - first).days)

    def x_of(day: date) -> float:
        inset = 10  # keep the first and last dots clear of the value labels and the edge
        return left + plot_w / 2 if last == first else left + inset + (plot_w - 2 * inset) * (day - first).days / days

    def y_of(value: float) -> float:
        return top_pad + plot_h * (1 - (value - floor) / (top - floor))

    body = []
    for i in range(round((top - floor) / step) + 1):  # value axis: a labelled line at each round step to the top
        value = floor + step * i
        y = y_of(value)
        body.append(f'<line class="chart-grid" x1="{left}" x2="{left + plot_w}" y1="{y:.1f}" y2="{y:.1f}"/>'
                    f'<text x="{left - 6}" y="{y + 4:.1f}" font-size="{SMALL}" text-anchor="end">'
                    f'{number_text(value)}</text>')
    body.append(f'<text x="{left - 6}" y="{SMALL + 2}" font-size="{SMALL}" text-anchor="end" '
                f'class="chart-axis-title">{escape(unit)}</text>')
    if floor:  # a fitted scale says plainly that it does not start at zero
        body.append(f'<text x="{left + plot_w}" y="{SMALL + 2}" font-size="{SMALL}" text-anchor="end" '
                    f'class="chart-axis-title chart-fitted">Scale starts at {number_text(floor)}'
                    f'{escape(" " + unit if unit else "")}, not 0</text>')
    base = top_pad + plot_h
    body.append(f'<line class="chart-axis" x1="{left}" x2="{left + plot_w}" y1="{base}" y2="{base}"/>')
    ticks = [first] if last == first else [first, last]
    for day in ticks:
        anchor = "middle" if last == first else ("start" if day == first else "end")
        x = x_of(day)
        body.append(f'<line class="chart-axis" x1="{x:.1f}" x2="{x:.1f}" y1="{base}" y2="{base + 5}"/>'
                    f'<text x="{x:.1f}" y="{base + 5 + SMALL + 2}" font-size="{SMALL}" text-anchor="{anchor}">'
                    f'{escape(show_date(day))}</text>')
    body.append(f'<text x="{left + plot_w / 2:.1f}" y="{base + 2 * SMALL + 16}" font-size="{SMALL}" '
                f'text-anchor="middle" class="chart-axis-title">{escape(axis_label)}</text>')
    same_day: dict[date, int] = {}
    for dot in dots:
        same_day[dot.day] = same_day.get(dot.day, 0) + 1
    placed: dict[date, int] = {}
    spots = []
    for dot in dots:
        k, n = placed.get(dot.day, 0), same_day[dot.day]
        placed[dot.day] = k + 1
        centre, spread = x_of(dot.day), (n - 1) / 2 * 11
        centre = min(left + plot_w - spread, max(left + spread, centre))  # the whole day's group stays inside
        x = centre + (k - (n - 1) / 2) * 11
        spots.append((dot.day, x, y_of(dot.value)))
        body.append(f'<a href="{escape(dot.href)}" class="chart-mark" aria-label="{escape(dot.text)}">'
                    f'<title>{escape(dot.text)}</title>'
                    f'<circle class="chart-dot" cx="{x:.1f}" cy="{y_of(dot.value):.1f}" r="5.5"/></a>')
    if line and len(spots) > 1:  # drawn under the dots; a long gap between readings breaks it
        ordered = sorted(spots, key=lambda spot: (spot[0], spot[1]))
        runs, run = [], [ordered[0]]
        for before, after in zip(ordered, ordered[1:]):
            if gap_days is not None and (after[0] - before[0]).days > gap_days:
                runs.append(run)
                run = []
            run.append(after)
        runs.append(run)
        lines = ['<polyline class="chart-line" aria-hidden="true" fill="none" points="'
                 + " ".join(f"{x:.1f},{y:.1f}" for _, x, y in r) + '"/>' for r in runs if len(r) > 1]
        first_mark = next(i for i, part in enumerate(body) if part.startswith("<a "))
        body[first_mark:first_mark] = lines
    return _svg(chart_id, height, title, description, body)
