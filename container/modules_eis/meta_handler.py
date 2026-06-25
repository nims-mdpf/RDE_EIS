from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from rdetoolkit import rde2util
from rdetoolkit.models.rde2types import MetaType, RepeatedMetaType
from rdetoolkit.rde2util import CharDecEncoding
from rdetoolkit.rdelogger import get_logger

from modules_eis.interfaces import IMetaParser

logger = get_logger('eis')


class MetaParser(IMetaParser[MetaType]):
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

    def save_meta(
        self,
        save_path: Path,
        meta: rde2util.Meta,
        *,
        const_meta_info: MetaType | None = None,
        repeated_meta_info: RepeatedMetaType | None = None,
    ) -> Any:
        """Save parsed metadata to a file using the provided Meta object.

        Args:
            save_path (Path): The path where the metadata file will be saved.
            meta (rde2util.Meta): Meta object used for saving the metadata.
            const_meta_info (MetaType | None, optional): Constant metadata information.
                    Defaults to None.
            repeated_meta_info (RepeatedMetaType | None, optional): Repeated metadata information.
                    Defaults to None.

        Returns:
            Any: The result of the Meta object's writefile method.

        """
        if const_meta_info is None:
            const_meta_info = self.const_meta_info
        if repeated_meta_info is None:
            repeated_meta_info = self.repeated_meta_info

        if const_meta_info is not None:
            meta.assign_vals(const_meta_info)
        if repeated_meta_info is not None:
            meta.assign_vals(repeated_meta_info)

        return meta.writefile(str(save_path))

    def parse_conductivity(self, data: dict[str, Any]) -> dict:
        """Extract conductivity information from a DataFrame.

        Args:
            data: A pandas DataFrame containing raw conductivity data. It
                should be convertible to the nested‑dictionary format.

        Returns:
            dict: A flat mapping where keys are dot‑separated descriptors
                (e.g., ``"conductivity.total.activation_energy_ev.log_sigma"``)
                and values are the corresponding scalar values.

        """
        needed = {
            "activation_energy_ev",
            "activation_energy_kjmol",
            "conductivity_300k",
            "preexponetial_term",
            "approximate_formula",
        }

        def _walk(d: Any, path: list, out: dict) -> None:
            """Recursively traverse the dictionary and save only when a leaf entry is in NEEDED."""
            if isinstance(d, dict):
                for k, v in d.items():
                    _walk(v, path + [k], out)
            elif path and path[-1] in needed:
                out[tuple(path)] = d

        tmp: dict = {}
        _walk(data, [], tmp)

        flat: dict = {}
        for p, v in tmp.items():
            leaf = p[-1]
            group = p[0]
            middle = ".".join(p[1:-1])
            key = ".".join(filter(None, ["conductivity", middle, leaf, group]))
            flat[key] = v
        return flat

    def add_temperature(self, imp_data: dict, cond_df: pd.DataFrame) -> None:
        """Add temperature information to an impedance metadata dictionary.

        The function looks up temperature values (both °C and K) that were
        calculated during the conductivity processing step and attaches them
        to the impedance metadata (``imp_data``) based on a common “impedance
        file” identifier.  The operation mutates ``imp_data`` in place.

        Args:
            imp_data (dict): The impedance metadata dictionary that will receive
                two new keys:
                * ``impedance.temperature_c``
                * ``impedance.temperature_k``
                The values are lists aligned with the existing
                ``impedance.file`` entries.
            cond_df (DataFrame): The conductivity result dictionary produced by
                the conductivity calculation step.  It must contain a
                ``'total'`` -> ``'calc'`` DataFrame with columns
                ``'Impedance File'``, ``'Temperature (C)'`` and ``'Temperature (K)'``.

        Returns:
            None

        Note:
            If the required ``'Impedance File'`` column is missing from the
            conductivity DataFrame, the function exits early without modifying
            ``imp_data``.

        """
        # cond_df = calc_cond_data['total']['calc']
        if "Impedance File" not in cond_df.columns:
            return

        def _clean_series(s: pd.Series) -> pd.Series:
            return s.apply(lambda v: None if pd.isna(v) or (isinstance(v, str) and v.strip() == "") else v)

        temp_c_map = dict(zip(
            cond_df["Impedance File"],
            _clean_series(cond_df["Temperature (C)"]),
            strict=False,
        ))
        temp_k_map = dict(zip(
            cond_df["Impedance File"],
            _clean_series(cond_df["Temperature (K)"]),
            strict=False,
        ))

        imp_data["impedance.temperature_c"] = [temp_c_map.get(f) for f in imp_data["impedance.file"]]
        imp_data["impedance.temperature_k"] = [temp_k_map.get(f) for f in imp_data["impedance.file"]]

    def inject_pellet_info_from_invoice(
        self,
        meta_info: MetaType,
        invoice_org_path: Path,
    ) -> None:
        """Populate pellet‑related fields in ``meta_info`` from an invoice JSON file.

        The method attempts to read the JSON file located at ``invoice_org_path``.
        Because the file may have been written with an unknown text encoding,
        :class:`CharDecEncoding` is used to detect the correct encoding before
        reading.  The JSON structure is expected to contain a top‑level ``"custom"``
        object that holds the optional keys ``pellet.diameter``, ``pellet.area``,
        and ``pellet.thickness``.  If a key is present and its value is a string,
        the stripped string is stored in ``meta_info`` under the same key name.
        Missing keys or non‑string values are stored as an empty string.

        Args:
            meta_info (MetaType): A mutable mapping (usually ``dict``) that will be
                enriched with the pellet information.  The function updates the
                mapping in place; no value is returned.
            invoice_org_path (Path): Path to the original invoice file in JSON
                format.  The file may be encoded in any text encoding; the
                function automatically detects it.

        Returns:
            None

        Raises:
            FileNotFoundError: If ``invoice_org_path`` does not exist.
            json.JSONDecodeError: If the file cannot be parsed as valid JSON.
            UnicodeDecodeError: If the detected encoding is incorrect and the
                file cannot be decoded.

        Note:
            The invoice schema is not strictly validated—only the ``custom``
            section and the three pellet fields are inspected.  This method is
            deliberately tolerant: any missing or malformed field results in an
            empty string being written to ``meta_info`` rather than raising an
            exception.

        """
        enc = CharDecEncoding.detect_text_file_encoding(invoice_org_path)
        data = json.loads(invoice_org_path.read_text(encoding=enc))
        diameter = (data.get("custom") or {}).get("pellet.diameter")
        meta_info["pellet.diameter"] = diameter.strip() if isinstance(diameter, str) else ""
        area = (data.get("custom") or {}).get("pellet.area")
        meta_info["pellet.area"] = area.strip() if isinstance(area, str) else ""
        thickness = (data.get("custom") or {}).get("pellet.thickness")
        meta_info["pellet.thickness"] = thickness.strip() if isinstance(thickness, str) else ""
