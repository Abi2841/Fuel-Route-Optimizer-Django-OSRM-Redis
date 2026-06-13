import logging
import math
from typing import Dict, List, Tuple

from django.conf import settings
from shapely.geometry import Point, LineString

logger = logging.getLogger(__name__)


class FuelOptimizer:
    # Buffer distance to look for gas stations off the main highway
    ROUTE_BUFFER_MILES = 10.0

    def __init__(self, vehicle_range=None, efficiency=None):
        self.vehicle_range = vehicle_range or settings.VEHICLE_RANGE_MILES
        self.efficiency = efficiency or settings.FUEL_EFFICIENCY_MPG

    def optimize(
            self,
            origin: Tuple[float, float],
            destination: Tuple[float, float],
            route_distance: float,
            route_coordinates: List[List[float]],
            all_stations: List[Dict],
    ) -> Dict:
        try:
            # Convert routing API distance (usually meters) to miles
            total_distance_miles = route_distance / 1609.34

            nearby_stations = self._find_route_stations(
                route_coordinates,
                total_distance_miles,
                all_stations,
            )

            if not nearby_stations:
                return {
                    "status": "error",
                    "message": "No fuel stations found along the route.",
                }

            fuel_stops, total_cost = self._calculate_optimal_stops(
                nearby_stations,
                total_distance_miles,
            )

            return {
                "status": "success",
                "fuel_stops": fuel_stops,
                "total_distance": round(total_distance_miles, 2),
                "total_fuel_cost": round(total_cost, 2),
                "avg_fuel_price": round(self._avg_price(fuel_stops), 2),
                "message": f"Found {len(fuel_stops)} optimal fuel stops.",
            }

        except Exception as exc:
            logger.exception("Fuel optimization failed")
            return {
                "status": "error",
                "message": str(exc),
            }

    def _find_route_stations(
            self,
            route_coordinates: List[List[float]],
            total_distance: float,
            stations: List[Dict],
    ) -> List[Dict]:
        if not route_coordinates:
            return []

        # 1. Calculate Bounding Box for fast spatial pre-filtering
        min_lon = min(c[0] for c in route_coordinates)
        max_lon = max(c[0] for c in route_coordinates)
        min_lat = min(c[1] for c in route_coordinates)
        max_lat = max(c[1] for c in route_coordinates)

        # 2. Local Cartesian Projection setup (Fixes the "Flat Earth" bug)
        # 1 degree of latitude is ~69.172 miles. Longitude shrinks based on latitude.
        avg_lat = sum(c[1] for c in route_coordinates) / len(route_coordinates)
        cos_lat = math.cos(math.radians(avg_lat))

        lat_buffer = self.ROUTE_BUFFER_MILES / 69.172
        lon_buffer = self.ROUTE_BUFFER_MILES / (69.172 * cos_lat)

        # Fast O(N) pre-filter to drop stations outside the general route area
        candidate_stations = [
            s for s in stations
            if (min_lon - lon_buffer) <= s.get("lng", 0) <= (max_lon + lon_buffer)
               and (min_lat - lat_buffer) <= s.get("lat", 0) <= (max_lat + lat_buffer)
        ]

        def project_to_miles(lng: float, lat: float) -> Tuple[float, float]:
            """Converts local degrees to approximate miles for accurate Shapely distance checks."""
            return lng * cos_lat * 69.172, lat * 69.172

        # Project the complex route line into Cartesian miles
        route_miles_coords = [project_to_miles(lng, lat) for lng, lat in route_coordinates]
        route_line = LineString(route_miles_coords)

        nearby = []

        # 3. Exact Distance Checking
        for station in candidate_stations:
            try:
                p_miles = Point(project_to_miles(station["lng"], station["lat"]))
                distance = route_line.distance(p_miles)

                if distance > self.ROUTE_BUFFER_MILES:
                    continue

                # Project point onto line to find distance from the start of the route
                fraction = route_line.project(p_miles, normalized=True)
                route_dist = fraction * total_distance

                station_copy = dict(station)
                station_copy["route_distance"] = route_dist
                nearby.append(station_copy)

            except Exception:
                continue

        nearby.sort(key=lambda s: s["route_distance"])
        logger.info("Found %s stations near route", len(nearby))
        return nearby

    def _calculate_optimal_stops(self, stations: List[Dict], total_distance: float):
        # Bootstrap: Simulate starting the trip with a full tank of gas.
        # By setting price to 0.0, the algorithm naturally uses this "free" gas
        # for the first `vehicle_range` miles before buying from real stations.
        stations.insert(0, {
            "id": "START",
            "name": "Initial Full Tank",
            "price": 0.0,
            "route_distance": 0.0,
        })

        events = []
        for idx, station in enumerate(stations):
            # Station comes into range
            events.append((station["route_distance"], "enter", station, idx))
            # Station leaves range (tank would be empty)
            events.append((station["route_distance"] + self.vehicle_range, "exit", station, idx))

        # Sort events by distance along route
        events.sort(key=lambda x: x[0])

        active = {}
        current_distance = 0.0
        total_cost = 0.0
        gallons_by_station = {}

        # Sweep-line algorithm processing
        for position, event_type, station, idx in events:
            if current_distance >= total_distance:
                break

            if position > current_distance:
                if not active:
                    raise Exception(
                        f"Route cannot be completed. A gap larger than the "
                        f"{self.vehicle_range} mile vehicle range was found."
                    )

                # Find the cheapest station currently in our "active window" range
                cheapest_idx = min(active, key=lambda i: active[i]["price"])
                cheapest_station = active[cheapest_idx]

                # Calculate how much distance we need to cover before the next event
                segment = min(position, total_distance) - current_distance
                gallons = segment / self.efficiency

                total_cost += gallons * cheapest_station["price"]
                gallons_by_station[cheapest_idx] = gallons_by_station.get(cheapest_idx, 0) + gallons

                current_distance = min(position, total_distance)

            # Update the active window
            if event_type == "enter":
                active[idx] = station
            else:
                active.pop(idx, None)

        # Format output
        fuel_stops = []
        for idx, gallons in gallons_by_station.items():
            station = stations[idx]

            # Filter out the artificial start station and any station where we bought < 0.01 gallons
            if station["id"] == "START" or gallons <= 0.01:
                continue

            fuel_stops.append({
                "station_name": station["name"],
                "city": station.get("city", ""),
                "state": station.get("state", ""),
                "price_per_gallon": station["price"],
                "fuel_gallons": round(gallons, 2),
                "cost": round(gallons * station["price"], 2),
                "distance_along_route": round(station["route_distance"], 2),
                "lat": station.get("lat"),
                "lng": station.get("lng"),
            })

        # Sort final stops sequentially by distance along the route
        fuel_stops.sort(key=lambda x: x["distance_along_route"])
        return fuel_stops, total_cost

    @staticmethod
    def _avg_price(fuel_stops: List[Dict]) -> float:
        if not fuel_stops:
            return 0.0
        return sum(s["price_per_gallon"] for s in fuel_stops) / len(fuel_stops)


def get_fuel_optimizer():
    return FuelOptimizer()