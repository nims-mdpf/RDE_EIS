from __future__ import annotations

import io
import logging
import math
import sys
import typing
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.optimize import curve_fit

from modules_eis import plot_utils

# ----------------------------------------------------------------------
# logger utilities (place near the top of the script)
# ----------------------------------------------------------------------
_LOGGER_NAME: Final = "eis"


def get_logger(name: str = _LOGGER_NAME) -> logging.Logger:
    """Return the shared logger (default name ``eis``)."""
    return logging.getLogger(name)


def _has_stdout_handler(logger: logging.Logger) -> bool:
    """Return True if the logger already has a StreamHandler that writes to stdout."""
    return any(
        isinstance(h, logging.StreamHandler) and h.stream is sys.stdout
        for h in logger.handlers
    )


def switch_to_stdout(force: bool = False, level: int = logging.INFO) -> None:
    """Remove all handlers and attach a single stdout StreamHandler.

    Args:
        force (bool) : Re-configure even if a stdout handler already exists.
        level (int) : Logging level (default ``logging.INFO``).

    """
    logger = get_logger()

    # if a stdout handler exists and we aren't forced, do nothing
    if _has_stdout_handler(logger) and not force:
        return

    # remove existing handlers
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()

    # add a fresh stdout handler
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(level)
    fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    sh.setFormatter(logging.Formatter(fmt, "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(sh)

    # finalise logger settings
    logger.setLevel(level)
    logger.propagate = False


logger = get_logger('eis')


# ----------------------------------------------------------------------
# 0. Constant definitions
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Constants:
    """Immutable configuration values used throughout the module.

    Attributes:
        BASE_TEMP_K: Temperature (K) used as the default reference point for Arrhenius plots.
        REFERENCE_TEMP_C: Temperature (°C) used as a secondary reference point.
        CELSIUS_TO_KELVIN_OFFSET: Offset to convert Celsius to Kelvin.
        BOLTZMANN_CONSTANT: Boltzmann constant in J/K.
        AVOGADRO_CONSTANT: Avogadro constant in 1/mol.
        FARADAY_CONSTANT_KJ: Faraday constant in kJ/(V·mol) (≈96485.3 C/mol ÷ 1000).

    """

    BASE_TEMP_K: float = 300.0
    REFERENCE_TEMP_C: float = 25.0
    CELSIUS_TO_KELVIN_OFFSET: Final[float] = 273.15
    BOLTZMANN_CONSTANT: Final[float] = 1.380649
    AVOGADRO_CONSTANT: Final[float] = 6.02214076
    FARADAY_CONSTANT_KJ: Final[float] = 96.4853


# CONST: Constants | None = None  # global
CONST: Constants = Constants()
# Usage: CONST = Constants(BASE_TEMP_K=300.0, REFERENCE_TEMP_C = 25.0)
# Error: CONST.BASE_TEMP_K = 333.0  # Raises dataclasses.FrozenInstanceError


SIGMA_TYPE: Final[dict[str, dict[str, Any]]] = {
    "total": {
        "filename_suffix": "total",
        "plot_label": "total",
        "plot_title": "Total",
    },
    "bulk": {
        "filename_suffix": "bulk",
        "plot_label": "bulk",
        "plot_title": "Bulk",
    },
    "gb": {
        "filename_suffix": "gb",
        "plot_label": "g.b.",
        "plot_title": "G.B.",
    },
}

# Unicode escape sequence for the Greek letter sigma
SIGMA_CHAR = '\u03C3'


class ConductivityColumn:
    """Column name constants for conductivity data frames."""

    TEMP_C = 'Temperature (C)'
    TEMP_K = 'Temperature (K)'
    RESISTIVITY = 'Resistivity (Ohm)'
    CONDUCTIVITY = 'Conductivity (S/cm)'
    INV_T_1000 = '1000/T (K^-1)'
    LOG_SIGMA = f"log {SIGMA_CHAR} (S cm^-1)"  # Column name in CSV: 'log sigma (S cm^-1)'
    LOG_SIGMA_T = f"log {SIGMA_CHAR} T (K S cm^-1)"  # Column name in CSV: 'log sigma T (K S cm^-1)'
    IMP_FILE = 'Impedance File'


# ----------------------------------------------------------------------
# 1. Conductivity data processing group
# ----------------------------------------------------------------------
# 1-1. Functions for handling a single conductivity file
def load_conductivity_data(csv_path: Path) -> pd.DataFrame:
    """Load a conductivity CSV file and force all columns to be strings.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        DataFrame containing the raw CSV data.

    """
    df = pd.read_csv(csv_path, dtype=str)  # Forces all columns to be strings
    # Remove the BOM if present in any column name
    if any(col.startswith('\ufeff') for col in df.columns):
        df.rename(columns=lambda c: c.lstrip('\ufeff'), inplace=True)
    logger.info("Loaded %s", csv_path)
    logger.info(f"df summary:\n{df.to_string(max_rows=5, max_cols=5)}")
    return df


def fill_missing_conductivity_data(df: pd.DataFrame) -> pd.DataFrame:  # noqa: C901
    """Fill missing values in a conductivity DataFrame.

    The function creates a numeric copy for calculations, performs temperature
    conversion, computes missing derived columns, and renames columns to the
    standardized sigma notation.

    Args:
        df: DataFrame with raw conductivity data (all columns as strings).

    Returns:
        DataFrame with missing values filled and column names normalized.

    """
    # Create a numeric DataFrame for calculations (working copy)
    df_numeric = df.copy()
    # Convert columns that can be numeric to float for calculations
    numeric_columns = [
        'Temperature (C)',
        'Temperature (K)',
        'Resistivity (Ohm)',
        'Conductivity (S/cm)',
        '1000/T (K^-1)',
        'log sigma (S cm^-1)',
        'log sigma T (K S cm^-1)',
    ]
    for col in numeric_columns:
        if col in df_numeric.columns:
            df_numeric[col] = pd.to_numeric(df_numeric[col], errors='coerce')
    # Result DataFrame retains original data types
    result_df = df.copy()
    # Process each row
    for idx in df.index:
        # Mutual completion of Temperature (C) and Temperature (K)
        temp_c = df_numeric.loc[idx, 'Temperature (C)']
        temp_k = df_numeric.loc[idx, 'Temperature (K)']
        if pd.isna(temp_c) and not pd.isna(temp_k):
            # Compute Celsius from Kelvin
            result_df.loc[idx, 'Temperature (C)'] = repr((temp_k - CONST.CELSIUS_TO_KELVIN_OFFSET).item())
        elif pd.isna(temp_k) and not pd.isna(temp_c):
            # Compute Kelvin from Celsius
            result_df.loc[idx, 'Temperature (K)'] = repr((temp_c + CONST.CELSIUS_TO_KELVIN_OFFSET).item())
        # Re‑convert after temperature completion
        temp_c = pd.to_numeric(result_df.loc[idx, 'Temperature (C)'], errors='coerce')
        temp_k = pd.to_numeric(result_df.loc[idx, 'Temperature (K)'], errors='coerce')
        # Check Resistivity and Conductivity
        conductivity = df_numeric.loc[idx, 'Conductivity (S/cm)']
        # Skip rows where required data are missing
        if pd.isna(conductivity):
            continue
        # Temperature (K) is required for subsequent calculations
        if pd.isna(temp_k):
            continue
        # Fill missing 1000/T (K^-1)
        if pd.isna(df_numeric.loc[idx, '1000/T (K^-1)']):
            result_df.loc[idx, '1000/T (K^-1)'] = repr((1000.0 / temp_k).item())
        # Fill missing log sigma (S cm^-1)
        if pd.isna(df_numeric.loc[idx, 'log sigma (S cm^-1)']):  # noqa: SIM102
            if conductivity > 0:
                result_df.loc[idx, 'log sigma (S cm^-1)'] = repr(np.log10(conductivity).item())
        # Fill missing log sigma T (K S cm^-1)
        if pd.isna(df_numeric.loc[idx, 'log sigma T (K S cm^-1)']):  # noqa: SIM102
            if conductivity > 0:
                sigma_t = conductivity * temp_k
                result_df.loc[idx, 'log sigma T (K S cm^-1)'] = repr(np.log10(sigma_t).item())
    # Rename columns to use the Greek sigma character
    result_df = result_df.rename(
        columns={
            'log sigma (S cm^-1)': f"log {SIGMA_CHAR} (S cm^-1)",
            'log sigma T (K S cm^-1)': f"log {SIGMA_CHAR} T (K S cm^-1)",
        },
    )
    logger.info("Calculated conductivity")
    logger.info(f"calculated df summary:\n{result_df.to_string(max_rows=5, max_cols=5)}")
    return result_df


def save_conductivity_data(df: pd.DataFrame, output_path: Path) -> None:
    """Save a conductivity DataFrame to CSV.

    Args:
        df: DataFrame to be saved.
        output_path: Destination file path.

    """
    df.to_csv(output_path, index=False)


def extract_conductivity_fitting_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare a numeric DataFrame for conductivity fitting.

    This function selects the columns required for fitting, coerces them to
    numeric types, replaces empty strings with NaN, and drops rows containing
    NaN values.

    Args:
        df: DataFrame containing conductivity data.

    Returns:
        Cleaned DataFrame ready for curve fitting.

    """
    # Prepare numeric DataFrame for fitting
    cols_for_fit = [
        ConductivityColumn.INV_T_1000,
        ConductivityColumn.LOG_SIGMA_T,
        ConductivityColumn.LOG_SIGMA,
    ]
    df_fit = (
        df[cols_for_fit]
        .apply(lambda s: pd.to_numeric(
            s.replace('', np.nan).replace('NaN', np.nan),
            errors="coerce",
        ))
        .dropna()
    )
    logger.info("Prepared fit data")
    logger.info(f"fitted df summary:\n{df_fit.to_string(max_rows=5, max_cols=5)}")
    return df_fit


def fit_conductivity_data(df: pd.DataFrame) -> tuple[dict, dict]:
    """Fit conductivity data for both log σ and log σ·T.

    Args:
        df: DataFrame prepared by `extract_conductivity_fitting_data`.

    Returns:
        A tuple containing two dictionaries:
        - Fit results for log σ.
        - Fit results for log σ·T.

    """
    logger.info("conductivity fitting")
    x: list[float] = pd.to_numeric(df[ConductivityColumn.INV_T_1000], errors='coerce').tolist()
    # log sigma
    y_s: list[float] = pd.to_numeric(df[ConductivityColumn.LOG_SIGMA], errors='coerce').tolist()
    logger.info("conductivity log s")
    out_s = analyze_conductivity_log_s(x, y_s)
    # log sigma T
    y_st: list[float] = pd.to_numeric(df[ConductivityColumn.LOG_SIGMA_T], errors='coerce').tolist()
    logger.info("conductivity log sT")
    out_st = analyze_conductivity_log_st(x, y_st)
    return out_s, out_st


def linear_approximation(x: Any, a: Any, b: Any) -> Any:
    """Linear approximation function.

    Args:
        x: Independent variable.
        a: Intercept.
        b: Slope.

    Returns:
        Computed y = a + b * x.

    """
    return a + b * x


def analyze_conductivity_log_st(
    x_fit: list[float],
    y_fit: list[float],
) -> dict[str, Any]:
    """Fit log10(σ·T) vs 1000/T and return a dictionary of results.

    Args:
        x_fit: Independent variable values (1000/T).
        y_fit: Dependent variable values (log σ·T).

    Returns:
        Dictionary containing activation energy, predicted conductivities,
        fitted parameters, and extended fit data for plotting.

    """
    (intercept, slope), _covariance = curve_fit(linear_approximation, x_fit, y_fit)
    logger.info(f"intercept: {intercept}")
    logger.info(f"slope: {slope}")
    inv_temp_base = 1000.0 / CONST.BASE_TEMP_K
    log_pred_base = intercept + slope * inv_temp_base
    logger.info(f"predict: {inv_temp_base}, {log_pred_base}")
    act_energy_kjmol = -slope * CONST.BOLTZMANN_CONSTANT * CONST.AVOGADRO_CONSTANT * np.log(10)
    act_energy_ev = act_energy_kjmol / CONST.FARADAY_CONSTANT_KJ
    logger.info(f"activation energy KJ/mol: {act_energy_kjmol}")
    logger.info(f"activation energy eV: {act_energy_ev}")
    sigma_base = 10 ** (intercept + slope * inv_temp_base) / CONST.BASE_TEMP_K
    inv_temp_ref = 1000.0 / (CONST.REFERENCE_TEMP_C + CONST.CELSIUS_TO_KELVIN_OFFSET)
    sigma_ref = 10 ** (intercept + slope * inv_temp_ref)
    logger.info(f"conductivity at 300K: {sigma_base}")
    logger.info(f"conductivity at 25C: {sigma_ref}")
    a_preexp = 10 ** intercept
    b_arr = slope * 1000.0 * np.log(10)
    logger.info(f"approximate: A={a_preexp}, B={b_arr}")
    sigma_pred = a_preexp / CONST.BASE_TEMP_K * np.exp(b_arr / CONST.BASE_TEMP_K)
    logger.info(f"predict: {CONST.BASE_TEMP_K}, {sigma_pred}")
    approx_formula = f"{SIGMA_CHAR}={a_preexp}/T*exp({b_arr}/T)"
    logger.info(f"approximate formula: {approx_formula}")
    x_extended = list(x_fit) + [inv_temp_base]
    y_extended = intercept + slope * np.array(x_extended)
    return {
        "activation_energy_ev": act_energy_ev,
        "activation_energy_kjmol": act_energy_kjmol,
        "conductivity_300k": sigma_base,
        "preexponetial_term": intercept,  # a_preexp,
        "approximate_formula": approx_formula,
        "x_pred": inv_temp_base,
        "y_pred": log_pred_base,
        "x_fit": x_extended,
        "y_fit": y_extended,
        "intercept": intercept,
        "slope": slope,
    }


def analyze_conductivity_log_s(
    x_fit: list[float],
    y_fit: list[float],
) -> dict[str, Any]:
    """Fit log10(σ) vs 1000/T and return a dictionary of results.

    Args:
        x_fit: Independent variable values (1000/T).
        y_fit: Dependent variable values (log σ).

    Returns:
        Dictionary containing activation energy, predicted conductivities,
        fitted parameters, and extended fit data for plotting.

    """
    (intercept, slope), _covariance = curve_fit(linear_approximation, x_fit, y_fit)
    logger.info(f"intercept: {intercept}")
    logger.info(f"slope: {slope}")
    inv_temp_base = 1000.0 / CONST.BASE_TEMP_K
    log_pred_base = intercept + slope * inv_temp_base
    logger.info(f"predict: {inv_temp_base}, {log_pred_base}")
    act_energy_kjmol = -slope * CONST.BOLTZMANN_CONSTANT * CONST.AVOGADRO_CONSTANT * np.log(10)
    act_energy_ev = act_energy_kjmol / CONST.FARADAY_CONSTANT_KJ
    logger.info(f"activation energy KJ/mol: {act_energy_kjmol}")
    logger.info(f"activation energy eV: {act_energy_ev}")
    sigma_base = 10 ** (intercept + slope * inv_temp_base)
    inv_temp_ref = 1000.0 / (CONST.REFERENCE_TEMP_C + CONST.CELSIUS_TO_KELVIN_OFFSET)
    sigma_ref = 10 ** (intercept + slope * inv_temp_ref)
    logger.info(f"conductivity at 300K: {sigma_base}")
    logger.info(f"conductivity at 25C: {sigma_ref}")
    a_preexp = 10 ** intercept
    b_arr = slope * 1000.0 * np.log(10)
    logger.info(f"approximate: A={a_preexp}, B={b_arr}")
    sigma_pred = a_preexp * np.exp(b_arr / CONST.BASE_TEMP_K)
    logger.info(f"predict: {CONST.BASE_TEMP_K}, {sigma_pred}")
    approx_formula = f"{SIGMA_CHAR}={a_preexp}*exp({b_arr}/T)"
    logger.info(f"approximate formula: {approx_formula}")
    x_extended = list(x_fit) + [inv_temp_base]
    y_extended = intercept + slope * np.array(x_extended)
    return {
        "activation_energy_ev": act_energy_ev,
        "activation_energy_kjmol": act_energy_kjmol,
        "conductivity_300k": sigma_base,
        "preexponetial_term": intercept,  # a_preexp,
        "approximate_formula": approx_formula,
        "x_pred": inv_temp_base,
        "y_pred": log_pred_base,
        "x_fit": x_extended,
        "y_fit": y_extended,
        "intercept": intercept,
        "slope": slope,
    }


def plot_conductivity_indivisual(
    df: pd.DataFrame,
    fit_param: dict,
    sigma_type: str,
    plot_type: str,
    x_attr: str,
    y_attr: str,
    title: str,
    output_path: Path,
    show_fit: bool = True,
    y_log: bool = False,
) -> None:
    """Create an individual conductivity plot using Matplotlib.

    Args:
        df: DataFrame containing the data to plot.
        fit_param: Dictionary with fitting parameters and extended data.
        sigma_type: Identifier for the sigma type (e.g., 'total', 'bulk').
        plot_type: String indicating the plot type (e.g., 'log_s', 'fit_st').
        x_attr: Name of the column to use for the x‑axis.
        y_attr: Name of the column to use for the y‑axis.
        title: Plot title.
        output_path: Destination file path for the saved figure.
        show_fit: Whether to display the fitted line and 300 K prediction.
        y_log: Whether to use a logarithmic scale for the y‑axis (unused here).

    """
    default_colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    x_data: list[float] = pd.to_numeric(df[x_attr], errors='coerce').tolist()
    y_data: list[float] = pd.to_numeric(df[y_attr], errors='coerce').tolist()
    color = default_colors[0]
    color_pred = default_colors[1]
    all_x = []
    all_y = []
    all_x.extend(x_data)
    all_y.extend(y_data)
    fig, ax = plot_utils.init_figure_matplotlib()
    label_sigma_type = SIGMA_TYPE[sigma_type]['plot_label']
    ax.scatter(x_data, y_data, label=label_sigma_type, color=color)
    # Individual plots always add fitting line and 300 K prediction
    if show_fit:
        ax.plot(fit_param['x_fit'], fit_param['y_fit'], color=color,
                label=f"{label_sigma_type} (fit)")
        ax.scatter(fit_param['x_pred'], fit_param['y_pred'], marker='s',
                   color=color_pred, zorder=5,
                   label=f'{label_sigma_type} (predict 300K)')
        all_x.append(fit_param['x_pred'])
        all_y.append(fit_param['y_pred'])
    xlims, ylims, xticks_args, yticks_args, xscale_args, yscale_args = (
        plot_utils.optimize_plot_limits(
            [all_x], [all_y], x_margin=0.05, y_margin=0.05))
    ax.set_xscale(xscale_args)
    ax.set_yscale(yscale_args)
    ax.set_xlim(*xlims)
    ax.set_ylim(*ylims)
    ax.set_xticks(xticks_args)
    ax.set_yticks(yticks_args)
    ax.set_xlabel(x_attr, labelpad=20)
    ax.set_ylabel(y_attr)
    ax.set_title(title, pad=20)
    ax.legend()
    moved, adjust_params = plot_utils.create_and_move_legend_to_right_if_needed(fig, ax)
    if moved:
        fig.set_size_inches(*adjust_params["figsize"])
        plt.subplots_adjust(**adjust_params["subplots_adjust"])
    fig.savefig(output_path)
    plt.close(fig)
    logger.info(f"Saved: {output_path}")


def create_arrhenius_plotly_indivisual(
    df: pd.DataFrame,
    fit_param: dict,
    sigma_type: str,
    plot_type: str,
    x_attr: str,
    y_attr: str,
    title: str,
    output_path: Path,
    show_fit: bool = True,
    y_log: bool = False,
) -> dict[str, go.Figure]:
    """Create an individual Arrhenius plot using Plotly.

    Args:
        df: DataFrame containing the data to plot.
        fit_param: Dictionary with fitting parameters and extended data.
        sigma_type: Identifier for the sigma type.
        plot_type: Plot type string.
        x_attr: Column name for the x‑axis.
        y_attr: Column name for the y‑axis.
        title: Plot title.
        output_path: Destination path for the saved image (not used for the figure object).
        show_fit: Whether to include the fitted line and prediction point.
        y_log: Whether to use a logarithmic y‑axis.

    Returns:
        Dictionary mapping the title to the generated Plotly Figure.

    """
    x_data: list[float] = pd.to_numeric(df[x_attr], errors='coerce').tolist()
    y_data: list[float] = pd.to_numeric(df[y_attr], errors='coerce').tolist()
    label_sigma_type = SIGMA_TYPE[sigma_type]['plot_label']
    # Plotly
    plot_data = []
    plot_data.append(go.Scatter(
        x=x_data, y=y_data, mode='markers', name=f"{label_sigma_type} (exp)",
    ))
    if show_fit:
        params = fit_param
        plot_data.append(go.Scatter(
            x=params['x_fit'], y=params['y_fit'], mode="lines",
            name=f"{label_sigma_type} (fit)",
        ))
        plot_data.append(go.Scatter(
            x=[params['x_pred']], y=[params['y_pred']], mode="markers",
            name=f"{label_sigma_type} (predict 300K)",
        ))
    go_fig = go.Figure(data=plot_data)
    y_scale = 'log' if y_log else 'linear'
    go_fig.update_layout(
        xaxis={"title": x_attr},
        yaxis={"title": y_attr, "type": y_scale, "exponentformat": "e"},
        title=title,
    )
    return {title: go_fig}


# 1-2. Functions for combining multiple conductivity files
def plot_conductivity_combined(
    dfs: dict[str, pd.DataFrame],  # key: sigma_type
    fit_params: dict[str, dict] | None,   # key: sigma_type
    plot_type: str,
    x_attr: str,
    y_attr: str,
    title: str,
    output_path: Path,
    show_fit: bool = True,
    y_log: bool = False,
) -> None:
    """Create a combined conductivity plot for multiple sigma types.

    Args:
        dfs: Mapping from sigma type to its DataFrame.
        fit_params: Mapping from sigma type to its fitting parameters.
        plot_type: Identifier for the plot type.
        x_attr: Column name used for the x‑axis.
        y_attr: Column name used for the y‑axis.
        title: Plot title.
        output_path: Destination file path.
        show_fit: Whether to include fitted lines and predictions.
        y_log: Whether to use a logarithmic y‑axis.

    """
    default_colors = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    fig, ax = plot_utils.init_figure_matplotlib()
    all_x = []
    all_y = []
    order = SIGMA_TYPE.keys()  # ["total", "bulk", "gb"]
    dfs = {k: dfs[k] for k in order if k in dfs}
    for idx, (sigma_type, df) in enumerate(dfs.items()):
        label_sigma_type = SIGMA_TYPE[sigma_type]['plot_label']
        x_data: list[float] = pd.to_numeric(df[x_attr], errors='coerce').tolist()
        y_data: list[float] = pd.to_numeric(df[y_attr], errors='coerce').tolist()
        color = default_colors[idx % len(default_colors)]
        color_pred = default_colors[(idx + len(dfs)) % len(default_colors)]
        all_x.extend(x_data)
        all_y.extend(y_data)
        ax.scatter(x_data, y_data, label=f"{label_sigma_type} (exp)", color=color)
        # if show_fit:
        if show_fit and fit_params:
            ax.plot(fit_params[sigma_type]['x_fit'],
                    fit_params[sigma_type]['y_fit'],
                    color=color, label=f"{label_sigma_type} (fit)")
            ax.scatter(fit_params[sigma_type]['x_pred'],
                       fit_params[sigma_type]['y_pred'],
                       marker='s', color=color_pred, zorder=5,
                       label=f'{label_sigma_type} (predict 300K)')
            all_x.extend([fit_params[sigma_type]['x_pred']])
            all_y.extend([fit_params[sigma_type]['y_pred']])
    y_scale = 'log' if y_log else 'linear'
    xlims, ylims, xticks_args, yticks_args, xscale_args, yscale_args = (
        plot_utils.optimize_plot_limits(
            [all_x], [all_y], x_margin=0.05, y_margin=0.05, y_scale=y_scale))
    ax.set_xscale(xscale_args)
    ax.set_yscale(yscale_args)
    ax.set_xlim(*xlims)
    ax.set_ylim(*ylims)
    ax.set_xticks(xticks_args)
    ax.set_yticks(yticks_args)
    ax.set_xlabel(x_attr, labelpad=20)
    ax.set_ylabel(y_attr)
    ax.set_title(title, pad=20)
    ax.legend()
    moved, adjust_params = plot_utils.create_and_move_legend_to_right_if_needed(fig, ax)
    if moved:
        fig.set_size_inches(*adjust_params["figsize"])
        plt.subplots_adjust(**adjust_params["subplots_adjust"])
    fig.savefig(output_path)
    plt.close(fig)
    logger.info(f"Saved: {output_path}")


def create_arrhenius_plotly_combined(
    dfs: dict[str, pd.DataFrame],  # key: sigma_type
    fit_params: dict[str, dict] | None,   # key: sigma_type
    plot_type: str,
    x_attr: str,
    y_attr: str,
    title: str,
    output_path: Path,
    show_fit: bool = True,
    y_log: bool = False,
) -> dict[str, go.Figure | dict[str, go.Figure | pd.DataFrame]]:
    """Create a combined Arrhenius plot for multiple sigma types using Plotly.

    Args:
        dfs: Mapping from sigma type to its DataFrame.
        fit_params: Mapping from sigma type to its fitting parameters.
        plot_type: Identifier for the plot type.
        x_attr: Column name for the x‑axis.
        y_attr: Column name for the y‑axis.
        title: Plot title.
        output_path: Destination path for the saved image (not used for the figure object).
        show_fit: Whether to include fitted lines and predictions.
        y_log: Whether to use a logarithmic y‑axis.

    Returns:
        dict: `{title: fig}` or `{title: {"fig": fig, "params": df_params}}`
        (the latter is returned only when ``show_fit=True`` and ``fit_params`` is provided).

    """
    plot_data = []
    order = SIGMA_TYPE.keys()  # ["total", "bulk", "gb"]
    dfs = {k: dfs[k] for k in order if k in dfs}
    for sigma_type, df in dfs.items():
        label_sigma_type = SIGMA_TYPE[sigma_type]['plot_label']
        x_data: list[float] = pd.to_numeric(df[x_attr], errors='coerce').tolist()
        y_data: list[float] = pd.to_numeric(df[y_attr], errors='coerce').tolist()
        plot_data.append(go.Scatter(
            x=x_data, y=y_data, mode='markers',
            name=f"{label_sigma_type} (exp)",
        ))
        if show_fit and fit_params:
            params = fit_params[sigma_type]
            plot_data.append(go.Scatter(
                x=params['x_fit'], y=params['y_fit'], mode="lines",
                name=f"{label_sigma_type} (fit)",
            ))
            plot_data.append(go.Scatter(
                x=[params['x_pred']], y=[params['y_pred']], mode="markers",
                name=f"{label_sigma_type} (predict 300K)",
            ))
    go_fig = go.Figure(data=plot_data)
    y_scale = 'log' if y_log else 'linear'
    go_fig.update_layout(
        xaxis={"title": x_attr},
        yaxis={"title": y_attr, "type": y_scale, "exponentformat": "e"},
    )
    go_fig.update_layout(title=title)

    if show_fit and fit_params is not None:
        df_params = pd.DataFrame.from_dict(fit_params).astype(str)
        order = SIGMA_TYPE.keys()  # ["total", "bulk", "gb"]
        df_params = df_params[[c for c in order if c in df_params.columns]]  # Reorder the columns
        df_params = df_params.rename(columns={c: SIGMA_TYPE[c]['plot_label'] for c in order})
        df_params = df_params.drop(index=['x_fit', 'y_fit'])
        left_hand_side = f"log {SIGMA_CHAR}T" if plot_type == 'fit_st' else f"log {SIGMA_CHAR}"
        for col in df_params.columns.to_list():
            df_params.loc["fitting parameter", col] = (
                f"{left_hand_side} = "
                f"{df_params.loc['intercept', col]} + "
                f"{df_params.loc['slope', col]} * (1000/T)"
            )
        name_and_order_map: Final[dict[str, str]] = {
            "activation_energy_ev": "activation energy (eV)",
            "activation_energy_kjmol": "activation energy (KJ/mol)",
            "preexponetial_term": "preexponetial term",
            "conductivity_300k": "conductivity (predict 300K) (S/cm)",
            "approximate_formula": "approximate formula",
            "fitting parameter": "fitting parameter",
        }
        df_params = df_params.rename(index=name_and_order_map).reindex(index=list(name_and_order_map.values()))
        df_params = df_params.reset_index()
        df_params = df_params.rename(columns={'index': ''})

        return {title: {'fig': go_fig, 'params': df_params}}
    return {title: go_fig}


# 1-3. File‑path generation utility
def get_conductivity_file_paths(input_dir: Path) -> dict[str, Path]:
    """Retrieve conductivity CSV file paths from a directory.

    Args:
        input_dir: Directory containing conductivity CSV files.

    Returns:
        Dictionary mapping sigma type strings to their corresponding CSV file
        Path objects. Keys are the same as the `SIGMA_TYPE` identifiers.

    """
    csv_paths: dict[str, Path] = {}
    if not input_dir:
        return csv_paths

    order = SIGMA_TYPE.keys()
    for entry in input_dir.iterdir():
        if not entry.is_file() or entry.suffix.lower() != ".csv":
            continue
        name = entry.name.lower()
        for key in order:
            suffix = SIGMA_TYPE[key]["filename_suffix"]
            if f"conductivity_{suffix}" in name:
                csv_paths[key] = entry
                break

    has_total = "total" in csv_paths
    has_bulk = "bulk" in csv_paths
    has_gb = "gb" in csv_paths

    if (has_bulk or has_gb) and not has_total:
        msg = (
            "bulk または gb conductivity file が存在する場合、"
            "total conductivity file も必要です。"
        )
        raise ValueError(
            msg,
        )

    return csv_paths


# ----------------------------------------------------------------------
# 2. Impedance data processing group
# ----------------------------------------------------------------------
# 2-1. Functions for handling a single impedance file
def load_impedance_file(file_path: Path) -> list[str]:
    """Load an impedance file and return its lines.

    Args:
        file_path: Path to the impedance file.

    Returns:
        List of strings, each representing a line in the file.

    """
    with open(file_path, encoding="utf-8") as f:
        lines = f.readlines()
    logger.info("Reading impedance file: %s", file_path.name)
    return lines


def split_impedance_header_and_data(
    lines: list[str],
) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
    """Separate the header and data sections of an impedance file.

    Args:
        lines: List of lines read from the impedance file.

    Returns:
        A tuple `(header_df, data_df)` where `header_df` contains the header
        information and `data_df` contains the numeric data.

    """
    # Separate header and data sections
    i_start: int = 0
    i_end: int = 0
    tab_sep: bool = False
    find_data: bool = False
    for i, line in enumerate(lines):
        if ("Re(Z)/Ohm" in line and "Im(Z)/Ohm" in line) \
                or ("Z'(a)" in line and "Z''(b)" in line) \
                or ("Z'(a)" in line and "Z\"(b)" in line):
            i_start = i
            tab_sep = "\t" in line
            find_data = True
        if "End Comments" in line:
            i_end = i
    skip_rows = list(range(i_start)) + [i_end]
    df: pd.DataFrame | None = None
    df_header: pd.DataFrame | None = None
    if find_data:
        try:
            txt = "".join(lines)
            buffer = io.StringIO(txt)
            sep = "\t" if tab_sep else r"\s+"
            df = pd.read_csv(buffer, sep=sep, skiprows=skip_rows, header=0, engine='python')
        except Exception as e:
            logger.info(f"tab_sep={tab_sep}")
            logger.error(f"Read impedance data header failed: {e}")
            sys.exit(1)
    header_rows = lines[: i_start]
    df_header = pd.DataFrame(data=[row.strip() for row in header_rows])
    if df is not None:
        logger.info(f"experiment df summary:\n{df.to_string(max_rows=5, max_cols=5)}")
    return df_header, df


def save_impedance_data(df: pd.DataFrame, output_path: Path) -> None:
    """Save impedance data to CSV without a header.

    Args:
        df: DataFrame containing impedance data.
        output_path: Destination file path.

    """
    # Function not needed?
    # <filename>_data.csv
    df.to_csv(output_path, header=False)


def extract_and_calculate_missing_columns(  # noqa: PLR0912, C901
        experiment_data: pd.DataFrame) -> pd.DataFrame:
    """Extract required columns and calculate missing impedance quantities.

    This function builds a new DataFrame with standardized column names,
    copies existing columns where possible, and computes magnitude and phase
    when they are missing.

    Args:
        experiment_data: Raw DataFrame from the impedance measurement.

    Returns:
        DataFrame with columns:
        `freq/Hz`, `Re(Z)/Ohm`, `-Im(Z)/Ohm`, `|Z|/Ohm`, `Phase(Z)/deg`.

    """
    df_exp = experiment_data.copy()
    cols = df_exp.columns
    df_calc = pd.DataFrame(columns=[
        "freq/Hz", "Re(Z)/Ohm", "-Im(Z)/Ohm", "|Z|/Ohm", "Phase(Z)/deg",
    ])
    if ("freq/Hz" in cols):
        df_calc["freq/Hz"] = df_exp["freq/Hz"]
    if ("Re(Z)/Ohm" in cols):
        df_calc["Re(Z)/Ohm"] = df_exp["Re(Z)/Ohm"]
    if ("-Im(Z)/Ohm" in cols):
        df_calc["-Im(Z)/Ohm"] = df_exp["-Im(Z)/Ohm"]
    if ("Im(Z)/Ohm" in cols):
        df_calc["-Im(Z)/Ohm"] = -1.0 * df_exp["Im(Z)/Ohm"]
    if ("|Z|/Ohm" in cols):
        df_calc["|Z|/Ohm"] = df_exp["|Z|/Ohm"]
    if ("Phase(Z)/deg" in cols):
        df_calc["Phase(Z)/deg"] = df_exp["Phase(Z)/deg"]
    if ("Freq(Hz)" in cols):
        df_calc["freq/Hz"] = df_exp["Freq(Hz)"]
    if ("  Freq(Hz)" in cols):
        df_calc["freq/Hz"] = df_exp["  Freq(Hz)"]
    if ("Z'(a)" in cols):
        df_calc["Re(Z)/Ohm"] = df_exp["Z'(a)"]
    if ("Z''(b)" in cols):
        df_calc["-Im(Z)/Ohm"] = -1.0 * df_exp["Z''(b)"]
    if ("Freq.(Hz)" in cols):
        df_calc["freq/Hz"] = df_exp["Freq.(Hz)"]
    if ("Z'(a)" in cols):
        df_calc["Re(Z)/Ohm"] = df_exp["Z'(a)"]
    if ('Z"(b)' in cols):
        df_calc["-Im(Z)/Ohm"] = -1.0 * df_exp['Z"(b)']
    # Calculate magnitude and phase when NaN
    arr = df_calc.to_numpy()
    for i, row in enumerate(arr):
        if np.isnan(row[3]):  # |Z|
            z = complex(row[1], -row[2])
            row[3] = np.abs(z)
            df_calc.iat[i, 3] = row[3]
        if np.isnan(row[4]):  # Phase
            z = complex(row[1], -row[2])
            row[4] = np.angle(z, deg=True)
            df_calc.iat[i, 4] = row[4]
    logger.info(f"calculated df summary:\n{df_calc.to_string(max_rows=5, max_cols=5)}")
    return df_calc


def save_impedance_plot_data(df: pd.DataFrame, output_path: Path) -> None:
    """Save calculated impedance data to CSV without a header.

    Args:
        df: DataFrame with calculated impedance quantities.
        output_path: Destination file path.

    """
    # Function not needed?
    # <filename>_calc.csv
    df.to_csv(output_path, header=False)


# 2-2. Composite plot processing functions
def plot_cole_cole(
    dfs: dict[str, pd.DataFrame],
    output_path: Path,
    *,
    is_normalized: bool = False,
) -> None:
    """Create a Cole‑Cole plot for multiple impedance datasets.

    Args:
        dfs (dict[str, pd.DataFrame]): Mapping from a label to its impedance DataFrame.
        output_path (Path): Destination file path for the saved image.
        is_normalized (bool): Whether the input data is already normalized. Defaults to False.

    """
    # Preparations to align the X and Y axis limits for a Cole‑Cole plot
    all_data: list = []
    for _label, df in dfs.items():
        all_data.extend(df["Re(Z)/Ohm"])
        all_data.extend(df["-Im(Z)/Ohm"])
    min_val = min(all_data)
    max_val = max(all_data)
    fig, ax = plot_utils.init_figure_matplotlib()
    for label, df in dfs.items():
        ax.scatter(df["Re(Z)/Ohm"], df["-Im(Z)/Ohm"], label=label, s=1.5)  # s=1.5=linewidth
    adjust_params = plot_utils.align_axes_range_and_ticks_plt(
        min_val, max_val, margin=0.05, fix_origin_to_zero=True)
    ax.set_xlim(*adjust_params["xlim"])
    ax.set_ylim(*adjust_params["ylim"])
    ax.set_xticks(adjust_params["xticks"])
    ax.set_yticks(adjust_params["yticks"])
    fig.set_size_inches(*adjust_params['figsize'])
    ax.set_xlabel("Re(Z) (Ohm" + (" cm" if is_normalized else "") + ")", labelpad=20)
    ax.set_ylabel("-Im(Z) (Ohm" + (" cm" if is_normalized else "") + ")")
    ax.set_title("Cole-Cole" + (" (normalized)" if is_normalized else ""), pad=20)
    ax.legend()
    moved, adjust_params = plot_utils.create_and_move_legend_to_right_if_needed(
        fig, ax)
    if moved:
        fig.set_size_inches(*adjust_params["figsize"])
        plt.subplots_adjust(**adjust_params["subplots_adjust"])
    fig.savefig(output_path)
    plt.close(fig)


def plot_bode_magnitude(
    dfs: dict[str, pd.DataFrame],
    output_path: Path,
    *,
    is_normalized: bool = False,
) -> None:
    """Create a Bode magnitude plot (|Z| vs frequency) for multiple datasets.

    Args:
        dfs: Mapping from a label to its impedance DataFrame.
        output_path: Destination file path for the saved image.
        is_normalized (bool): Whether the input data is already normalized. Defaults to False.

    """
    # Preparations to align the X and Y axis limits for a Bode magnitude plot
    x_data: list = []
    y_data: list = []
    for _label, df in dfs.items():
        x_data.extend(df["freq/Hz"])
        y_data.extend(df["|Z|/Ohm"])
    xlims, ylims, xticks_args, yticks_args, xscale_args, yscale_args = (
        plot_utils.optimize_plot_limits(
            x_data, y_data, y_margin=0.05, x_scale='log', y_scale='log'))
    fig, ax = plot_utils.init_figure_matplotlib()
    for label, df in dfs.items():
        ax.scatter(df["freq/Hz"], df["|Z|/Ohm"], label=label, s=1.5)  # s=1.5=linewidth
    ax.set_xscale(xscale_args)
    ax.set_yscale(yscale_args)
    ax.set_xlim(xlims)
    ax.set_ylim(ylims)
    ax.set_xticks(xticks_args)
    ax.set_yticks(yticks_args)
    ax.set_xlabel("Frequency (Hz)", labelpad=20)
    ax.set_ylabel("|Z| (Ohm" + (" cm" if is_normalized else "") + ")")
    ax.set_title("Bode |Z|" + (" (normalized)" if is_normalized else ""), pad=20)
    ax.legend()
    moved, adjust_params = plot_utils.create_and_move_legend_to_right_if_needed(
        fig, ax)
    if moved:
        fig.set_size_inches(*adjust_params["figsize"])
        plt.subplots_adjust(**adjust_params["subplots_adjust"])
    fig.savefig(output_path)
    plt.close(fig)


def plot_bode_phase(
    dfs: dict[str, pd.DataFrame],
    output_path: Path,
    *,
    invert_phase: bool = False,
    is_normalized: bool = False,
) -> None:
    """Create a Bode phase plot (phase vs frequency) for multiple datasets.

    Args:
        dfs (dict[str, pd.DataFrame]): Mapping from a label to its impedance DataFrame.
        output_path (Path): Destination file path for the saved image.
        invert_phase (bool): If True, inverts the y-axis (phase) of the plot. Defaults to False.
        is_normalized (bool): Whether the input data is already normalized. Defaults to False.

    """
    # Preparations to align the X and Y axis limits for a Bode phase plot
    x_data: list = []
    y_data: list = []
    for _label, df in dfs.items():
        x_data.extend(df["freq/Hz"])
        y_data.extend(df["Phase(Z)/deg"])
    xlims, ylims, xticks_args, yticks_args, xscale_args, yscale_args = (
        plot_utils.optimize_plot_limits(
            x_data, y_data, y_margin=0.05, x_scale='log'))
    fig, ax = plot_utils.init_figure_matplotlib()
    for label, df in dfs.items():
        ax.scatter(df["freq/Hz"], df["Phase(Z)/deg"], label=label, s=1.5)  # s=1.5=linewidth

    # Set the X‑ and Y‑axis limits to be identical so the plot is close to square
    ax.set_xscale(xscale_args)
    ax.set_yscale(yscale_args)
    ax.set_xlim(xlims)
    ax.set_ylim(ylims)
    ax.set_xticks(xticks_args)
    ax.set_yticks(yticks_args)
    ax.set_xlabel("Frequency (Hz)", labelpad=20)
    ax.set_ylabel("Phase(Z) (deg)")
    suffix_parts = ("inverted" if invert_phase else None, "normalized" if is_normalized else None)
    suffix = "".join(f" ({p})" for p in suffix_parts if p)
    ax.set_title(f"Bode Phase(Z){suffix}", pad=20)
    if invert_phase:
        ax.invert_yaxis()
    ax.legend()
    moved, adjust_params = plot_utils.create_and_move_legend_to_right_if_needed(
        fig, ax)
    if moved:
        fig.set_size_inches(*adjust_params["figsize"])
        plt.subplots_adjust(**adjust_params["subplots_adjust"])
    fig.savefig(output_path)
    plt.close(fig)


def create_cole_cole_plotly(
    dfs: dict[str, pd.DataFrame],
    *,
    is_normalized: bool = False,
) -> tuple[go.Figure, go.Figure]:
    """Create interactive Cole‑Cole plots using Plotly.

    Returns a tuple `(interactive_fig, printable_fig)` where the printable
    version has the legend‑show/hide button removed.

    Args:
        dfs (dict[str, pd.DataFrame]): Mapping from a label to its impedance DataFrame.
        is_normalized (bool): Whether the input data is already normalized. Defaults to False.

    Returns:
        A tuple containing two Plotly Figure objects.

    """
    # Preparations to align the X and Y axis limits for a Cole‑Cole plot
    all_data: list = []
    for _legend, df in dfs.items():
        all_data.extend(df["Re(Z)/Ohm"])
        all_data.extend(df["-Im(Z)/Ohm"])
    min_val = min(all_data)
    max_val = max(all_data)
    padding = (max_val - min_val) * 0.05  # Add a 5% margin
    cole_cole_range_min = min_val - padding  # for Plotly
    cole_cole_range_max = max_val + padding  # for Plotly
    # plotly
    plot_data: list = []
    for legend, df in dfs.items():
        plot_data.append(go.Scatter(
            x=df["Re(Z)/Ohm"], y=df["-Im(Z)/Ohm"],
            mode="markers", name=legend,
        ))
    go_fig = go.Figure(data=plot_data)
    go_fig.update_layout(
        title="Cole-Cole" + (" (normalized)" if is_normalized else ""),
        xaxis={
            "title": "Re(Z) (Ohm" + (" cm" if is_normalized else "") + ")",
            "range": [cole_cole_range_min, cole_cole_range_max],
            "constrain": "domain",
            "exponentformat": "power",
            "autorange": False,
        },
        yaxis={
            "title": "-Im(Z) (Ohm" + (" cm" if is_normalized else "") + ")",
            "range": [cole_cole_range_min, cole_cole_range_max],
            "scaleanchor": "x",
            "scaleratio": 1,
            "constrain": "domain",
            "exponentformat": "power",
            "autorange": False,
        },
        margin={"l": 80, "r": 80, "t": 80, "b": 80},
        legend={
            "entrywidth": 200,
            "entrywidthmode": "pixels",
        },
    )
    create_show_and_hide_buttons(go_fig)
    # Remove the legend show/hide button for printing.
    print_go_fig = go.Figure(go_fig.to_dict())
    print_go_fig.layout.updatemenus = []
    return go_fig, print_go_fig


def create_bode_magnitude_plotly(
    dfs: dict[str, pd.DataFrame],
    *,
    is_normalized: bool = False,
) -> tuple[go.Figure, go.Figure]:
    """Create interactive Bode magnitude plots using Plotly.

    Returns a tuple `(interactive_fig, printable_fig)`.

    Args:
        dfs: Mapping from a label to its impedance DataFrame.
        is_normalized (bool): Whether the input data is already normalized. Defaults to False.

    Returns:
        Two Plotly Figure objects.

    """
    # Preparations to align the X and Y axis limits for a Bode magnitude plot
    x_data: list = []
    y_data: list = []
    for _label, df in dfs.items():
        x_data.extend(df["freq/Hz"])
        y_data.extend(df["|Z|/Ohm"])
    # plotly
    plot_data: list = []
    for label, df in dfs.items():
        plot_data.append(go.Scatter(
            x=df["freq/Hz"], y=df["|Z|/Ohm"], mode="markers", name=label,
        ))
    go_fig = go.Figure(data=plot_data)
    go_fig.update_layout(
        title="Bode |Z|" + (" (normalized)" if is_normalized else ""),
        xaxis={
            "title": "Frequency (Hz)",
            "type": "log",
            "constrain": "domain",
            "exponentformat": "power",
        },
        yaxis={
            "title": "|Z| (Ohm" + (" cm" if is_normalized else "") + ")",
            "type": "log",
            "constrain": "domain",
            "exponentformat": "power",
        },
        margin={"l": 80, "r": 80, "t": 80, "b": 80},
        legend={
            "entrywidth": 200,
            "entrywidthmode": "pixels",
        },
    )
    create_show_and_hide_buttons(go_fig)
    # Remove the legend show/hide button for printing.
    print_go_fig = go.Figure(go_fig.to_dict())
    print_go_fig.layout.updatemenus = []
    return go_fig, print_go_fig


def create_bode_phase_plotly(
    dfs: dict[str, pd.DataFrame],
    *,
    invert_phase: bool = False,
    is_normalized: bool = False,
) -> tuple[go.Figure, go.Figure]:
    """Create interactive Bode phase plots using Plotly.

    Returns a tuple `(interactive_fig, printable_fig)`.

    Args:
        dfs(dict[str, pd.DataFrame]): Mapping from a label to its impedance DataFrame.
        invert_phase (bool): If True, inverts the y-axis (phase) of the plot. Defaults to False.
        is_normalized (bool): Whether the input data is already normalized. Defaults to False.

    Returns:
        Two Plotly Figure objects.

    """
    # plotly
    plot_data = []
    for label, df in dfs.items():
        plot_data.append(go.Scatter(
            x=df["freq/Hz"], y=df["Phase(Z)/deg"], mode="markers", name=label,
        ))
    go_fig = go.Figure(data=plot_data)
    suffix_parts = ("inverted" if invert_phase else None, "normalized" if is_normalized else None)
    suffix = "".join(f" ({p})" for p in suffix_parts if p)
    go_fig.update_layout(
        title=f"Bode Phase(Z){suffix}",
        xaxis={
            "title": "Frequency (Hz)",
            "type": "log",
            "constrain": "domain",
            "exponentformat": "power",
        },
        yaxis={
            "title": "Phase(Z) (deg)",
            "constrain": "domain",
            "exponentformat": "power",
            "autorange": "reversed" if invert_phase else None,
        },
        margin={"l": 80, "r": 80, "t": 80, "b": 80},
        legend={
            "entrywidth": 200,
            "entrywidthmode": "pixels",
        },
    )
    create_show_and_hide_buttons(go_fig)
    # Remove the legend show/hide button for printing.
    print_go_fig = go.Figure(go_fig.to_dict())
    print_go_fig.layout.updatemenus = []
    return go_fig, print_go_fig


def create_show_and_hide_buttons(go_fig: go.Figure) -> None:
    """Add “Show all” / “Hide all” buttons to a Plotly figure.

    The function mutates *go_fig* in‑place by inserting an ``updatemenus``
    element that toggles the visibility of all traces.  The figure is returned
    implicitly (i.e., the function returns ``None``).

    Args:
        go_fig (go.Figure):
            The Plotly ``Figure`` object to which the buttons will be added.
            The figure is modified directly; a new figure is not created.

    Returns:
        None

    """
    go_fig.update_layout(
        updatemenus=[{
            "type": "buttons", "direction": "left", "x": 1.00, "y": 1.10,
            "buttons": [
                {"label": "Show all", "method": "restyle", "args": [{"visible": True}]},
                {"label": "Hide all", "method": "restyle", "args": [{"visible": "legendonly"}]},
            ],
        }],
    )


# 2-3. File‑path generation utility for impedance files
def get_impedance_file_paths(directory_path: Path) -> list[Path]:
    """Collect impedance files with supported extensions from a directory.

    Supported extensions are `.mpt`, `.z`, and `.txt`.

    Args:
        directory_path: Directory to search for impedance files.

    Returns:
        List of Path objects for each matching file.

    """
    extensions = ['.mpt', '.z', '.txt']
    imp_files = []
    for file_path in sorted(directory_path.glob('*')):
        if file_path.is_file() and file_path.suffix.lower() in extensions:  # Process only files (excluding directories)
            imp_files.append(str(file_path))
    return [Path(s) for s in imp_files]


# ----------------------------------------------------------------------
# 3. Data linking functions
# ----------------------------------------------------------------------
def find_temperature_for_impedance_file(
    conductivity_df: pd.DataFrame,
    impedance_file: Path,
) -> str | None:
    """Find the temperature (°C) associated with an impedance file name.

    Args:
        conductivity_df: DataFrame that includes a column mapping file names to temperatures.
        impedance_file: File path of the impedance measurement.

    Returns:
        Temperature as a string if found; otherwise, None.

    """
    # str: temperature (C), None if not found
    condition = conductivity_df[ConductivityColumn.IMP_FILE] == impedance_file.name
    temp_value = conductivity_df.loc[condition, ConductivityColumn.TEMP_C]
    if temp_value.empty:
        return None
    return temp_value.iloc[0]


def extract_cond_resist_coeff_avg(conductivity_df: pd.DataFrame | None) -> float | None:
    """Compute the mean of ``1 / (Resistivity × Conductivity)`` over all rows of a DataFrame.

    Args:
        conductivity_df: DataFrame containing the columns
            ``ConductivityColumn.RESISTIVITY`` and
            ``ConductivityColumn.CONDUCTIVITY``. May be ``None``.

    Returns:
        Float with the average coefficient, or ``None`` when unavailable.

    """
    if conductivity_df is None:
        return None
    res_all = pd.to_numeric(conductivity_df[ConductivityColumn.RESISTIVITY], errors="coerce")
    cond_all = pd.to_numeric(conductivity_df[ConductivityColumn.CONDUCTIVITY], errors="coerce")
    avg_series = (1.0 / (res_all * cond_all)).replace([float("inf"), -float("inf")], pd.NA)
    avg = avg_series.mean()
    if pd.isna(avg):
        return None
    return float(avg)


def extract_normalization_coeff(
    conductivity_df: pd.DataFrame | None,
    impedance_file: Path,
    *,
    pellet_coeff: float | None,
) -> float | None:
    """Get the A/L normalization coefficient.

    The coefficient is ``1 / (Resistivity * Conductivity)``.

    Retrieval order:
    1. If a row in ``conductivity_df`` matches ``impedance_file.name``,
       compute ``1/(resistivity*conductivity)`` from that row.
       If conversion fails, fall back to step 2.
    2. Use the average of all valid rows (``extract_cond_resist_coeff_avg``).
    3. If the average cannot be computed, use ``pellet_coeff``.

    If both ``conductivity_df`` and ``pellet_coeff`` are ``None``, ``None`` is
    returned and a warning is logged.

    Args:
        conductivity_df: DataFrame that (when not ``None``) contains the columns
            ``ConductivityColumn.IMP_FILE``, ``ConductivityColumn.RESISTIVITY``,
            and ``ConductivityColumn.CONDUCTIVITY``.
        impedance_file: Path to the impedance file; only its ``name`` is used for
            matching.
        pellet_coeff: A/L value derived from pellet geometry (area/length); used as
            a fallback.

    Returns:
        The A/L coefficient as a ``float`` or ``None`` if it cannot be obtained.

    """
    if (conductivity_df is None) and (pellet_coeff is None):
        logger.warning('No conductivity CSV; and No pellet A/L')
        return None

    if conductivity_df is None:
        logger.info(f'No average 1/(cond*res) from conductivity CSV; using pellet A/L={pellet_coeff}')
        return pellet_coeff

    imp_name = impedance_file.name
    avg: float | None = extract_cond_resist_coeff_avg(conductivity_df)

    if avg is None:
        if pellet_coeff is None:
            logger.warning('No average 1/(cond*res) from conductivity CSV; and No pellet A/L')
        else:
            logger.info(f'No average 1/(cond*res) from conductivity CSV; using pellet A/L={pellet_coeff}')
        return pellet_coeff

    mask = conductivity_df[ConductivityColumn.IMP_FILE] == imp_name
    if not mask.any():
        logger.info(f'"{imp_name}" not in conductivity CSV; using average 1/(cond*res)={avg}')
        return avg

    row = conductivity_df.loc[mask].iloc[0]
    logger.info(f'Impedance file "{imp_name}" matched')
    res = pd.to_numeric(row[ConductivityColumn.RESISTIVITY], errors="coerce")
    cond = pd.to_numeric(row[ConductivityColumn.CONDUCTIVITY], errors="coerce")

    if pd.isna(res) or pd.isna(cond):
        logger.info(f'Could not convert to float. Using average 1/(cond*res)={avg}')
        return avg

    val = float(1.0 / (res * cond))
    logger.info(f'Conductivity={cond}, Resistivity={res}, Value=1/(cond*res)={val}')
    return val


def normalize_impedance_data(data: pd.DataFrame, coeff: float) -> pd.DataFrame:
    """Normalize impedance values by a scalar coefficient.

    The real and imaginary impedance columns are multiplied by ``coeff`` and
    the magnitude and phase columns are recomputed.

    Args:
        data (pd.DataFrame): Must contain ``'Re(Z)/Ohm'`` and ``'-Im(Z)/Ohm'``.
        coeff (float): Scalar factor applied to the real and imaginary columns.

    Returns:
        pd.DataFrame: DataFrame with normalized ``'Re(Z)/Ohm'`` and ``'-Im(Z)/Ohm'``
        and recalculated ``'|Z|/Ohm'`` and ``'Phase(Z)/deg'`` columns.

    """
    norm_data = data.copy()
    norm_data[['Re(Z)/Ohm', '-Im(Z)/Ohm']] = (norm_data[['Re(Z)/Ohm', '-Im(Z)/Ohm']] * coeff)
    # Delete the |Z| and Phase(Z) columns and recompute them
    norm_data.drop(columns=['|Z|/Ohm', 'Phase(Z)/deg'], inplace=True)
    return extract_and_calculate_missing_columns(norm_data)


def calc_pellet_normalization_coeff(
    *,
    area: str | float | None = None,
    diameter: str | float | None = None,
    thickness: str | float | None = None,
) -> float | None:
    """Compute the A/L normalization coefficient for a circular pellet.

    Exactly two of ``area``, ``diameter`` and ``thickness`` must be supplied.
    If ``area`` is missing but ``diameter`` is given, the area is derived from the
    diameter.  The reverse conversion is currently disabled.

    Args:
        area (str | float | None, optional):   Pellet cross‑sectional area.
        diameter (str | float | None, optional): Pellet diameter.
        thickness (str | float | None, optional): Pellet thickness (must be > 0).

    Returns:
        float | None: ``area / thickness`` when the inputs are valid, otherwise ``None``.

    """
    logger.info("Calculating pellet normalization coefficient")

    # str -> float
    def _to_float_or_none(v: str | float | None) -> float | None:
        if isinstance(v, str):
            val = pd.to_numeric([v], errors="coerce")[0]   # NaN on failure
            return None if pd.isna(val) else float(val)
        return v
    diameter = _to_float_or_none(diameter) if diameter else None
    area = _to_float_or_none(area) if area else None
    thickness = _to_float_or_none(thickness) if thickness else None

    # thickness is required; either area or diameter must be provided
    if thickness is None or (area is None and diameter is None):
        missing = [name for name, val in
                   zip(('area', 'diameter', 'thickness'),
                       (area, diameter, thickness), strict=True)
                   if val is None]
        logger.warning(f"Error: Insufficient parameters; missing={missing}")
        return None

    # area -> diameter conversion
    if area is None and diameter is not None:
        area = math.pi * (diameter / 2) ** 2

    # ---- Uncomment below to calculate diameter ----
    # elif diameter is None and area is not None:
    #     if area < 0:
    #         logger.warning(f"Error: area is negative (area={area})")
    #         return None
    #     diameter = 2 * math.sqrt(area / math.pi)

    # thickness must be present and positive
    if thickness is None or thickness <= 0:
        logger.warning(f"Error: Invalid thickness: must be a positive number, got {thickness!r}")
        return None

    # now area, thickness are guaranteed to be floats
    result = typing.cast(float, area) / thickness  # cast area to float for the type checker
    logger.info(f"A/L: area={area} / thickness={thickness} -> result={result}")
    return result


# ----------------------------------------------------------------------
# 4. Common processing & HTML output
# ----------------------------------------------------------------------
def create_combined_html(
    figures: dict,
    print_figures: dict | None,
    html_path: Path,
) -> None:
    """Write Plotly figures to a single HTML file.

    Args:
        figures: Mapping from titles to Plotly Figure objects.
        print_figures: Optional mapping for printable figures.
        html_path: Destination HTML file path.

    """
    with open(html_path, "w", encoding="utf-8") as f:
        # Insert a tag telling the browser the page is UTF‑8 (prevents garbled σ characters)
        f.write('<meta charset="utf-8">\n')
        # write the main figures
        for _title, fig in figures.items():
            if isinstance(fig, go.Figure):
                fig.write_html(f, full_html=False, include_plotlyjs="cdn")
            elif isinstance(fig, dict):
                fig['fig'].write_html(f, full_html=False, include_plotlyjs="cdn")
                f.write(df_to_html(fig['params']))
        # write printable figures inside a collapsible block, if any
        if print_figures:
            f.write("\n<details><summary>Impedance Plot for Export Image</summary>\n")
            for _title, fig in print_figures.items():
                if isinstance(fig, go.Figure):
                    fig.write_html(f, full_html=False, include_plotlyjs="cdn")
                elif isinstance(fig, dict):
                    fig['fig'].write_html(f, full_html=False, include_plotlyjs="cdn")
                    f.write(df_to_html(fig['params']))
            f.write("\n</details>\n")


def df_to_html(df: pd.DataFrame) -> str:
    """Convert a pandas DataFrame to an HTML table.

    The generated table follows a fixed style:

    - The first row is a header that shows the column names.
    - All following rows contain the data values.
    - The table tag includes ``border=1`` and CSS for margin, collapsed borders,
      and a width of 90 % (center‑aligned).
    - The header row has a light‑gray background (``#f2f2f2``).

    Args:
        df: The DataFrame to be converted. All columns are kept.

    Returns:
        str: An HTML string that represents the formatted table.

    """
    # Drop any extra columns if present; in this version we keep all columns
    df2 = df.copy()
    # Table opening tag + header row
    html = (
        '\n<table border="1" '
        'style="border-collapse:collapse; '
        'white-space:nowrap; font-size:small;">\n'
    )
    for col in df2.columns:
        html += f'<th>{col}</th>'
    html += '</tr>\n'
    # Data rows
    for _, row in df2.iterrows():
        html += '  <tr>'
        for cell in row:
            html += f'<td>{cell}</td>'
        html += '</tr>\n'
    # Table closing tag
    html += '</table>'
    return html


def initialize_config(
    base_temp_k: float = 300.0,
    reference_temp_c: float = 25.0,
) -> None:
    """Initialize the global configuration constants.

    Args:
        base_temp_k: Base temperature in Kelvin (default 300 K).
        reference_temp_c: Reference temperature in Celsius (default 25 °C).

    Raises:
        RuntimeError: If the configuration has already been set.

    """
    # Temperature definitions
    global CONST                     # noqa: PLW0603
    if isinstance(CONST, Constants) and (
        CONST.BASE_TEMP_K != 300.0 or CONST.REFERENCE_TEMP_C != 25.0  # noqa: PLR2004
    ):
        # Already set by user → re‑setting raises an exception
        msg = "Config is already set"
        raise RuntimeError(msg)

    # Overwrite with a new instance (None will not appear)
    CONST = Constants(BASE_TEMP_K=base_temp_k,
                      REFERENCE_TEMP_C=reference_temp_c)


# ----------------------------------------------------------------------
# 5. Integrated execution functions
# ----------------------------------------------------------------------
# 5-1. Conductivity data processing
def process_conductivity(
    csv_paths: dict[str, Path],
    csv_output_dir: Path,
    main_png_output_dir: Path,
    png_output_dir: Path,
) -> tuple[OrderedDict[str, Any], dict, dict, dict, pd.DataFrame | None]:
    """Process multiple conductivity CSV files and generate plots.

    Args:
        csv_paths: Mapping from sigma type to CSV file path.
        csv_output_dir: Directory for intermediate CSV outputs.
        main_png_output_dir: Directory for main PNG images.
        png_output_dir: Directory for auxiliary PNG images.

    Returns:
        Tuple containing:
            - Ordered dictionary of Plotly figures,
            - Dictionary of calculated DataFrames,
            - Fit results for log σ,
            - Fit results for log σ·T,
            - Total conductivity DataFrame (or None).

    """
    logger.info("Processing conductivity")
    figs, calc_dfs, fit_s, fit_st, total = {}, {}, {}, {}, None
    indivisual_order_list = []
    for sigma_type, csv_path in csv_paths.items():
        logger.info(f"conducrivity {sigma_type}")
        raw = load_conductivity_data(csv_path)
        calc = fill_missing_conductivity_data(raw)
        calc_dfs[sigma_type] = calc
        calc.to_csv(Path(csv_output_dir, f"{csv_path.stem}_calc.csv"),
                    index=False)
        fit_df = extract_conductivity_fitting_data(calc)
        fit_df.to_csv(Path(csv_output_dir, f"{csv_path.stem}_fit.csv"),
                      index=False)
        s_param, st_param = fit_conductivity_data(fit_df)
        fit_s[sigma_type], fit_st[sigma_type] = s_param, st_param
        if sigma_type == "total":
            total = calc
        # Individual plots per sigma type
        title_sigma_type = SIGMA_TYPE[sigma_type]['plot_title']
        for plot_type, param, xcol, ycol, _ylab, fit, fname, title in [
            # ----- Uncomment the following for plots without fitting. -----
            # ("log_st", st_param, ConductivityColumn.INV_T_1000,
            #  ConductivityColumn.LOG_SIGMA_T,
            #  f"log {SIGMA_CHAR}T (K S cm^-1)", False,
            #  f"conductivity_{sigma_type}_arrhenius_log_sigma_t.png",
            #  f"Conductivity {title_sigma_type} Arrhenius log {SIGMA_CHAR}T"),
            # ("log_s", s_param, ConductivityColumn.INV_T_1000,
            #  ConductivityColumn.LOG_SIGMA,
            #  f"log {SIGMA_CHAR} (S cm^-1)", False,
            #  f"conductivity_{sigma_type}_arrhenius_log_sigma.png",
            #  f"Conductivity {title_sigma_type} Arrhenius log {SIGMA_CHAR}"),

            ("fit_st", st_param, ConductivityColumn.INV_T_1000,
             ConductivityColumn.LOG_SIGMA_T,
             f"log {SIGMA_CHAR}T (K S cm^-1)", True,
             f"conductivity_{sigma_type}_arrhenius_fit_log_sigma_t.png",
             f"Conductivity {title_sigma_type} Arrhenius fit log {SIGMA_CHAR}T"),
            ("fit_s", s_param, ConductivityColumn.INV_T_1000,
             ConductivityColumn.LOG_SIGMA,
             f"log {SIGMA_CHAR} (S cm^-1)", True,
             f"conductivity_{sigma_type}_arrhenius_fit_log_sigma.png",
             f"Conductivity {title_sigma_type} Arrhenius fit log {SIGMA_CHAR}"),
        ]:
            if fit:
                indivisual_order_list.append(title)  # fit only added to HTML output
            plot_conductivity_indivisual(
                calc, param, sigma_type, plot_type, xcol, ycol, title,
                Path(png_output_dir, fname), fit, False)
            figs.update(create_arrhenius_plotly_indivisual(
                calc, param, sigma_type, plot_type, xcol, ycol, title,
                Path(png_output_dir, fname), fit, False))
    # Combined plots
    for plot_type, _, params, xcol, ycol, _xl, _yl, fit, logy, fname, title in [
        ("raw", None, None, ConductivityColumn.TEMP_K, ConductivityColumn.CONDUCTIVITY,
         "Temperature (K)", "Conductivity (S/cm)", False, True,
         "conductivity.png", "Conductivity"),
        ("log_s", "log_sigma", fit_s, ConductivityColumn.INV_T_1000,
         ConductivityColumn.LOG_SIGMA,
         "1000/T (K^-1)", f"log {SIGMA_CHAR} (S cm^-1)", False, False,
         "conductivity_arrhenius_log_sigma.png",
         f"Conductivity Arrhenius log {SIGMA_CHAR}"),
        ("log_st", "log_sigma_t", fit_st, ConductivityColumn.INV_T_1000,
         ConductivityColumn.LOG_SIGMA_T,
         "1000/T (K^-1)", f"log {SIGMA_CHAR}T (K S cm^-1)", False, False,
         "conductivity_arrhenius_log_sigma_t.png",
         f"Conductivity Arrhenius log {SIGMA_CHAR}T"),
        ("fit_s", "log_sigma", fit_s, ConductivityColumn.INV_T_1000,
         ConductivityColumn.LOG_SIGMA,
         "1000/T (K^-1)", f"log {SIGMA_CHAR} (S cm^-1)", True, False,
         "conductivity_arrhenius_fit_log_sigma.png",
         f"Conductivity Arrhenius fit log {SIGMA_CHAR}"),
        ("fit_st", "log_sigma_t", fit_st, ConductivityColumn.INV_T_1000,
         ConductivityColumn.LOG_SIGMA_T,
         "1000/T (K^-1)", f"log {SIGMA_CHAR}T (K S cm^-1)", True, False,
         "conductivity_arrhenius_fit_log_sigma_t.png",
         f"Conductivity Arrhenius fit log {SIGMA_CHAR}T"),
    ]:
        output_dir = (main_png_output_dir if plot_type == 'fit_st'
                      else png_output_dir)
        plot_conductivity_combined(calc_dfs, params, plot_type,
                                   xcol, ycol, title,
                                   Path(output_dir, fname), fit, logy)
        figs.update(create_arrhenius_plotly_combined(
            calc_dfs, params, plot_type, xcol, ycol, title,
            Path(png_output_dir, fname), fit, logy))
    # HTML display order
    order_list = [
        "Conductivity",
        f"Conductivity Arrhenius log {SIGMA_CHAR}T",
        f"Conductivity Arrhenius log {SIGMA_CHAR}",
    ]
    order_list.extend(indivisual_order_list)
    order_list.extend([
        f"Conductivity Arrhenius fit log {SIGMA_CHAR}T",
        f"Conductivity Arrhenius fit log {SIGMA_CHAR}",
    ])
    figs = OrderedDict((k, figs[k]) for k in order_list if k in figs)
    return figs, calc_dfs, fit_s, fit_st, total


# 5-2. Impedance data full processing
def process_impedance(
    imp_data: dict[str, tuple[pd.DataFrame | None, pd.DataFrame]],
    csv_output_dir: Path,
    png_output_dir: Path,
    main_png_output_dir: Path,
    save_to_mainimage: bool,
    total_conductivity_temp_map: pd.DataFrame | None = None,
    pellet_diameter: str | None = None,
    pellet_area: str | None = None,
    pellet_thickness: str | None = None,
) -> tuple[dict[str, pd.DataFrame | None], dict[str, go.Figure], dict[str, go.Figure]]:
    """Process a list of impedance files and generate plots.

    Args:
        imp_data: Dictionary mapping impedance file names to tuples of (header, data) DataFrames.
        csv_output_dir: Directory for CSV outputs.
        png_output_dir: Directory for auxiliary PNG images.
        main_png_output_dir: Directory for main PNG images.
        save_to_mainimage: Whether to store main images in the main directory.
        total_conductivity_temp_map: Optional DataFrame linking impedance filenames to temperatures,
          and extract_area_per_length()
        pellet_diameter: float | None,
        pellet_area: float | None,
        pellet_thickness: float | None,

    Returns:
        Tuple containing:
            - Mapping from file descriptor to header DataFrames,
            - Mapping from plot titles to interactive Plotly figures,
            - Mapping from plot titles to printable Plotly figures.

    """
    logger.info("Processing impedance")
    dfs: dict[str, pd.DataFrame] = {}
    dfs_norm: dict[str, pd.DataFrame] = {}
    imp_header: dict[str, pd.DataFrame | None] = {}
    figs: dict[str, go.Figure] = {}
    print_figs: dict[str, go.Figure] = {}

    # do_normalization=True if A/L comes from pellet info or avg conductivity
    pellet_coeff: float | None = calc_pellet_normalization_coeff(
        diameter=pellet_diameter,
        area=pellet_area,
        thickness=pellet_thickness,
    )
    cond_resist_coeff_avg: float | None = extract_cond_resist_coeff_avg(total_conductivity_temp_map)
    do_normalization: bool = (
        total_conductivity_temp_map is not None and cond_resist_coeff_avg is not None) or (pellet_coeff is not None)
    if not do_normalization:
        logger.warning('NORMALIZATION SKIPPED: no avg A/L from conductivity TOTAL csv and no pellet A/L.')

    for imp_name, (header, data) in imp_data.items():

        if data is None:
            continue

        data.to_csv(Path(csv_output_dir, f"{imp_name}_data.csv"), index=False)

        calced_data = data
        calced_data.to_csv(Path(csv_output_dir, f"{imp_name}_calc.csv"), index=False)

        temperature = (
            None if total_conductivity_temp_map is None
            else find_temperature_for_impedance_file(total_conductivity_temp_map, Path(imp_name))
        )

        suffix = f" {temperature}" if temperature else ""

        dfs[f"{imp_name}{suffix}"] = calced_data
        imp_header[imp_name] = header

        normalization_coeff = extract_normalization_coeff(
            total_conductivity_temp_map,
            Path(imp_name),
            pellet_coeff=pellet_coeff,
        )

        if normalization_coeff is not None:
            norm_data = normalize_impedance_data(calced_data, normalization_coeff)
            norm_data.to_csv(
                Path(csv_output_dir, f"{imp_name}_norm.csv"),
                index=False,
            )
            dfs_norm[f"{imp_name}{suffix}"] = norm_data
    cole_cole_output_dir: Path = main_png_output_dir if save_to_mainimage else png_output_dir
    plot_cole_cole(dfs, Path(cole_cole_output_dir, "cole_cole.png"))
    figs["Cole-Cole"], print_figs["Cole-Cole"] = create_cole_cole_plotly(dfs)
    plot_bode_magnitude(dfs, Path(png_output_dir, "bode_magnitude.png"))
    figs["Bode |Z|"], print_figs["Bode |Z|"] = create_bode_magnitude_plotly(dfs)
    plot_bode_phase(dfs, Path(png_output_dir, "bode_phase.png"))
    figs["Bode Phase(Z)"], print_figs["Bode Phase(Z)"] = create_bode_phase_plotly(dfs)
    plot_bode_phase(
        dfs,
        Path(png_output_dir, "bode_phase_inverted.png"),
        invert_phase=True,
    )

    figs["Bode Phase(Z) (inverted)"], print_figs[
        "Bode Phase(Z) (inverted)"
    ] = create_bode_phase_plotly(dfs, invert_phase=True)
    if do_normalization:  # conductivity_total.csvのA/L平均値が取れた | ペレット情報からA/Lが取れた
        plot_cole_cole(
            dfs_norm,
            Path(png_output_dir, "cole_cole_normalized.png"),
            is_normalized=True,
        )
        figs["Cole-Cole (normalized)"], print_figs[
            "Cole-Cole (normalized)"
        ] = create_cole_cole_plotly(dfs_norm, is_normalized=True)
        plot_bode_magnitude(
            dfs_norm,
            Path(png_output_dir, "bode_magnitude_normalized.png"),
            is_normalized=True,
        )
        figs["Bode |Z| (normalized)"], print_figs[
            "Bode |Z| (normalized)"
        ] = create_bode_magnitude_plotly(dfs_norm, is_normalized=True)
        plot_bode_phase(
            dfs_norm,
            Path(png_output_dir, "bode_phase_normalized.png"),
            is_normalized=True,
        )
        figs["Bode Phase(Z) (normalized)"], print_figs[
            "Bode Phase(Z) (normalized)"
        ] = create_bode_phase_plotly(dfs_norm, is_normalized=True)
        plot_bode_phase(
            dfs_norm,
            Path(png_output_dir, "bode_phase_inverted_normalized.png"),
            invert_phase=True,
            is_normalized=True,
        )
        figs["Bode Phase(Z) (inverted) (normalized)"], print_figs[
            "Bode Phase(Z) (inverted) (normalized)"
        ] = create_bode_phase_plotly(
            dfs_norm,
            invert_phase=True,
            is_normalized=True,
        )
    return imp_header, figs, print_figs
