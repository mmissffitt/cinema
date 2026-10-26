from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import Booking, Ticket

BOOKING_DURATION_MINUTES = 15


def expire_old_bookings():
    """Помечает истёкшие брони и освобождает связанные с ними места.

    Функция вызывается из API-запросов; для учебного проекта фоновый планировщик
    не требуется. Срок брони также ограничивается временем начала сеанса.
    """
    now = timezone.now()
    expired_filter = Q(expires_at__lte=now) | Q(session__start_time__lte=now)

    with transaction.atomic():
        expired_ids = list(
            Booking.objects.select_for_update()
            .filter(status=Booking.Status.PENDING)
            .filter(expired_filter)
            .values_list("id", flat=True)
        )
        if not expired_ids:
            return 0

        Booking.objects.filter(id__in=expired_ids).update(status=Booking.Status.EXPIRED)
        Ticket.objects.filter(
            booking_id__in=expired_ids,
            status__in=[Ticket.Status.BOOKED, Ticket.Status.PAID],
        ).update(status=Ticket.Status.CANCELLED)

    return len(expired_ids)


def get_occupied_seat_ids(session):
    """Возвращает ID мест, занятых действующей бронью или подтверждённым билетом."""
    now = timezone.now()
    active_booking = Q(booking__status=Booking.Status.PAID) | Q(
        booking__status=Booking.Status.PENDING,
        booking__expires_at__gt=now,
        booking__session__start_time__gt=now,
    )

    return set(
        Ticket.objects.filter(
            session=session,
            seat__hall_id=session.hall_id,
            status__in=[Ticket.Status.BOOKED, Ticket.Status.PAID, Ticket.Status.USED],
        )
        .filter(active_booking)
        .values_list("seat_id", flat=True)
        .distinct()
    )
