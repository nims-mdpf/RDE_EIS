from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar

import pandas as pd
from rdetoolkit.models.rde2types import MetaType, RepeatedMetaType
from rdetoolkit.rde2util import Meta
from rdetoolkit.rdelogger import get_logger

logger = get_logger('eis')

T = TypeVar("T")


class IInputFileParser(ABC):
    """Abstract base class (interface) for input file parsers.

    This interface defines the contract that input file parser
    implementations must follow. The parsers are expected to read files
    from a specified path, parse the contents of the files, and provide
    options for saving the parsed data.

    Methods:
        read: A method expecting a file path and responsible for reading a file.

    Example implementations of this interface could be for parsing files
    of different formats like CSV, Excel, JSON, etc.

    """

    @abstractmethod
    def get_zipfiles(self, directory: Path) -> list[Path]:
        """Retrieve ZIP files in a directory.

        Return a list of unique ZIP file paths found in the given directory.

        Args:
            self (Any): Instance reference.
            directory (Path): Directory to search for ZIP archives.

        Returns:
            list[Path]: Unique Path objects for each discovered ZIP file.

        """
        raise NotImplementedError

    @abstractmethod
    def unpacked(self, zip_file: Path) -> list[Path]:
        """Extract contents of a ZIP file.

        Extract a ZIP archive to a subdirectory and return file paths.

        Args:
            self (Any): Instance reference.
            zip_file (Path): Path to the ZIP file to extract.

        Returns:
            list[Path]: Paths of all extracted files (empty list on error).

        """
        raise NotImplementedError

    @abstractmethod
    def get_impedance_file_paths(self, directory_path: Path) -> list[Path]:
        """Get impedance file paths from a directory.

        Search for impedance files in the specified directory and return their paths.

        Args:
            self (Any): Instance reference.
            directory_path (Path): Directory to search for impedance files.

        Returns:
            list[Path]: Paths of all discovered impedance files.

        """
        raise NotImplementedError

    @abstractmethod
    def load_impedance_file(self, file_path: Path) -> list[str]:
        """Load an impedance file and return its lines.

        Args:
            file_path: Path to the impedance file.

        Returns:
            List of strings, each representing a line in the file.

        """
        raise NotImplementedError

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
        raise NotImplementedError

    def extract_and_calculate_missing_columns(
            self, experiment_data: pd.DataFrame) -> pd.DataFrame:
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
        raise NotImplementedError


class IMetaParser(ABC, Generic[T]):
    """Abstract base class (interface) for meta information parsers.

    This interface defines the contract that meta information parser
    implementations must follow. The parsers are expected to save the
    constant and repeated meta information to a specified path.

    Method:
        save_meta: Saves the constant and repeated meta information to a specified path.
        parse: This method returns two types of metadata: const_meta_info and repeated_meta_info.

    """

    @abstractmethod
    def parse(
        self,
        cond_meta: dict,
        imp_meta: dict[str, pd.DataFrame | None],
        calc_total_df: pd.DataFrame | None,
    ) -> tuple[MetaType, RepeatedMetaType | None]:
        """Parse."""
        raise NotImplementedError

    @abstractmethod
    def save_meta(
        self,
        save_path: Path,
        meta: Meta,
        *,
        const_meta_info: MetaType | None = None,
        repeated_meta_info: RepeatedMetaType | None = None,
    ) -> Any:
        """Save the constant and repeated meta information to a specified path.

        Args:
            save_path (Path): The path where the meta information will be saved.
            meta (Meta): The meta information to be saved.
            const_meta_info (MetaType, optional): Constant meta information. Defaults to None.
            repeated_meta_info (RepeatedMetaType, optional): Repeated meta information. Defaults to None.

        """
        raise NotImplementedError
