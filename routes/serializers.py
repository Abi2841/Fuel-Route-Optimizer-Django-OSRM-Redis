from rest_framework import serializers
from .utils.constants import USA_BOUNDS

class CoordinateSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lng = serializers.FloatField(min_value=-180, max_value=180)

    def validate(self, data):
        """Check if coordinates are within USA bounds"""
        lat, lng = data['lat'], data['lng']
        if not (USA_BOUNDS['min_lat'] <= lat <= USA_BOUNDS['max_lat'] and
                USA_BOUNDS['min_lng'] <= lng <= USA_BOUNDS['max_lng']):
            raise serializers.ValidationError("Coordinates are outside USA bounds.")
        return data

class OptimizeRouteRequestSerializer(serializers.Serializer):
    origin = CoordinateSerializer()
    destination = CoordinateSerializer()
    optional_route = serializers.BooleanField(default=False, required=False)

class FuelStopSerializer(serializers.Serializer):
    station_name = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    price_per_gallon = serializers.FloatField()
    # Fixed mismatch: your optimizer returns 'distance_along_route', not 'distance_from_origin'
    distance_along_route = serializers.FloatField()
    fuel_gallons = serializers.FloatField()
    cost = serializers.FloatField()
    lat = serializers.FloatField(allow_null=True)
    lng = serializers.FloatField(allow_null=True)

class RouteResponseSerializer(serializers.Serializer):
    fuel_stops = FuelStopSerializer(many=True)
    total_distance = serializers.FloatField()
    total_fuel_cost = serializers.FloatField()
    avg_fuel_price = serializers.FloatField()
    cached = serializers.BooleanField(required=False)
    # Added to match OSRM output
    route_geometry = serializers.JSONField(required=False)