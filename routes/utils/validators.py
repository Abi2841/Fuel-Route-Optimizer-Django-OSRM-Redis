from django.core.exceptions import ValidationError
from .constants import MIN_LAT, MAX_LAT, MIN_LNG, MAX_LNG, USA_BOUNDS, DECIMAL_PLACES_FOR_COORDS


class CoordinateValidator:
    """Validate geographic coordinates"""

    @staticmethod
    def validate_lat(lat: float) -> bool:
        """Validate latitude"""
        try:
            lat = float(lat)
            return MIN_LAT <= lat <= MAX_LAT
        except (TypeError, ValueError):
            return False

    @staticmethod
    def validate_lng(lng: float) -> bool:
        """Validate longitude"""
        try:
            lng = float(lng)
            return MIN_LNG <= lng <= MAX_LNG
        except (TypeError, ValueError):
            return False

    @staticmethod
    def validate_usa_location(lat: float, lng: float) -> bool:
        """Check if coordinates are within USA bounds"""
        try:
            lat = float(lat)
            lng = float(lng)

            return (USA_BOUNDS['min_lat'] <= lat <= USA_BOUNDS['max_lat'] and
                    USA_BOUNDS['min_lng'] <= lng <= USA_BOUNDS['max_lng'])
        except (TypeError, ValueError):
            return False

    @staticmethod
    def round_coordinates(lat: float, lng: float) -> tuple:
        """Round coordinates to reduce cache key uniqueness issues"""
        return (
            round(float(lat), DECIMAL_PLACES_FOR_COORDS),
            round(float(lng), DECIMAL_PLACES_FOR_COORDS)
        )


class RequestValidator:
    """Validate API request payloads"""

    @staticmethod
    def validate_optimize_route_request(data: dict) -> tuple:
        """
        Validate request data.

        Returns:
            (is_valid, error_message)
        """

        # Check required fields
        if 'origin' not in data:
            return False, "Missing 'origin' field"
        if 'destination' not in data:
            return False, "Missing 'destination' field"

        origin = data['origin']
        destination = data['destination']

        # Validate origin
        if not isinstance(origin, dict) or 'lat' not in origin or 'lng' not in origin:
            return False, "Origin must be {lat: float, lng: float}"

        if not CoordinateValidator.validate_lat(origin['lat']):
            return False, f"Invalid origin latitude: {origin['lat']}"

        if not CoordinateValidator.validate_lng(origin['lng']):
            return False, f"Invalid origin longitude: {origin['lng']}"

        if not CoordinateValidator.validate_usa_location(origin['lat'], origin['lng']):
            return False, f"Origin coordinates not in USA bounds"

        # Validate destination
        if not isinstance(destination, dict) or 'lat' not in destination or 'lng' not in destination:
            return False, "Destination must be {lat: float, lng: float}"

        if not CoordinateValidator.validate_lat(destination['lat']):
            return False, f"Invalid destination latitude: {destination['lat']}"

        if not CoordinateValidator.validate_lng(destination['lng']):
            return False, f"Invalid destination longitude: {destination['lng']}"

        if not CoordinateValidator.validate_usa_location(destination['lat'], destination['lng']):
            return False, f"Destination coordinates not in USA bounds"

        # Validate optional_route
        optional_route = data.get('optional_route', False)
        if not isinstance(optional_route, bool):
            return False, "'optional_route' must be boolean"

        return True, ""

    @staticmethod
    def normalize_request(data: dict) -> dict:
        """Normalize and round coordinates for caching"""
        origin_lat, origin_lng = CoordinateValidator.round_coordinates(
            data['origin']['lat'], data['origin']['lng']
        )
        dest_lat, dest_lng = CoordinateValidator.round_coordinates(
            data['destination']['lat'], data['destination']['lng']
        )

        return {
            'origin': {'lat': origin_lat, 'lng': origin_lng},
            'destination': {'lat': dest_lat, 'lng': dest_lng},
            'optional_route': data.get('optional_route', False),
        }