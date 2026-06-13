# Vehicle specifications
DEFAULT_VEHICLE_RANGE = 500  # miles
DEFAULT_FUEL_EFFICIENCY = 10  # MPG (miles per gallon)

# USA coordinates bounds (rough)
USA_BOUNDS = {
    'min_lat': 24.5,
    'max_lat': 49.4,
    'min_lng': -125.0,
    'max_lng': -66.9,
}

# Cache settings
OSRM_CACHE_TTL = 30 * 24 * 60 * 60  # 30 days
RESULT_CACHE_TTL = 24 * 60 * 60      # 1 day
CSV_RELOAD_CACHE_TTL = 60 * 60       # 1 hour

# API settings
OSRM_TIMEOUT = 10  # seconds
MAX_ROUTE_ITERATIONS = 100  # Greedy algorithm safety limit

# Validation
MIN_LAT = -90
MAX_LAT = 90
MIN_LNG = -180
MAX_LNG = 180

DECIMAL_PLACES_FOR_COORDS = 4  # Round to 4 decimal places