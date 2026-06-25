from __future__ import annotations

import io
from pathlib import Path

import numpy as np
import pandas as pd
from rdetoolkit.rdelogger import get_logger

from modules_eis.inputfile_handler import FileReader as zFileReader

logger = get_logger('eis')


class FileReader(zFileReader):
    """Template class for reading and parsing input data.

    This class serves as a template for the development team to read and parse input data.
    It implements the IInputFileParser interface. Developers can use this template class
    as a foundation for adding specific file reading and parsing logic based on the project's
    requirements.

    Args:
        srcpaths (tuple[Path, ...]): Paths to input source files.

    Returns:
        Any: The loaded data from the input file(s).

    Example:
        file_reader = FileReader()
        loaded_data = file_reader.read(('file1.txt', 'file2.txt'))
        file_reader.to_csv('output.csv')

    """

    def get_impedance_file_paths(self, directory_path: Path) -> list[Path]:
        """Collect impedance files with supported extensions from a directory.

        Supported extensions are `.z`.

        Args:
            directory_path: Directory to search for impedance files.

        Returns:
            List of Path objects for each matching file.

        """
        extensions = {".z"}
        return [
            p for p in sorted(directory_path.glob("*"))
            if p.is_file() and p.suffix.lower() in extensions
        ]

    def load_impedance_file(self, file_path: Path) -> list[str]:
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
        self,
        lines: list[str],
        file_name: str,
    ) -> tuple[pd.DataFrame | None, pd.DataFrame | None]:
        """Separate the header and data sections of an impedance file.

        Args:
            lines: List of lines read from the impedance file.
            file_name: Name of the impedance file.

        Returns:
            A tuple `(header_df, data_df)` where `header_df` contains the header
            information and `data_df` contains the numeric data.

        """
        i_start: int = 0
        i_end: int = 0
        tab_sep: bool = False
        find_data: bool = False
        for i, line in enumerate(lines):
            if ("Z'(a)" in line and "Z''(b)" in line) \
                    or ("Z'(a)" in line and "Z\"(b)" in line):
                i_start = i
                tab_sep = "\t" in line
                find_data = True
            if "End Comments" in line:
                i_end = i
        skip_rows = list(range(i_start)) + [i_end]

        df: pd.DataFrame | None = None
        df_header: pd.DataFrame | None = None

        if not find_data:
            msg = (
                "Impedance header not found "
                f"(file={file_name}). "
                "Check file format or column names."
            )
            logger.error(msg)
            raise ValueError(msg)

        try:
            txt = "".join(lines)
            buffer = io.StringIO(txt)
            sep = "\t" if tab_sep else r"\s+"

            df = pd.read_csv(
                buffer,
                sep=sep,
                skiprows=skip_rows,
                header=0,
                engine="python",
            )

        except Exception as e:
            msg = f"CSV parse failed (file={file_name}): {e}"
            logger.exception(msg)
            raise ValueError(msg) from e

        header_rows = lines[:i_start]
        df_header = pd.DataFrame(data=[row.strip() for row in header_rows])

        return df_header, df

    def extract_and_calculate_missing_columns(
            self,
            experiment_data: pd.DataFrame,
    ) -> pd.DataFrame:
        """Extract required columns and calculate missing impedance quantities."""
        df_exp = experiment_data.copy()

        df_calc = pd.DataFrame(columns=[
            "freq/Hz",
            "Re(Z)/Ohm",
            "-Im(Z)/Ohm",
            "|Z|/Ohm",
            "Phase(Z)/deg",
        ])

        column_map = {
            "freq/Hz": ["Freq(Hz)", "  Freq(Hz)", "Freq.(Hz)"],
            "Re(Z)/Ohm": ["Z'(a)"],
            "-Im(Z)/Ohm": ["Z''(b)", 'Z"(b)'],
        }

        for target_col, source_candidates in column_map.items():
            for source_col in source_candidates:
                if source_col in df_exp.columns:
                    values = df_exp[source_col]

                    if target_col == "-Im(Z)/Ohm":
                        values = -1.0 * values

                    df_calc[target_col] = values
                    break

        # Calculate magnitude and phase when missing
        for i in range(len(df_calc)):
            re_z = df_calc.at[i, "Re(Z)/Ohm"]
            im_z = df_calc.at[i, "-Im(Z)/Ohm"]

            z = complex(re_z, -im_z)

            if pd.isna(df_calc.at[i, "|Z|/Ohm"]):
                df_calc.at[i, "|Z|/Ohm"] = np.abs(z)

            if pd.isna(df_calc.at[i, "Phase(Z)/deg"]):
                df_calc.at[i, "Phase(Z)/deg"] = np.angle(z, deg=True)

        logger.info(
            f"calculated df summary:\n"
            f"{df_calc.to_string(max_rows=5, max_cols=5)}",
        )

        return df_calc
