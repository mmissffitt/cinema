from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Booking, Hall, Movie, Seat, Session, Ticket

User = get_user_model()


class CinemaApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="viewer", password="Safe-test-password-123"
        )
        self.client.force_authenticate(user=self.user)

        self.movie = Movie.objects.create(
            title="Тестовый фильм",
            description="Описание",
            duration=100,
            age_rating="12+",
            country="Россия",
            director="Тестовый режиссёр",
        )
        self.hall = Hall.objects.create(name="1", capacity=2)
        self.seat_1 = Seat.objects.create(
            hall=self.hall, row_number=1, seat_number=1
        )
        self.seat_2 = Seat.objects.create(
            hall=self.hall, row_number=1, seat_number=2
        )
        self.other_hall = Hall.objects.create(name="2", capacity=1)
        self.foreign_seat = Seat.objects.create(
            hall=self.other_hall, row_number=1, seat_number=1
        )
        start = timezone.now() + timedelta(days=1)
        self.session = Session.objects.create(
            movie=self.movie,
            hall=self.hall,
            start_time=start,
            end_time=start + timedelta(minutes=100),
            base_price=Decimal("8.50"),
        )

    def create_booking(self, seat_ids=None, expires_at=None, status_value=Booking.Status.PENDING):
        if seat_ids is None:
            seat_ids = [self.seat_1.id]
        booking = Booking.objects.create(
            user=self.user,
            session=self.session,
            status=status_value,
            expires_at=expires_at or timezone.now() + timedelta(minutes=15),
            total_price=self.session.base_price * len(seat_ids),
        )
        Ticket.objects.bulk_create(
            [
                Ticket(booking=booking, session=self.session, seat_id=seat_id)
                for seat_id in seat_ids
            ]
        )
        return booking

    def test_health_check(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ok")

    def test_user_can_book_available_seat(self):
        response = self.client.post(
            "/api/bookings/",
            {"session_id": self.session.id, "seat_ids": [self.seat_1.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["total_price"], "8.50")
        self.assertEqual(Ticket.objects.filter(booking_id=response.data["id"]).count(), 1)
        self.assertEqual(response.data["status"], Booking.Status.PENDING)

    def test_unauthenticated_user_cannot_create_booking(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            "/api/bookings/",
            {"session_id": self.session.id, "seat_ids": [self.seat_1.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_same_seat_cannot_be_booked_twice(self):
        first_response = self.client.post(
            "/api/bookings/",
            {"session_id": self.session.id, "seat_ids": [self.seat_1.id]},
            format="json",
        )
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)

        second_user = User.objects.create_user(
            username="second-viewer", password="Another-safe-password-123"
        )
        self.client.force_authenticate(user=second_user)
        second_response = self.client.post(
            "/api/bookings/",
            {"session_id": self.session.id, "seat_ids": [self.seat_1.id]},
            format="json",
        )
        self.assertEqual(second_response.status_code, status.HTTP_409_CONFLICT)

    def test_seat_from_another_hall_is_rejected(self):
        response = self.client.post(
            "/api/bookings/",
            {"session_id": self.session.id, "seat_ids": [self.foreign_seat.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_seat_id_is_rejected(self):
        response = self.client.post(
            "/api/bookings/",
            {"session_id": self.session.id, "seat_ids": [self.seat_1.id, self.seat_1.id]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_more_than_ten_seats_is_rejected(self):
        response = self.client.post(
            "/api/bookings/",
            {"session_id": self.session.id, "seat_ids": list(range(1, 12))},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_seat_map_returns_availability_for_session(self):
        response = self.client.get(f"/api/sessions/{self.session.id}/seats/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertTrue(all(seat["is_available"] for seat in response.data))

        self.create_booking([self.seat_1.id])
        response = self.client.get(f"/api/sessions/{self.session.id}/seats/")
        available = {seat["id"]: seat["is_available"] for seat in response.data}
        self.assertFalse(available[self.seat_1.id])
        self.assertTrue(available[self.seat_2.id])

    def test_expired_booking_releases_seat(self):
        booking = self.create_booking(
            [self.seat_1.id], expires_at=timezone.now() - timedelta(minutes=1)
        )
        response = self.client.get(f"/api/sessions/{self.session.id}/seats/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        ticket = booking.tickets.get()
        self.assertEqual(booking.status, Booking.Status.EXPIRED)
        self.assertEqual(ticket.status, Ticket.Status.CANCELLED)
        available = {seat["id"]: seat["is_available"] for seat in response.data}
        self.assertTrue(available[self.seat_1.id])

    def test_user_can_cancel_own_pending_booking(self):
        booking = self.create_booking([self.seat_1.id])
        response = self.client.delete(f"/api/bookings/{booking.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.CANCELLED)
        self.assertEqual(booking.tickets.get().status, Ticket.Status.CANCELLED)

    def test_user_cannot_view_another_users_booking(self):
        booking = self.create_booking([self.seat_1.id])
        other_user = User.objects.create_user(
            username="other", password="Another-safe-password-123"
        )
        self.client.force_authenticate(user=other_user)
        response = self.client.get(f"/api/bookings/{booking.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_demo_confirmation_marks_booking_and_tickets_paid(self):
        booking = self.create_booking([self.seat_1.id])
        response = self.client.post(f"/api/bookings/{booking.id}/confirm/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.PAID)
        self.assertEqual(booking.tickets.get().status, Ticket.Status.PAID)

        cancel_response = self.client.delete(f"/api/bookings/{booking.id}/")
        self.assertEqual(cancel_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_returns_token_and_does_not_return_password(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(
            "/api/auth/register/",
            {
                "username": "new-viewer",
                "email": "viewer@example.com",
                "password": "Different-Strong-Password-456",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", response.data)
        self.assertNotIn("password", response.data["user"])
        self.assertTrue(Token.objects.filter(user__username="new-viewer").exists())

    def test_session_model_rejects_overlapping_sessions_when_validated(self):
        overlapping = Session(
            movie=self.movie,
            hall=self.hall,
            start_time=self.session.start_time + timedelta(minutes=30),
            end_time=self.session.end_time + timedelta(minutes=30),
            base_price=Decimal("8.50"),
        )
        with self.assertRaises(ValidationError):
            overlapping.full_clean()
