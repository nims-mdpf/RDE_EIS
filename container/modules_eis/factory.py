from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from rdetoolkit.exceptions import StructuredError

from modules_eis.Biologic.mpt.inputfile_handler import FileReader as mptFileReader
from modules_eis.Biologic.mpt.meta_handler import MetaParser as mptMetaParser
from modules_eis.custom.txt.inputfile_handler import FileReader as txtFileReader
from modules_eis.custom.txt.meta_handler import MetaParser as txtMetaParser
from modules_eis.inputfile_handler import FileReader as EisFileReader
from modules_eis.meta_handler import MetaParser as EisMetaParser
from modules_eis.Scribner.z.inputfile_handler import FileReader as zFileReader
from modules_eis.Scribner.z.meta_handler import MetaParser as zMetaParser

EIS_MANUFACTURER_CLASS_MAPPING: dict[str, tuple[type[EisFileReader], type[EisMetaParser]]] = {
    "Biologic": (mptFileReader, mptMetaParser),
    "Scribner": (zFileReader, zMetaParser),
    "Custom": (txtFileReader, txtMetaParser),
}


class EisFactory:
    """Obtain a variety of data for use in the EIS's Structured processing."""

    def __init__(
        self,
        file_reader: EisFileReader,
        meta_parser: EisMetaParser,
    ):
        self.file_reader = file_reader
        self.meta_parser = meta_parser

    @staticmethod
    def get_config(path_tasksupport: Path) -> Any:
        """Obtain a variety of data.

        Obtain configuration data.

        Args:
            rawfile (Path): measurement file.
            path_tasksupport (Path): tasksupport path.

        Returns:
            config (Any): config data.

        """
        rdeconfig_file = path_tasksupport.joinpath("rdeconfig.yaml")

        # Get the graph scale of the representative image from rdeconfig.yaml.
        if not rdeconfig_file.exists():
            err_msg = f"File not found: {rdeconfig_file}"
            raise StructuredError(err_msg)
        try:
            with open(rdeconfig_file) as file:
                config = yaml.safe_load(file)
        except Exception:
            err_msg = f"Invalid configuration file: {rdeconfig_file}"
            raise StructuredError(err_msg) from None

        return config

    @staticmethod
    def get_objects(_path_tasksupport: Path, config: dict) -> EisFactory:
        """Obtain classes based on manufacturer only (extension ignored)."""
        manufacturer: str = config["eis"]["manufacturer"]

        try:
            file_reader_cls, meta_parser_cls = EIS_MANUFACTURER_CLASS_MAPPING[manufacturer]
        except KeyError:
            msg = f"Unsupported manufacturer: {manufacturer}"
            raise StructuredError(msg) from None
        return EisFactory(
            file_reader_cls(),
            meta_parser_cls(),
        )
