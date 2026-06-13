import csv
import logging
from pathlib import Path
from .data_enrichment_service import enrich_csv_if_needed
from django.conf import settings

logger = logging.getLogger(__name__)


class FuelDataCache:
    """
    Singleton cache for fuel station data.

    CSV MUST contain:

    OPIS Truckstop ID
    Truckstop Name
    Address
    City
    State
    Retail Price
    LATITUDE
    LONGITUDE
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()

        return cls._instance

    def _initialize(self):
        self._data = {}
        self._state_index = {}
        self._all_stations = []
        self.station_count = 0

        self.load_csv()

    def load_csv(self):

        enrich_csv_if_needed()

        csv_path = Path(settings.ENRICHED_FUEL_CSV_PATH)
        if not csv_path.exists():
            logger.error(
                "Fuel CSV not found: %s",
                csv_path
            )
            return

        self._data.clear()
        self._state_index.clear()
        self._all_stations.clear()

        loaded = 0
        skipped = 0

        try:
            with open(
                csv_path,
                mode="r",
                encoding="utf-8"
            ) as file:

                reader = csv.DictReader(file)

                for row in reader:

                    try:

                        state = row["State"].strip()
                        city = row["City"].strip()

                        if not state or not city:
                            skipped += 1
                            continue

                        lat = row.get("LATITUDE")
                        lng = row.get("LONGITUDE")

                        if not lat or not lng:
                            skipped += 1
                            continue

                        station = {
                            "id": row["OPIS Truckstop ID"],
                            "name": row["Truckstop Name"],
                            "address": row["Address"],
                            "city": city,
                            "state": state,
                            "price": float(row["Retail Price"]),
                            "lat": float(lat),
                            "lng": float(lng),
                        }

                        self._data.setdefault(
                            state,
                            {}
                        )

                        self._data[state].setdefault(
                            city,
                            []
                        )

                        self._data[state][city].append(
                            station
                        )

                        self._state_index.setdefault(
                            state,
                            []
                        )

                        self._state_index[state].append(
                            station
                        )

                        self._all_stations.append(
                            station
                        )

                        loaded += 1

                    except (
                        KeyError,
                        ValueError,
                        TypeError,
                    ):
                        skipped += 1

            self.station_count = loaded

            logger.info(
                "Loaded %s stations "
                "(skipped=%s)",
                loaded,
                skipped,
            )

        except Exception:
            logger.exception(
                "Failed loading fuel CSV"
            )

    def get_station_count(self):
        return self.station_count

    def get_all_stations(self):
        return self._all_stations

    def get_stations_by_state(
        self,
        state: str
    ):
        return self._state_index.get(
            state,
            []
        )

    def get_stations_by_state_city(
        self,
        state: str,
        city: str
    ):
        return self._data.get(
            state,
            {}
        ).get(
            city,
            []
        )

    def reload(self):
        logger.info(
            "Reloading fuel cache..."
        )
        self.load_csv()


def get_fuel_cache():
    return FuelDataCache()