from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MovieViewSet, SessionViewSet, SeatViewSet, BookingViewSet

router = DefaultRouter()
router.register(r'movies', MovieViewSet, basename='movie')
router.register(r'sessions', SessionViewSet, basename='session')
router.register(r'seats', SeatViewSet, basename='seat')
router.register(r'bookings', BookingViewSet, basename='booking')

urlpatterns = [
    path('', include(router.urls)),
]