"""Chart rendering for the market brief.

The dashboard answers one question at a glance — do the timeframes agree? — so
the alignment matrix leads and the price panels support it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

from .trend import Alignment, Direction, InstrumentTrend  # noqa: E402


@dataclass(frozen=True)
class Palette:
    bg: str
    panel: str
    ink: str
    ink_soft: str
    ink_faint: str
    line: str
    up: str
    down: str
    flat: str
    accent: str


LIGHT = Palette(
    bg="#FFFFFF",
    panel="#F4F5F8",
    ink="#191C22",
    ink_soft="#565C68",
    ink_faint="#878E9C",
    line="#D8DCE4",
    up="#146B47",
    down="#A93E27",
    flat="#878E9C",
    accent="#2F4B7C",
)

DARK = Palette(
    bg="#101318",
    panel="#1F242C",
    ink="#E9EBEF",
    ink_soft="#A0A8B5",
    ink_faint="#6B7382",
    line="#2A303A",
    up="#4FBE8B",
    down="#E5806A",
    flat="#6B7382",
    accent="#8FAFDD",
)

THEMES = {"light": LIGHT, "dark": DARK}

_ALIGNMENT_COLOR = {
    Alignment.ALIGNED_UP: "up",
    Alignment.ALIGNED_DOWN: "down",
    Alignment.REBOUND: "accent",
    Alignment.PULLBACK: "accent",
    Alignment.MIXED: "ink_faint",
    Alignment.FLAT: "ink_faint",
}


def _direction_color(direction: Direction, palette: Palette) -> str:
    return {
        Direction.UP: palette.up,
        Direction.DOWN: palette.down,
        Direction.FLAT: palette.flat,
    }[direction]


def _draw_matrix(ax, trends: list[InstrumentTrend], tf_keys: list[str],
                 tf_labels: dict[str, str], palette: Palette) -> None:
    """Instruments down the side, timeframes across, verdict on the right."""
    n_rows = len(trends)
    n_cols = len(tf_keys)

    label_w = 2.3
    cell_w = 1.55
    verdict_w = 3.5
    total_w = label_w + n_cols * cell_w + verdict_w

    ax.set_xlim(0, total_w)
    # Rows sit between 0.5 and n_rows - 0.5, the header at n_rows + 0.45; the
    # limits hug that so the axes does not leave a dead band under the table.
    ax.set_ylim(0.06, n_rows + 0.85)
    ax.axis("off")

    header_y = n_rows + 0.45

    for col, key in enumerate(tf_keys):
        x = label_w + col * cell_w + cell_w / 2
        ax.text(x, header_y, tf_labels.get(key, key).upper(), ha="center",
                va="center", fontsize=8.5, color=palette.ink_faint,
                family="monospace", weight="bold")

    ax.text(label_w + n_cols * cell_w + verdict_w / 2, header_y, "SAMSTÄMMIGHET",
            ha="center", va="center", fontsize=8.5, color=palette.ink_faint,
            family="monospace", weight="bold")

    ax.plot([0, total_w], [n_rows + 0.12, n_rows + 0.12],
            color=palette.line, linewidth=1.0)

    for row, trend in enumerate(trends):
        y = n_rows - row - 0.5

        ax.text(0.05, y, trend.label, ha="left", va="center",
                fontsize=11, color=palette.ink, weight="bold")

        for col, key in enumerate(tf_keys):
            x0 = label_w + col * cell_w
            tf = trend.timeframes.get(key)

            if tf is None:
                ax.text(x0 + cell_w / 2, y, "–", ha="center", va="center",
                        fontsize=11, color=palette.ink_faint)
                continue

            color = _direction_color(tf.direction, palette)
            ax.add_patch(Rectangle(
                (x0 + 0.06, y - 0.38), cell_w - 0.12, 0.76,
                facecolor=color, alpha=0.15, edgecolor=color,
                linewidth=0.8, zorder=1,
            ))

            ax.text(x0 + cell_w / 2, y + 0.09,
                    f"{tf.direction.arrow} {tf.bars_summary}",
                    ha="center", va="center", fontsize=9.5, color=color,
                    weight="bold", family="monospace", zorder=2)

            # Strength read-out: how far past the noise gate the move reached.
            seg_w = 0.19
            start = x0 + cell_w / 2 - (3 * seg_w + 2 * 0.05) / 2
            for i in range(3):
                filled = i < tf.strength
                ax.add_patch(Rectangle(
                    (start + i * (seg_w + 0.05), y - 0.26), seg_w, 0.07,
                    facecolor=color if filled else palette.line,
                    alpha=1.0 if filled else 0.9,
                    edgecolor="none", zorder=2,
                ))

        vx = label_w + n_cols * cell_w
        v_color = getattr(palette, _ALIGNMENT_COLOR[trend.alignment])
        ax.add_patch(Rectangle(
            (vx + 0.12, y - 0.38), verdict_w - 0.24, 0.76,
            facecolor=v_color, alpha=0.10, edgecolor=v_color,
            linewidth=0.8, zorder=1,
        ))
        ax.text(vx + verdict_w / 2, y, trend.alignment.label, ha="center",
                va="center", fontsize=9.5, color=v_color, weight="bold",
                zorder=2)


def _draw_panel(ax, tf, series, palette: Palette) -> None:
    color = _direction_color(tf.direction, palette)
    tail = series.tail(80)
    xs = range(len(tail))
    values = tail.to_numpy(dtype=float)

    ax.set_facecolor(palette.panel)
    ax.plot(xs, values, color=color, linewidth=1.7, zorder=3)
    ax.fill_between(xs, values, values.min(), color=color, alpha=0.10, zorder=2)
    ax.scatter([len(tail) - 1], [values[-1]], s=22, color=color,
               zorder=4, edgecolor=palette.bg, linewidth=1.0)

    ax.set_title(f"{tf.label}   {tf.direction.arrow} {tf.direction.label}   {tf.bars_summary}",
                 fontsize=9.5, color=color, weight="bold", pad=7, loc="left")

    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([])
    ax.tick_params(axis="y", labelsize=7.5, colors=palette.ink_faint, length=0)
    ax.grid(axis="y", color=palette.line, linewidth=0.6, alpha=0.7, zorder=1)
    ax.set_axisbelow(True)


def render_dashboard(
    trends: list[InstrumentTrend],
    tf_keys: list[str],
    tf_labels: dict[str, str],
    focus: InstrumentTrend,
    focus_series: dict[str, "object"],
    path: str | Path,
    theme: str = "light",
    subtitle: str = "",
) -> Path:
    """One PNG: the alignment matrix, then price panels for the focus name."""
    palette = THEMES[theme]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    n_rows = len(trends)
    matrix_h = 0.52 * n_rows + 0.9
    fig_h = matrix_h + 3.0

    fig = plt.figure(figsize=(11.5, fig_h), dpi=160, facecolor=palette.bg)
    grid = fig.add_gridspec(
        2, len(tf_keys),
        height_ratios=[matrix_h, 2.6],
        hspace=0.30, wspace=0.22,
        left=0.035, right=0.975, top=0.90, bottom=0.07,
    )

    fig.text(0.035, 0.965, "Trendläge per tidsintervall", fontsize=15,
             color=palette.ink, weight="bold", ha="left", va="top")
    if subtitle:
        fig.text(0.035, 0.925, subtitle, fontsize=9.5,
                 color=palette.ink_faint, ha="left", va="top")

    ax_matrix = fig.add_subplot(grid[0, :])
    ax_matrix.set_facecolor(palette.bg)
    _draw_matrix(ax_matrix, trends, tf_keys, tf_labels, palette)

    for col, key in enumerate(tf_keys):
        ax = fig.add_subplot(grid[1, col])
        tf = focus.timeframes.get(key)
        series = focus_series.get(key)
        if tf is None or series is None:
            ax.axis("off")
            continue
        _draw_panel(ax, tf, series, palette)

    fig.text(0.035, 0.028, f"{focus.label} · {focus.alignment.note}",
             fontsize=9, color=palette.ink_soft, ha="left", va="bottom")

    fig.savefig(path, facecolor=palette.bg, bbox_inches="tight", pad_inches=0.3)
    plt.close(fig)
    return path
