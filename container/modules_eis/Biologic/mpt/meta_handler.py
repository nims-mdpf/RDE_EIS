from __future__ import annotations

import re

import pandas as pd
from rdetoolkit.models.rde2types import MetaType, RepeatedMetaType
from rdetoolkit.rdelogger import get_logger

from modules_eis.meta_handler import MetaParser as mptMetaParser

logger = get_logger('eis')


class MetaParser(mptMetaParser):
    """Template class for parsing and saving metadata.

    This class serves as a template for the development team to parse and save metadata. It implements
    the IMetaParser interface. Developers can use this template class as a foundation for adding
    specific parsing and saving logic for metadata based on the project's requirements.

    Args:
        data (MetaType): The metadata to be parsed and saved.

    Returns:
        tuple[MetaType, MetaType]: A tuple containing the parsed constant and repeated metadata.

    Example:
        meta_parser = MetaParser()
        parsed_const_meta, parsed_repeated_meta = meta_parser.parse(data)
        meta_obj = rde2util.Meta(metaDefFilePath='meta_definition.json')
        saved_info = meta_parser.save_meta('saved_meta.json', meta_obj,
                                        const_meta_info=parsed_const_meta,
                                        repeated_meta_info=parsed_repeated_meta)

    """

    def __init__(self) -> None:
        self.const_meta_info: MetaType | None = None
        self.repeated_meta_info: RepeatedMetaType | None = None
        self.IMPEDANCE_META_KEYS = [
            "impedance.file",
            "impedance.temperature_k",
            "impedance.temperature_c",
            "impedance.mpt.acquisition_started_on",
            "impedance.mpt.technique_started_on",
            "impedance.mpt.potential_control",
            "impedance.mpt.ewe_ctrl_range_min",
            "impedance.mpt.ewe_ctrl_range_max",
            "impedance.mpt.ewe_I_filtering",
            "impedance.mpt.device",
            "impedance.mpt.software",
        ]

    def parse(
        self,
        cond_meta: dict,
        imp_meta: dict[str, pd.DataFrame | None],
        calc_total_df: pd.DataFrame | None,
    ) -> tuple[MetaType, RepeatedMetaType | None]:
        """Parse conductivity and (optionally) impedance metadata.

        Args:
            cond_meta: Raw conductivity metadata dictionary.
            imp_meta: Raw impedance metadata dictionary (may be empty/None).
            calc_total_df: Optional DataFrame used to add temperature info to
                the impedance data.

        Returns:
            tuple[MetaType, RepeatedMetaType]: ``(const_meta_info,
            repeated_meta_info)`` where *const_meta_info* is the flattened
            conductivity dict and *repeated_meta_info* is the processed
            impedance dict (or an empty dict if ``imp_meta`` is falsy).

        """
        self.const_meta_info = self.parse_conductivity(cond_meta)
        if imp_meta:
            parsed_imp_meta = self.parse_impedance(imp_meta)
            if cond_meta and calc_total_df is not None:
                self.add_temperature(parsed_imp_meta, calc_total_df)
            self.repeated_meta_info = parsed_imp_meta

        return self.const_meta_info, self.repeated_meta_info

    def parse_impedance(self, data: dict[str, pd.DataFrame | None]) -> dict:
        """Extract impedance‑related metadata from a list of header strings.

        This method is a thin wrapper around :meth:`_extract_impedance_metadata`.
        It receives the raw header data (as a list of strings) and returns a
        dictionary whose keys are the predefined metadata fields
        (``self.IMPEDANCE_META_KEYS``) and whose values are lists containing the
        extracted information for each file.

        Args:
            data (list[str]): A list where each element is the header text of a
                single impedance measurement file.  The header may contain lines
                such as “Acquisition started on : …”, “Potential control : …”, etc.

        Returns:
            dict: A mapping from each metadata key to a list of extracted values.
                The length of each list equals the number of input files.  Missing
                values are represented by an empty string.

        Note:
            The heavy‑lifting is performed by the private method
            :meth:`_extract_impedance_metadata`.  This wrapper exists mainly for
            a clean public interface and to keep the calling code concise.

        """
        meta: dict[str, list[str]] = {
            key: [] for key in self.IMPEDANCE_META_KEYS
        }

        prefix_map = {
            "Acquisition started on : ": "impedance.mpt.acquisition_started_on",
            "Technique started on : ": "impedance.mpt.technique_started_on",
            "Potential control : ": "impedance.mpt.potential_control",
            "Device : ": "impedance.mpt.device",
        }

        for fname, header_df in data.items():
            if header_df is None or header_df.empty:
                continue

            temp: dict[str, str] = dict.fromkeys(self.IMPEDANCE_META_KEYS, "")
            temp["impedance.file"] = fname

            for line in header_df.iloc[:, 0].astype(str):
                self._parse_impedance_line(line.strip(), temp, prefix_map)

            for k in self.IMPEDANCE_META_KEYS:
                meta[k].append(temp.get(k, ""))

        logger.info("Extracted impedance metadata")
        return meta

    def _parse_impedance_line(
        self,
        line: str,
        temp: dict[str, str],
        prefix_map: dict[str, str],
    ) -> None:
        """Parse a single header line."""
        for prefix, key in prefix_map.items():
            if line.startswith(prefix):
                temp[key] = line[len(prefix):]
                return

        if line.startswith("Ewe ctrl range : "):
            self._parse_ewe_ctrl_range(line, temp)
            return

        if "Ewe,I filtering : " in line or "Ewe I filtering : " in line:
            self._parse_filtering(line, temp)
            return

        if line.startswith("Device : "):
            temp["impedance.mpt.device"] = line.replace("Device : ", "")
            return

        if line.endswith("(software)"):
            temp["impedance.mpt.software"] = line.replace("(software)", "").strip()
            return

    def _parse_ewe_ctrl_range(self, line: str, temp: dict[str, str]) -> None:
        m = re.search(
            r"min\s*=\s*([+-]?\d+\.?\d*)\s*V.*"
            r"max\s*=\s*([+-]?\d+\.?\d*)\s*V",
            line,
        )
        if m:
            temp["impedance.mpt.ewe_ctrl_range_min"] = m.group(1)
            temp["impedance.mpt.ewe_ctrl_range_max"] = m.group(2)

    def _parse_filtering(self, line: str, temp: dict[str, str]) -> None:
        m = re.search(r"(\d+\.?\d*)\s*kHz", line)
        if not m:
            m = re.search(r":\s*(\d+\.?\d*)", line)
        if m:
            temp["impedance.mpt.ewe_I_filtering"] = m.group(1)
