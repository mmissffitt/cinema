from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .models import Booking, Genre, Hall, Movie, Seat, Session, Ticket
from .serializers import (
    BookingCreateSerializer,
    BookingSerializer,
    GenreSerializer,
    HallSerializer,
    LoginSerializer,
    MovieSerializer,
    RegisterSerializer,
    SeatSerializer,
    SessionSeatSerializer,
    SessionSerializer,
)
from .utils import BOOKING_DURATION_MINUTES, expire_old_bookings, get_occupied_seat_ids


def _positive_int_param(request, name):
    value = request.query_params.get(name)
    if value in (None, ""):
        return None
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        raise ValidationError({name: "Параметр должен быть положительным целым числом."})
    if parsed_value < 1:
        raise ValidationError({name: "Параметр должен быть положительным целым числом."})
    return parsed_value


def _user_payload(user):
    return {"id": user.id, "username": user.username, "email": user.email}


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def health_check(request):
    return Response({"status": "ok", "service": "cinema-api"})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    token = Token.objects.create(user=user)
    return Response(
        {"token": token.key, "user": _user_payload(user)},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = authenticate(
        request=request,
        username=serializer.validated_data["username"],
        password=serializer.validated_data["password"],
    )
    if user is None:
        return Response(
            {"detail": "Неверный логин или пароль."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "user": _user_payload(user)})


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    Token.objects.filter(user=request.user).delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def current_user_view(request):
    return Response(_user_payload(request.user))


class GenreViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [permissions.AllowAny]


class MovieViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MovieSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Movie.objects.filter(
            status__in=[Movie.Status.NOW_SHOWING, Movie.Status.COMING_SOON]
        ).prefetch_related("genres")

        genre_id = _positive_int_param(self.request, "genre")
        if genre_id:
            queryset = queryset.filter(genres__id=genre_id)

        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset.distinct()


class HallViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Hall.objects.all().prefetch_related("seats")
    serializer_class = HallSerializer
    permission_classes = [permissions.AllowAny]


class SessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SessionSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = (
            Session.objects.filter(
                start_time__gte=timezone.now(),
                movie__status__in=[Movie.Status.NOW_SHOWING, Movie.Status.COMING_SOON],
            )
            .select_related("movie", "hall")
            .prefetch_related("movie__genres", "hall__seats")
        )

        movie_id = _positive_int_param(self.request, "movie_id")
        if movie_id:
            queryset = queryset.filter(movie_id=movie_id)

        date_value = self.request.query_params.get("date")
        if date_value:
            parsed_date = parse_date(date_value)
            if parsed_date is None:
                raise ValidationError({"date": "Укажите дату в формате ГГГГ-ММ-ДД."})
            queryset = queryset.filter(start_time__date=parsed_date)

        return queryset

    @action(detail=True, methods=["get"], url_path="seats")
    def seats(self, request, pk=None):
        """Список мест для выбранного сеанса и признак доступности каждого места."""
        expire_old_bookings()
        session = self.get_object()
        seats = session.hall.seats.all().order_by("row_number", "seat_number")
        serializer = SessionSeatSerializer(
            seats,
            many=True,
            context={"occupied_seat_ids": get_occupied_seat_ids(session)},
        )
        return Response(serializer.data)


class SeatViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Seat.objects.select_related("hall").all()
    serializer_class = SeatSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        hall_id = _positive_int_param(self.request, "hall_id")
        if hall_id:
            queryset = queryset.filter(hall_id=hall_id)
        return queryset


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_queryset(self):
        expire_old_bookings()
        return (
            Booking.objects.filter(user=self.request.user)
            .select_related("session__movie", "session__hall")
            .prefetch_related("tickets__seat__hall", "session__movie__genres")
        )

    def create(self, request, *args, **kwargs):
        input_serializer = BookingCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        session_id = input_serializer.validated_data["session_id"]
        seat_ids = input_serializer.validated_data["seat_ids"]

        expire_old_bookings()

        try:
            with transaction.atomic():
                # PostgreSQL serializes simultaneous bookings for the same session here.
                session = (
                    Session.objects.select_for_update()
                    .select_related("hall", "movie")
                    .get(pk=session_id)
                )

                now = timezone.now()
                if session.start_time <= now:
                    return Response(
                        {"error": "На начавшийся сеанс нельзя оформить бронь."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if session.movie.status == Movie.Status.FINISHED:
                    return Response(
                        {"error": "Фильм больше не доступен для бронирования."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                valid_seat_ids = set(
                    Seat.objects.filter(id__in=seat_ids, hall_id=session.hall_id)
                    .values_list("id", flat=True)
                )
                if valid_seat_ids != set(seat_ids):
                    return Response(
                        {"error": "Одно или несколько мест не существуют или относятся к другому залу."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                occupied_ids = get_occupied_seat_ids(session)
                unavailable_ids = occupied_ids.intersection(seat_ids)
                if unavailable_ids:
                    return Response(
                        {
                            "error": "Некоторые места уже заняты.",
                            "seat_ids": sorted(unavailable_ids),
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                created_at = timezone.now()
                expires_at = min(
                    created_at + timedelta(minutes=BOOKING_DURATION_MINUTES),
                    session.start_time,
                )
                booking = Booking.objects.create(
                    user=request.user,
                    session=session,
                    total_price=session.base_price * Decimal(len(seat_ids)),
                    expires_at=expires_at,
                )
                Ticket.objects.bulk_create(
                    [
                        Ticket(
                            booking=booking,
                            session=session,
                            seat_id=seat_id,
                            status=Ticket.Status.BOOKED,
                        )
                        for seat_id in seat_ids
                    ]
                )

        except Session.DoesNotExist:
            return Response({"error": "Сеанс не найден."}, status=status.HTTP_404_NOT_FOUND)
        except IntegrityError:
            # UniqueConstraint защищает от дублирования мест даже при конкурентных запросах.
            return Response(
                {"error": "Одно или несколько мест только что заняли. Обновите схему мест."},
                status=status.HTTP_409_CONFLICT,
            )

        booking = self.get_queryset().get(pk=booking.pk)
        return Response(
            BookingSerializer(booking, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="confirm")
    def confirm(self, request, pk=None):
        """Демонстрационное подтверждение без банковской оплаты."""
        expire_old_bookings()
        with transaction.atomic():
            booking = Booking.objects.select_for_update().filter(
                pk=self.get_object().pk, user=request.user
            ).first()
            if booking is None:
                return Response({"detail": "Бронь не найдена."}, status=status.HTTP_404_NOT_FOUND)

            if booking.status != Booking.Status.PENDING or booking.expires_at <= timezone.now():
                return Response(
                    {"error": "Эту бронь нельзя подтвердить: её срок истёк или она уже обработана."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not booking.tickets.filter(status=Ticket.Status.BOOKED).exists():
                return Response(
                    {"error": "У брони нет активных билетов."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            booking.status = Booking.Status.PAID
            booking.save(update_fields=["status"])
            booking.tickets.filter(status=Ticket.Status.BOOKED).update(status=Ticket.Status.PAID)

        booking = self.get_queryset().get(pk=booking.pk)
        return Response(BookingSerializer(booking, context={"request": request}).data)

    def destroy(self, request, *args, **kwargs):
        expire_old_bookings()
        initial_booking = self.get_object()

        with transaction.atomic():
            booking = Booking.objects.select_for_update().filter(
                pk=initial_booking.pk, user=request.user
            ).first()
            if booking is None:
                return Response({"detail": "Бронь не найдена."}, status=status.HTTP_404_NOT_FOUND)
            if booking.status != Booking.Status.PENDING:
                return Response(
                    {"error": "Отменить можно только действующую неподтверждённую бронь."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            booking.status = Booking.Status.CANCELLED
            booking.save(update_fields=["status"])
            booking.tickets.filter(status=Ticket.Status.BOOKED).update(
                status=Ticket.Status.CANCELLED
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
