import logging
from pathlib import Path

import pandas as pd
from django.conf import settings

logger = logging.getLogger(__name__)

US_CITIES_URL = (
    "https://raw.githubusercontent.com/"
    "kelvins/US-Cities-Database/main/csv/us_cities.csv"
)


def enrich_csv_if_needed():
    """
    Creates fuel_prices_enriched.csv if it does not exist.

    Input:
        fuel_prices.csv

    Output:
        fuel_prices_enriched.csv
    """

    fuel_csv = Path(settings.BASE_DIR) / "data" / "fuel_prices.csv"

    enriched_csv = (
        Path(settings.BASE_DIR)
        / "data"
        / "fuel_prices_enriched.csv"
    )

    if enriched_csv.exists():
        logger.info(
            "Enriched CSV already exists: %s",
            enriched_csv,
        )
        return

    logger.info("Creating enriched fuel CSV...")

    try:
        create_enriched_csv(
            fuel_csv,
            enriched_csv,
        )

        logger.info(
            "Created enriched CSV: %s",
            enriched_csv,
        )

    except Exception:
        logger.exception(
            "Failed creating enriched CSV"
        )
        raise


def create_enriched_csv(
    fuel_csv_path: Path,
    output_csv_path: Path,
):
    """
    Merge fuel station CSV with US city coordinates.
    """

    logger.info(
        "Loading fuel station CSV..."
    )

    fuel_df = pd.read_csv(
        fuel_csv_path
    )

    logger.info(
        "Downloading US cities dataset..."
    )

    cities_df = pd.read_csv(
        US_CITIES_URL
    )

    # Normalize join columns
    fuel_df["City_join"] = (
        fuel_df["City"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    fuel_df["State_join"] = (
        fuel_df["State"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    cities_df["CITY_join"] = (
        cities_df["CITY"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    cities_df["STATE_join"] = (
        cities_df["STATE_CODE"]
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # Keep one city/state record
    cities_df = cities_df.drop_duplicates(
        subset=[
            "CITY_join",
            "STATE_join",
        ]
    )

    logger.info(
        "Merging coordinates..."
    )

    merged = fuel_df.merge(
        cities_df[
            [
                "CITY_join",
                "STATE_join",
                "LATITUDE",
                "LONGITUDE",
            ]
        ],
        left_on=[
            "City_join",
            "State_join",
        ],
        right_on=[
            "CITY_join",
            "STATE_join",
        ],
        how="left",
    )

    total_rows = len(merged)

    matched_rows = (
        merged["LATITUDE"]
        .notna()
        .sum()
    )

    logger.info(
        "Matched %s/%s stations",
        matched_rows,
        total_rows,
    )

    # Remove helper columns
    merged.drop(
        columns=[
            "City_join",
            "State_join",
            "CITY_join",
            "STATE_join",
        ],
        inplace=True,
        errors="ignore",
    )

    output_csv_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    merged.to_csv(
        output_csv_path,
        index=False,
    )

    logger.info(
        "Saved enriched CSV with %s rows",
        len(merged),
    )