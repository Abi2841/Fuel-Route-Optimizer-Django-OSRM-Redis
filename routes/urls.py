from django.urls import path
from .views import OptimizeRouteView, HealthCheckView

app_name = 'routes'

urlpatterns = [
    # Health check
    path('health/', HealthCheckView.as_view(), name='health'),

    # Main optimization endpoint
    path('optimize/', OptimizeRouteView.as_view(), name='optimize-route'),
]