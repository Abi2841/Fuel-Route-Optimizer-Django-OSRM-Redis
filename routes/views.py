import logging
import time

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import OptimizeRouteRequestSerializer
from .services.cache_service import get_fuel_cache
from .services.osrm_service import get_osrm_service
from .services.fuel_optimizer import get_fuel_optimizer
from .utils.validators import RequestValidator

logger = logging.getLogger(__name__)


class OptimizeRouteView(APIView):
    def post(self, request):
        start_time = time.time()

        # 1. DRF Native Validation
        req_serializer = OptimizeRouteRequestSerializer(data=request.data)
        if not req_serializer.is_valid():
            return Response({
                "status": "error",
                "message": "Invalid payload",
                "errors": req_serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        valid_data = req_serializer.validated_data
        origin = (valid_data["origin"]["lat"], valid_data["origin"]["lng"])
        destination = (valid_data["destination"]["lat"], valid_data["destination"]["lng"])

        # 2. OSRM Service
        try:
            osrm_service = get_osrm_service()
            route_data = osrm_service.get_route(
                origin_lat=origin[0], origin_lng=origin[1],
                dest_lat=destination[0], dest_lng=destination[1]
            )
        except Exception as exc:
            return Response({"status": "error", "message": str(exc)}, status=503)

        # 3. Cache & Optimization
        fuel_cache = get_fuel_cache()
        all_stations = fuel_cache.get_all_stations()

        if not all_stations:
            return Response({"status": "error", "message": "Stations unavailable"}, status=500)

        optimizer = get_fuel_optimizer()
        opt_result = optimizer.optimize(
            origin=origin,
            destination=destination,
            route_distance=route_data["distance_meters"],
            route_coordinates=route_data["coordinates"],
            all_stations=all_stations,
        )

        if opt_result["status"] != "success":
            return Response(opt_result, status=400)

        # 4. Build Response Payload
        response_data = {
            "status": "success",
            "message": "Route optimization completed",
            "primary_route": {
                "fuel_stops": opt_result["fuel_stops"],
                "total_distance": opt_result["total_distance"],
                "total_fuel_cost": opt_result["total_fuel_cost"],
                "avg_fuel_price": opt_result["avg_fuel_price"],
                "cached": route_data.get("cached", False)
            },
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }

        return Response(response_data, status=status.HTTP_200_OK)

class HealthCheckView(APIView):

    def get(self, request):

        fuel_cache = get_fuel_cache()

        return Response(
            {
                "status": "healthy",
                "fuel_stations_loaded": (
                    fuel_cache.get_station_count()
                ),
            },
            status=status.HTTP_200_OK,
        )