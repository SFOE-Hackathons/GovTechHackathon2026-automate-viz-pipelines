import os
import io
import sys
import time
import logging
import requests
import pandas as pd
import yaml
from pylindas import Cube

GENERATION_COLUMNS: dict[str, str] = {
    "Erzeugung_Laufwerk_GWh": "Laufwerk",
    "Erzeugung_Speicherwerk_GWh": "Speicherwerk",
    "Erzeugung_Kernkraftwerk_GWh": "Kernkraftwerk",
    "Erzeugung_andere_GWh": "andere",
    "Erzeugung_Thermische_GWh": "Thermische",
    "Erzeugung_Windkraft_GWh": "Windkraft",
    "Erzeugung_Photovoltaik_GWh": "Photovoltaik",
}


def download_csv(url: str, timeout: tuple[int, int] = (30, 120), retries: int = 3) -> str:
    """Download CSV from URL with exponential backoff retry.

    Args:
        url: HTTP/HTTPS URL to download CSV from
        timeout: (connect_timeout, read_timeout) in seconds
        retries: Maximum number of retry attempts

    Returns:
        CSV content as string

    Raises:
        requests.exceptions.RequestException: If all retries exhausted
        ValueError: If response body is empty
    """
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            if not response.text.strip():
                raise ValueError("CSV response is empty")
            return response.text
        except (requests.exceptions.RequestException, ValueError) as e:
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt
            time.sleep(wait)


def validate_data(df: pd.DataFrame, required_columns: list[str]) -> None:
    """Validate DataFrame has expected columns and non-zero rows.

    Args:
        df: DataFrame to validate
        required_columns: List of column names that must be present

    Raises:
        ValueError: If required columns are missing or DataFrame is empty
    """
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if len(df) == 0:
        raise ValueError("Dataset is empty (zero data rows)")


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """Transform raw wide-format CSV data into long-format cube-ready structure.

    Melts 7 generation-type columns into rows, producing a DataFrame with
    columns: datum, definitiv, erzeugungstyp, gwh.

    Args:
        df: Raw DataFrame with columns Jahr, Monat, Definitiv, and 7 generation columns.

    Returns:
        Long-format DataFrame with columns: datum, definitiv, erzeugungstyp, gwh.
    """
    df = df.copy()

    # Create date column (first day of month)
    df["datum"] = pd.to_datetime(dict(year=df["Jahr"], month=df["Monat"], day=1))

    # Extract definitiv flag as integer
    df["definitiv"] = df["Definitiv"].astype(int)

    # Melt generation columns into long format
    melted = pd.melt(
        df,
        id_vars=["datum", "definitiv"],
        value_vars=list(GENERATION_COLUMNS.keys()),
        var_name="erzeugungstyp",
        value_name="gwh",
    )

    # Map raw column names to cleaned short labels
    melted["erzeugungstyp"] = melted["erzeugungstyp"].map(GENERATION_COLUMNS)

    # Round gwh values and cast to Int64 (nullable integer)
    melted["gwh"] = melted["gwh"].round(0).astype("Int64")

    # Replace NaN/NA with empty strings for cube compatibility
    melted = melted.astype(str).replace(["<NA>", "NaN", "nan"], "")

    return melted


def create_cube(df: pd.DataFrame, metadata_path: str, environment: str = "INT") -> Cube:
    """Load metadata YAML and create a pylindas Cube object.

    Args:
        df: Transformed DataFrame ready for cube creation
        metadata_path: Path to the metadata YAML file
        environment: Target environment (PROD, INT, or TEST)

    Returns:
        Fully prepared Cube object

    Raises:
        FileNotFoundError: If metadata file doesn't exist
        yaml.YAMLError: If metadata file is malformed
        ValueError: If metadata is missing required fields
    """
    if not os.path.exists(metadata_path):
        raise FileNotFoundError(f"Metadata file not found: {metadata_path}")

    with open(metadata_path, encoding="utf-8") as file:
        description = yaml.safe_load(file)

    if not description:
        raise ValueError(f"Metadata file is empty or invalid: {metadata_path}")

    cube = Cube(dataframe=df, cube_yaml=description, environment=environment, local=True)
    cube.prepare_data().write_cube().write_observations().write_shape()

    return cube


def serialize_cube(cube: Cube, output_path: str) -> None:
    """Serialize cube to Turtle (.ttl) format.

    Args:
        cube: Fully prepared Cube object
        output_path: File path for the output .ttl file
    """
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    cube.serialize(output_path)


def main() -> None:
    """Orchestrate the full pipeline: download → validate → transform → create → serialize."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    logger = logging.getLogger(__name__)

    CSV_URL = "https://www.uvek-gis.admin.ch/BFE/ogd/35/ogd35_schweizerische_elektrizitaetsbilanz_monatswerte.csv"
    REQUIRED_COLUMNS = ["Jahr", "Monat", "Definitiv", "Erzeugung_Laufwerk_GWh", "Erzeugung_Speicherwerk_GWh", "Erzeugung_Kernkraftwerk_GWh", "Erzeugung_andere_GWh", "Erzeugung_Thermische_GWh", "Erzeugung_Windkraft_GWh", "Erzeugung_Photovoltaik_GWh"]
    METADATA_PATH = "inputs/metadata.yml"
    OUTPUT_PATH = "outputs/cube.ttl"

    try:
        # Step 1: Download
        logger.info("Starting CSV download from %s", CSV_URL)
        csv_text = download_csv(CSV_URL)
        logger.info("CSV download complete (%d bytes)", len(csv_text))

        # Step 2: Parse and validate
        df = pd.read_csv(io.StringIO(csv_text))
        validate_data(df, REQUIRED_COLUMNS)
        logger.info("Data validation passed (%d rows)", len(df))

        # Step 3: Transform
        logger.info("Starting data transformation")
        df = transform_data(df)
        logger.info("Transformation complete")

        # Step 4: Create cube
        logger.info("Creating RDF cube")
        cube = create_cube(df, METADATA_PATH)
        logger.info("Cube creation complete")

        # Step 5: Serialize
        serialize_cube(cube, OUTPUT_PATH)
        logger.info("✅ Cube serialized to %s", OUTPUT_PATH)

    except Exception as e:
        logger.error("Pipeline failed: %s - %s", type(e).__name__, str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
