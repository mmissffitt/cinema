from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    BookingViewSet,
    GenreViewSet,
    HallViewSet,
    MovieViewSet,
    SeatViewSet,
    SessionViewSet,
    current_user_view,
    health_check,
    login_view,
    logout_view,
    register_view,
)

router = DefaultRouter()
router.register(r"genres", GenreViewSet, basename="genre")
router.register(r"movies", MovieViewSet, basename="movie")
router.register(r"halls", HallViewSet, basename="hall")
router.register(r"sessions", SessionViewSet, basename="session")
router.register(r"seats", SeatViewSet, basename="seat")
router.register(r"bookings", BookingViewSet, basename="booking")

urlpatterns = [
    path("health/", health_check, name="health-check"),
    path("auth/register/", register_view, name="register"),
    path("auth/login/", login_view, name="login"),
    path("auth/logout/", logout_view, name="logout"),
    path("auth/me/", current_user_view, name="current-user"),
    path("", include(router.urls)),
]
