from __future__ import annotations

from typing import Any, cast

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.backend_bases import RendererBase
from matplotlib.figure import Figure
from matplotlib.legend import Legend
from matplotlib.ticker import ScalarFormatter


def init_figure_matplotlib() -> tuple[Figure, Axes]:
    """Create a Matplotlib figure and axes with predefined settings."""
    # fig, ax = plt.subplots(figsize=(6.4, 4.8))
    fig, ax = plt.subplots()
    ax.xaxis.set_major_formatter(ScalarFormatter(useMathText=True))
    ax.yaxis.set_major_formatter(ScalarFormatter(useMathText=True))
    ax.ticklabel_format(style="sci", axis="both", scilimits=(0, 0))
    # ax.grid(ls=":")
    ax.grid(True)
    # fig.subplots_adjust(left=0.17, bottom=0.155, right=0.95, top=0.9)
    fig.subplots_adjust(left=0.17, bottom=0.2, right=0.95, top=0.9)
    return fig, ax


def has_legend_items(ax: Axes) -> bool:
    """Check whether an Axes has any artists that can appear in a legend.

    This helper is intended to be called before ``ax.legend()`` to avoid the
    warning *“No artists with labels found to put in legend.”* that matplotlib
    emits when there are no labeled artists.

    Args:
        ax: The ``matplotlib.axes.Axes`` (or subclass) to inspect.

    Returns:
        True if at least one artist on ``ax`` has a non‑empty label that does
        not start with an underscore (i.e., it would be included in a legend);
        otherwise False.

    """
    _, labels = ax.get_legend_handles_labels()
    return any(lab and not lab.startswith('_') for lab in labels)


def optimize_plot_limits(  # noqa: PLR0912, C901
    x_data: list[list[float]],
    y_data: list[list[float]],
    x_margin: float = 0.0,
    y_margin: float = 0.0,
    x_scale: str = 'linear',
    y_scale: str = 'linear',
) -> tuple[
    tuple[float, float],
    tuple[float, float],
    list[float],
    list[float],
    str,
    str,
]:
    """Calculate nice axis limits and tick positions for a pair of data series.

    Args:
        x_data: List of X‑axis series.
        y_data: List of Y‑axis series.
        x_margin: Fraction of X‑axis span to use as margin.
        y_margin: Fraction of Y‑axis span to use as margin.
        x_scale: Desired scaling for the X‑axis; either 'linear' or 'log'.
        y_scale: Desired scaling for the Y‑axis; either 'linear' or 'log'.

    Returns:
        Tuple containing X limits, Y limits, X ticks, Y ticks, and the scales used.

    """
    # 1️⃣ Data cleansing
    # Iterate over each pair of x_data and y_data, extracting only those where both are valid numbers.
    valid_x: list[float] = []
    valid_y: list[float] = []
    # Iterate over Sequence[list] using zip.
    for series_x, series_y in zip(x_data, y_data, strict=False):
        # Iterate over each series (list) using zip.
        # This avoids TypeError when series_x is a float.
        try:
            for vx, vy in zip(series_x, series_y, strict=False):  # noqa: SIM102
                if vx is not None and vy is not None:  # noqa: SIM102
                    # Number and NaN checks
                    if not (np.isnan(vx) or np.isnan(vy)):
                        valid_x.append(float(vx))
                        valid_y.append(float(vy))
        except TypeError:
            # Fallback in case series_x itself is a single scalar value.
            vx = cast(float, series_x)
            vy = cast(float, series_y)
            if vx is not None and vy is not None:  # noqa: SIM102
                if not (np.isnan(vx) or np.isnan(vy)):
                    valid_x.append(float(vx))
                    valid_y.append(float(vy))
    final_results: list[tuple[tuple[float, float], list[float]]] = []
    # 2️⃣ Compute X and Y axis limits
    for data, margin, scale in [(valid_x, x_margin, x_scale), (valid_y, y_margin, y_scale)]:
        if not data:
            final_results.append(((0.0, 1.0), [0.0, 0.5, 1.0]))
            continue
        # log scale
        if scale == 'log':
            # Logarithmic scale: only positive values are considered.
            pos_data = [v for v in data if v > 0]
            if not pos_data:
                final_results.append(((0.1, 10.0), [0.1, 1.0, 10.0]))
                continue
            d_min, d_max = min(pos_data), max(pos_data)
            l_log, u_log = np.log10(d_min), np.log10(d_max)
            log_span = u_log - l_log if u_log != l_log else 1.0
            # After applying margin, determine range as powers of 10.
            low_pow = int(np.floor(l_log - log_span * margin))
            high_pow = int(np.ceil(u_log + log_span * margin))
            l_limit, u_limit = 10.0**low_pow, 10.0**high_pow
            ticks = [float(10.0**i) for i in range(low_pow, high_pow + 1)]
            final_results.append(((l_limit, u_limit), ticks))
            continue

        # Linear scale: Nice Number Algorithm.
        FRAC_THRESHOLD_LOW = 1.5   # noqa: N806 # choose step = 1·10ⁿ when fraction < 1.5
        FRAC_THRESHOLD_MEDIUM = 3.0   # noqa: N806 # choose step = 2·10ⁿ when 1.5 ≤ fraction < 3.0
        FRAC_THRESHOLD_HIGH = 7.0   # noqa: N806 # choose step = 5·10ⁿ when 3.0 ≤ fraction < 7.0

        d_min, d_max = min(data), max(data)
        span = d_max - d_min if d_max != d_min else (abs(d_min) if d_min != 0 else 1.0)
        r_min = d_min - span * margin
        r_max = d_max + span * margin
        r_span = r_max - r_min if r_max != r_min else 1.0
        # Choose step size based on 1, 2, 5 series aiming for roughly 5 divisions.
        exp = np.floor(np.log10(r_span / 5))
        frac = (r_span / 5) / (10**exp)
        if frac < FRAC_THRESHOLD_LOW:
            step = 1.0 * (10**exp)
        elif frac < FRAC_THRESHOLD_MEDIUM:
            step = 2.0 * (10**exp)
        elif frac < FRAC_THRESHOLD_HIGH:
            step = 5.0 * (10**exp)
        else:
            step = 10.0 * (10**exp)
        # Round axis limits to multiples of the step.
        l_limit = np.floor(r_min / step) * step
        u_limit = np.ceil(r_max / step) * step
        ticks = []
        curr = l_limit
        while curr <= u_limit + (step * 0.1):
            ticks.append(float(round(curr, 12)))
            curr += step
        final_results.append(((float(l_limit), float(u_limit)), ticks))

    (xlim, xticks), (ylim, yticks) = final_results
    return xlim, ylim, xticks, yticks, x_scale, y_scale


def align_axes_range_and_ticks_plt(
    data_min: float,
    data_max: float,
    *,
    margin: float = 0.05,             # Data range padding (%). Can be 0.
    fix_origin_to_zero: bool = True,  # True → fix lower bound to 0
    size_inch: float = 6.0,           # Desired square figure size (inches)
    ax: Axes | None = None,
) -> dict[str, Any]:
    """Set equal X/Y limits and return automatically generated ticks.

    Args:
        data_min: Minimum value in the data set.
        data_max: Maximum value in the data set.
        margin: Fraction of the data range to use as padding.
        fix_origin_to_zero: If ``True`` the lower limit is forced to 0.
        size_inch: Desired side length of a square figure (in inches).
        ax: Target ``Axes`` object; if ``None`` the current axes
            (``plt.gca()``) is used.

    Returns:
        dict: ``{
            "xlim": (float, float),
            "ylim": (float, float),
            "xticks": np.ndarray,
            "yticks": np.ndarray,
            "figsize": (float, float)
        }``

    """
    # ------------------------------------------------------------
    # 0️⃣ Retrieve Axes (parameterized for easier testing)
    # ------------------------------------------------------------
    if ax is None:
        ax = plt.gca()
    # ------------------------------------------------------------
    # 1️⃣ Compute range with padding
    # ------------------------------------------------------------
    data_range = data_max - data_min
    padding = data_range * margin                # padding is 0 if margin is 0
    if fix_origin_to_zero:
        # Lower bound is forced to 0; padding added only to the upper side
        lower = 0.0
        upper = data_max + padding
    else:
        # Padding added to both sides (or none if margin is 0)
        lower = data_min - padding
        upper = data_max + padding
    # ------------------------------------------------------------
    # 2️⃣ Set limits on Axes (ticks remain automatic)
    # ------------------------------------------------------------
    # Disable the default 5% padding automatically added by Matplotlib.
    ax.margins(x=0, y=0)         # Only use the manually calculated padding.
    ax.set_xlim(lower, upper)
    ax.set_ylim(lower, upper)
    # ------------------------------------------------------------
    # 3️⃣ Make Figure square (override size)
    # ------------------------------------------------------------
    fig = plt.gcf()
    fig.set_size_inches(size_inch, size_inch)
    # ------------------------------------------------------------
    # 4️⃣ Let Matplotlib auto‑generate ticks
    # ------------------------------------------------------------
    # Changing limits alone does not update ticks, so trigger a draw once to let AutoLocator compute.
    fig.canvas.draw_idle()
    # (draw_idle is asynchronous; use draw() if immediate retrieval is needed).
    # fig.canvas.draw()   # Uncomment to force drawing if needed.
    # The default locator is AutoLocator (nice spacing), so retrieving here yields ticks like 0, 0.2, 0.4 …
    xticks = ax.get_xticks()
    yticks = ax.get_yticks()
    # ------------------------------------------------------------
    # 5️⃣ Return value (can be passed directly to plt.xlim(*res["xlim"]) etc.)
    # ------------------------------------------------------------
    return {
        "xlim": (lower, upper),
        "ylim": (lower, upper),
        "xticks": xticks,
        "yticks": yticks,
        "figsize": (size_inch, size_inch),
    }


def create_and_move_legend_to_right_if_needed(
    fig: Figure,
    ax: Axes,
    *,
    max_width_px: float | None = 300,
    max_items: int | None = 5,
    pad_factor: float = 0.05,
    ncol: int = 1,
    fontsize: int | str | None = None,
    title: str | None = None,
    frameon: bool = True,
) -> tuple[bool, dict[str, Any]]:
    """Move legend to the right if it exceeds width or item limits.

    Args:
        fig: Figure containing the Axes.
        ax: Axes whose legend is being inspected.
        max_width_px: Maximum allowed legend width in pixels (default 300).
            Set to None to disable the width check.
        max_items: Maximum allowed number of legend entries (default 5).
            Set to None to disable the item-count check.
        pad_factor: Fraction of the Figure width to add as padding between
            the Axes and the legend (default 0.05).
        ncol: Starting number of columns for the legend. The function will
            increase this value if needed to keep the legend height within
            the Axes height.
        fontsize: Font size to pass to ``ax.legend``.
        title: Legend title.
        frameon: Whether the legend should have a surrounding frame.

    Returns:
        tuple[bool, dict[str, Any]]:
            (moved, params) where ``moved`` indicates if the legend was
            repositioned and ``params`` holds ``figsize`` and
            ``subplots_adjust`` values.

    """
    # --- 0. No labeled artists, so legend is not needed ---------------------
    if not has_legend_items(ax):
        return False, {}
    # --- 1. If no legend exists, do nothing ---------------------------------
    legend_opt: Legend | None = ax.get_legend()
    if legend_opt is None:
        # User may have forgotten to create a legend; create an empty one for measurement.
        ax.legend()
        legend_opt = ax.get_legend()
    # if legend_opt is None:
    if legend_opt is None or len(legend_opt.get_texts()) == 0:
        # msg = "Failed to obtain a Legend object from the Axes – this is a bug."
        # raise RuntimeError(msg)
        if legend_opt is not None:
            legend_opt.remove()
        return False, {}
    legend: Legend = legend_opt
    # --- 2. Get pixel size (requires drawing) -------------------------------
    fig.canvas.draw()
    renderer: RendererBase = fig.canvas.get_renderer()  # type: ignore[attr-defined]
    legend_bbox_pix = legend.get_window_extent(renderer)   # (left, bottom, width, height) in px
    handles, labels = ax.get_legend_handles_labels()
    n_items = len(handles)
    too_wide = (max_width_px is not None) and (legend_bbox_pix.width > max_width_px)
    too_many = (max_items is not None) and (n_items > max_items)
    if not (too_wide or too_many):
        return False, {}
    # --- 3. Remove existing legend and reposition to the right ---------------------------
    ax_left, ax_bottom, ax_width, ax_height = ax.get_position().bounds
    legend.remove()
    ax_bbox_pix = ax.get_window_extent(renderer)
    ax_height_px = ax_bbox_pix.height
    cur_ncol = max(1, ncol)
    while True:
        legend = ax.legend(
            handles,
            labels,
            loc="center left",
            bbox_to_anchor=(1.0, 0.5),
            borderaxespad=0.5,
            ncol=cur_ncol,
            fontsize=fontsize,
            title=title,
            frameon=frameon,
        )
        fig.canvas.draw()
        legend_bbox = legend.get_window_extent(fig.canvas.get_renderer())  # type: ignore[attr-defined]
        if legend_bbox.height <= ax_height_px or cur_ncol >= n_items:
            break
        cur_ncol += 1
    # --- 4. Compute required Figure width and Axes position -------------------------------
    legend_width_in = legend_bbox.width / fig.dpi
    fig_width_in, fig_height_in = fig.get_size_inches()
    pad_width_in = pad_factor * fig_width_in
    # Distance from the left side of the Figure to the right edge of the Axes (in inches)
    axes_right_in = (ax_left + ax_width) * fig_width_in
    available_margin_in = fig_width_in - axes_right_in
    needed_total_in = legend_width_in + pad_width_in
    extra_width_in = max(0.0, needed_total_in - available_margin_in)
    new_fig_width_in = fig_width_in + extra_width_in
    # Scale the Axes positions so they keep the same visual size.
    scale = fig_width_in / new_fig_width_in
    new_left = ax_left * scale
    new_width = ax_width * scale
    # --- 5. Assemble results into a dictionary and return ------------------------------------
    params: dict[str, Any] = {
        "figsize": (new_fig_width_in, fig_height_in),
        "subplots_adjust": {
            "left": new_left,
            "right": new_left + new_width,
            "bottom": ax_bottom,
            "top": ax_bottom + ax_height,
        },
    }
    return True, params


def create_and_move_legend_to_right_if_needed_original(
    max_width_px: float | None = 300,
    max_items: int | None = 5,
    *,
    pad_factor: float = 0.05,
    ncol: int = 1,
    fontsize: int | str | None = None,
    title: str | None = None,
    frameon: bool = True,
) -> tuple[bool, dict[str, Any]]:
    """Legacy wrapper that works on the current figure and axes.

    Args:
        max_width_px: Maximum legend width in pixels (default 300).
        max_items: Maximum number of legend entries (default 5).
        pad_factor: Padding fraction between axes and legend.
        ncol: Starting number of legend columns.
        fontsize: Font size for the legend.
        title: Legend title.
        frameon: Whether the legend should have a frame.

    Returns:
        (moved, params) as described in the newer function.

    """
    fig = plt.gcf()
    ax = plt.gca()
    return create_and_move_legend_to_right_if_needed(
        fig,
        ax,
        max_width_px=max_width_px,
        max_items=max_items,
        pad_factor=pad_factor,
        ncol=ncol,
        fontsize=fontsize,
        title=title,
        frameon=frameon,
    )
