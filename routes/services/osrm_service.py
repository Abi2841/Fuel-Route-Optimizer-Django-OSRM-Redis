import copy
import logging
from typing import Dict, Any

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class OSRMService:
    """
    OSRM Routing Service

    Features:
    - Redis caching
    - Distance (meters + miles)
    - Duration
    - Route geometry
    - Route coordinates
    - Bounding box
    - Turn-by-turn steps
    """

    CACHE_TIMEOUT = 30 * 24 * 60 * 60  # 30 days

    def __init__(self):
        self.api_url = settings.OSRM_API_URL.rstrip("/")
        self.timeout = getattr(settings, "OSRM_TIMEOUT", 10)
        self.session = requests.Session()

    def _build_cache_key(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> str:
        """
        Round coordinates to improve cache hit ratio.
        4 decimals ~= 11 meters accuracy.
        """

        return (
            f"route:"
            f"{round(origin_lat, 4)}_{round(origin_lng, 4)}:"
            f"{round(dest_lat, 4)}_{round(dest_lng, 4)}"
        )

    def get_route(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> Dict[str, Any]:

        cache_key = self._build_cache_key(
            origin_lat,
            origin_lng,
            dest_lat,
            dest_lng,
        )

        cached_result = cache.get(cache_key)

        if cached_result:
            logger.info(
                "OSRM cache HIT: %s",
                cache_key,
            )

            result = copy.deepcopy(cached_result)
            result["cached"] = True

            return result

        logger.info(
            "OSRM cache MISS: %s",
            cache_key,
        )

        result = self._call_osrm_api(
            origin_lat,
            origin_lng,
            dest_lat,
            dest_lng,
        )

        cache.set(
            cache_key,
            result,
            timeout=self.CACHE_TIMEOUT,
        )

        result["cached"] = False

        return result

    def _call_osrm_api(
        self,
        origin_lat: float,
        origin_lng: float,
        dest_lat: float,
        dest_lng: float,
    ) -> Dict[str, Any]:

        coordinates = (
            f"{origin_lng},{origin_lat};"
            f"{dest_lng},{dest_lat}"
        )

        url = (
            f"{self.api_url}"
            f"/route/v1/driving/{coordinates}"
        )

        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
        }

        try:

            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
            )

            response.raise_for_status()

            data = response.json()

            if data.get("code") != "Ok":
                raise Exception(
                    data.get(
                        "message",
                        "OSRM returned an error"
                    )
                )

            routes = data.get("routes", [])

            if not routes:
                raise Exception(
                    "No route found from OSRM"
                )

            route = routes[0]

            geometry = route.get(
                "geometry",
                {}
            )

            route_coordinates = geometry.get(
                "coordinates",
                []
            )

            distance_meters = route.get(
                "distance",
                0
            )

            distance_miles = round(
                distance_meters / 1609.34,
                2
            )

            duration_seconds = route.get(
                "duration",
                0
            )

            steps = []

            for leg in route.get(
                "legs",
                []
            ):
                steps.extend(
                    leg.get(
                        "steps",
                        []
                    )
                )

            bbox = None

            if route_coordinates:

                lons = [
                    point[0]
                    for point in route_coordinates
                ]

                lats = [
                    point[1]
                    for point in route_coordinates
                ]

                bbox = {
                    "min_lat": min(lats),
                    "max_lat": max(lats),
                    "min_lng": min(lons),
                    "max_lng": max(lons),
                }

            return {
                # REQUIRED BY OPTIMIZER
                "distance_meters": distance_meters,
                "distance_miles": distance_miles,

                # ROUTE
                "geometry": geometry,
                "coordinates": route_coordinates,

                # EXTRA INFO
                "duration_seconds": duration_seconds,
                "coordinate_count": len(route_coordinates),
                "bbox": bbox,
                "steps": steps,
            }

        except requests.Timeout:
            logger.exception(
                "OSRM request timeout"
            )
            raise Exception(
                "OSRM request timeout"
            )

        except requests.ConnectionError:
            logger.exception(
                "OSRM connection failed"
            )
            raise Exception(
                "Could not connect to OSRM"
            )

        except requests.RequestException as exc:
            logger.exception(
                "OSRM request failed"
            )
            raise Exception(
                f"OSRM request failed: {exc}"
            )

        except Exception as exc:
            logger.exception(
                "Unexpected OSRM error"
            )
            raise Exception(
                str(exc)
            )

    @staticmethod
    def decode_geometry(
        geometry: Dict[str, Any]
    ) -> list:
        """
        Extract coordinates from GeoJSON LineString.
        """

        if (
            geometry
            and geometry.get("type")
            == "LineString"
        ):
            return geometry.get(
                "coordinates",
                []
            )

        return []


def get_osrm_service() -> OSRMService:
    return OSRMService()