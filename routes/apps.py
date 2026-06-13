from django.apps import AppConfig


class RoutesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "routes"

    def ready(self):
        """
        Startup sequence:

        1. Create enriched CSV if missing
        2. Load fuel cache
        """

        from .services.data_enrichment_service import (
            enrich_csv_if_needed,
        )

        from .services.cache_service import (
            get_fuel_cache,
        )

        try:
            enrich_csv_if_needed()

            cache = get_fuel_cache()

            print(
                f"Fuel cache initialized with "
                f"{cache.get_station_count()} stations"
            )

        except Exception as exc:
            print(
                f"Fuel cache initialization failed: "
                f"{exc}"
            )