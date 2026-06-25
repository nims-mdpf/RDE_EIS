from __future__ import annotations

import zipfile
from pathlib import Path

from rdetoolkit.rdelogger import get_logger

from modules_eis.interfaces import IInputFileParser

logger = get_logger('eis')


class FileReader(IInputFileParser):
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

    def get_zipfiles(self, directory: Path) -> list[Path]:
        """Retrieve ZIP files in a directory.

        Return a list of unique ZIP file paths found in the given directory.

        Args:
            self (Any): Instance reference.
            directory (Path): Directory to search for ZIP archives.

        Returns:
            list[Path]: Unique Path objects for each discovered ZIP file.

        """
        zip_files = []

        # Basic ZIP file search
        zip_files.extend(directory.glob("*.zip"))
        zip_files.extend(directory.glob("*.ZIP"))

        # Recursive search
        zip_files.extend(directory.rglob("*.zip"))

        # Remove duplicates
        unique_zip_files = list(set(zip_files))

        logger.info(f"Found {len(unique_zip_files)} ZIP files:")
        for zip_file in unique_zip_files:
            logger.info(f"  - {zip_file}")

        return unique_zip_files

    def unpacked(self, zip_file: Path) -> list[Path]:
        """Extract contents of a ZIP file.

        Extract a ZIP archive to a subdirectory and return file paths.

        Args:
            self (Any): Instance reference.
            zip_file (Path): Path to the ZIP file to extract.

        Returns:
            list[Path]: Paths of all extracted files (empty list on error).

        """
        extracted_files = []
        extract_dir = zip_file.parent / f"{zip_file.stem}_extracted"
        extract_dir.mkdir(exist_ok=True)

        try:
            with zipfile.ZipFile(zip_file, "r") as zf:
                zf.extractall(extract_dir)

                for file in extract_dir.rglob("*"):
                    if file.is_file():
                        extracted_files.append(file)

        except zipfile.BadZipFile:
            logger.exception(f"Invalid ZIP file: {zip_file}")
            raise

        logger.info(f"✓ Extraction complete: {len(extracted_files)} files")
        return extracted_files

    def get_unzipped_filepaths(self, dir_path: str | Path) -> list[Path]:
        """Collect and move files extracted from ZIP archives in a directory.

        Args:
            self (Any): Instance reference.
            dir_path (str | Path): Directory that holds ZIP files to process.

        Returns:
            list[Path]: Paths of all files moved to *dir_path* after extraction.

        """
        all_extracted_paths: list[Path] = []
        seen_filenames: set[str] = set()
        base_dir = Path(dir_path)

        zip_files = self.get_zipfiles(base_dir)

        for zip_path in zip_files:
            extracted_files = self.unpacked(zip_path)

            if not extracted_files:
                continue

            temp_dir = Path(extracted_files[0]).parent

            for file_path in extracted_files:
                old_path = Path(file_path)
                new_path = base_dir / old_path.name

                if new_path.name in seen_filenames:
                    msg = f"Duplicate filename detected: {new_path.name}"
                    raise FileExistsError(msg)

                old_path.rename(new_path)

                seen_filenames.add(new_path.name)
                all_extracted_paths.append(new_path)

            if temp_dir.exists() and temp_dir.is_dir():
                temp_dir.rmdir()
            zip_path.unlink()

        return all_extracted_paths
