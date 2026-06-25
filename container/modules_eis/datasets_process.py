from __future__ import annotations

from pathlib import Path
from typing import Any

from rdetoolkit.config import load_config
from rdetoolkit.errors import catch_exception_with_message
from rdetoolkit.models.rde2types import RdeInputDirPaths, RdeOutputResourcePath
from rdetoolkit.rde2util import Meta, read_from_json_file
from rdetoolkit.rdelogger import get_logger

from modules_eis import eisdata
from modules_eis.factory import EisFactory


@catch_exception_with_message()
def dataset(
    srcpaths: RdeInputDirPaths,
    resource_paths: RdeOutputResourcePath,
) -> None:
    """Execute structured processing based on EIS manufacturer."""
    logger = get_logger('eis', file_path=Path(resource_paths.struct, 'structured_log.txt'))
    logger.info("Application started.")
    config = EisFactory.get_config(srcpaths.tasksupport)
    module = EisFactory.get_objects(srcpaths.tasksupport, config)

    figs: dict[str, Any] = {}
    print_figs: dict[str, Any] = {}
    total_calc_df = None
    fit_s: dict = {}
    fit_st: dict = {}
    raw_files_directory: Path = resource_paths.nonshared_raw

    # config
    config = load_config(srcpaths.tasksupport)
    if config.system.save_raw or not config.system.save_nonshared_raw:
        raw_files_directory = resource_paths.raw
    eisdata.initialize_config(base_temp_k=300.0, reference_temp_c=25.0)

    # pellet metadata from invoice.json
    invoice_obj = read_from_json_file(resource_paths.invoice_org)
    pellet_diameter = invoice_obj.get("custom", "").get("pellet.diameter")
    pellet_area = invoice_obj.get("custom", "").get("pellet.area")
    pellet_thickness = invoice_obj.get("custom", "").get("pellet.thickness")

    # unzip
    module.file_reader.get_unzipped_filepaths(raw_files_directory)

    # conductivity
    exists_conductivity_data: bool = False
    csv_paths: dict[str, Path] = eisdata.get_conductivity_file_paths(raw_files_directory)
    if 'total' in csv_paths and csv_paths['total']:
        exists_conductivity_data = True
    else:
        logger.info("Conductivity TOTAL data file not found - skipping conductivity data structuring.")
    if exists_conductivity_data:
        cond_figs, _calc_dfs, fit_s, fit_st, total = eisdata.process_conductivity(
            csv_paths, resource_paths.struct, resource_paths.main_image, resource_paths.other_image,
        )
        figs.update(cond_figs)
        total_calc_df = total

    # impedance
    imp_header: dict = {}
    save_to_mainimage: bool = not exists_conductivity_data
    exists_impedance_data: bool = False
    imp_paths = module.file_reader.get_impedance_file_paths(raw_files_directory)

    imp_data = {}
    if imp_paths:
        exists_impedance_data = True
    if exists_impedance_data:
        for imp_path in imp_paths:
            lines = module.file_reader.load_impedance_file(imp_path)
            header, data = module.file_reader.split_impedance_header_and_data(lines, file_name=imp_path.name)
            if data is None:
                continue
            data = module.file_reader.extract_and_calculate_missing_columns(data)
            imp_data[imp_path.name] = (header, data)

        imp_header, imp_figs, imp_print_figs = eisdata.process_impedance(
            imp_data,
            resource_paths.struct,
            resource_paths.other_image,
            resource_paths.main_image,
            save_to_mainimage,
            total_calc_df,
            pellet_diameter,
            pellet_area,
            pellet_thickness,
        )

        figs.update(imp_figs)
        print_figs.update(imp_print_figs)

    if not exists_conductivity_data and not exists_impedance_data:
        logger.info("No structured processing. Only register the file (if it exists).")
        return

    # html
    eisdata.create_combined_html(figs, print_figs, Path(resource_paths.struct, 'eisdata.html'))

    # metadata
    cond_meta = {'log_sigma': fit_s, 'log_sigma_t': fit_st}
    const_meta_info, repeated_meta_info = module.meta_parser.parse(cond_meta, imp_header, total_calc_df)
    if resource_paths.invoice_org.exists():
        module.meta_parser.inject_pellet_info_from_invoice(const_meta_info, resource_paths.invoice_org)
    module.meta_parser.save_meta(
        resource_paths.meta.joinpath("metadata.json"),
        Meta(srcpaths.tasksupport.joinpath("metadata-def.json")),
        const_meta_info=const_meta_info,
        repeated_meta_info=repeated_meta_info,
    )

    logger.info("Application terminated.")
