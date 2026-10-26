from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response

from .models import Movie, Session, Seat, Booking, Ticket
from .serializers import (
    MovieSerializer, SessionSerializer, SeatSerializer,
    BookingSerializer, BookingCreateSerializer,
)


class MovieViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Movie.objects.filter(status='В прокате').prefetch_related('genres')
    serializer_class = MovieSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        genre = self.request.query_params.get('genre')
        if genre:
            queryset = queryset.filter(genres__id=genre)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset


class SessionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Session.objects.select_related('movie', 'hall').all()
    serializer_class = SessionSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        movie_id = self.request.query_params.get('movie_id')
        if movie_id:
            queryset = queryset.filter(movie_id=movie_id)
        date = self.request.query_params.get('date')
        if date:
            queryset = queryset.filter(start_time__date=date)
        return queryset


class SeatViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Seat.objects.all()
    serializer_class = SeatSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        hall_id = self.request.query_params.get('hall_id')
        if hall_id:
            queryset = queryset.filter(hall_id=hall_id)
        return queryset


class BookingViewSet(viewsets.ModelViewSet):
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'delete']

    def get_queryset(self):
        return Booking.objects.filter(
            user=self.request.user
        ).prefetch_related('tickets__seat')

    def create(self, request, *args, **kwargs):
        input_serializer = BookingCreateSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        session_id = input_serializer.validated_data['session_id']
        seat_ids = input_serializer.validated_data['seat_ids']

        try:
            with transaction.atomic():
                session = Session.objects.select_for_update().get(id=session_id)

                already_taken = Ticket.objects.filter(
                    session=session,
                    seat_id__in=seat_ids,
                    status__in=['booked', 'paid'],
                )
                if already_taken.exists():
                    return Response(
                        {"error": "Некоторые места уже заняты"},
                        status=status.HTTP_409_CONFLICT,
                    )

                total_price = session.base_price * len(seat_ids)
                booking = Booking.objects.create(
                    user=request.user,
                    session=session,
                    total_price=total_price,
                    expires_at=timezone.now() + timedelta(minutes=15),
                )
                Ticket.objects.bulk_create([
                    Ticket(booking=booking, session=session, seat_id=seat_id)
                    for seat_id in seat_ids
                ])

                return Response(
                    BookingSerializer(booking).data,
                    status=status.HTTP_201_CREATED,
                )
        except Session.DoesNotExist:
            return Response(
                {"error": "Сеанс не найден"},
                status=status.HTTP_404_NOT_FOUND,
            )
