from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Booking, Genre, Hall, Movie, Seat, Session, Ticket
from .utils import get_occupied_seat_ids

User = get_user_model()


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name"]


class MovieShortSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = ["id", "title", "poster", "duration", "age_rating", "genres"]


class MovieSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = [
            "id", "title", "description", "duration", "age_rating", "country",
            "director", "poster", "trailer_url", "status", "genres",
        ]


class HallSerializer(serializers.ModelSerializer):
    seats_count = serializers.SerializerMethodField()

    class Meta:
        model = Hall
        fields = ["id", "name", "capacity", "hall_type", "schema_json", "seats_count"]

    def get_seats_count(self, obj):
        return obj.seats.count()


class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = ["id", "hall", "row_number", "seat_number", "seat_type"]


class SessionSeatSerializer(serializers.ModelSerializer):
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = Seat
        fields = ["id", "row_number", "seat_number", "seat_type", "is_available"]

    def get_is_available(self, obj):
        return obj.id not in self.context.get("occupied_seat_ids", set())


class SessionSerializer(serializers.ModelSerializer):
    movie = MovieShortSerializer(read_only=True)
    hall_name = serializers.CharField(source="hall.name", read_only=True)
    total_seats = serializers.SerializerMethodField()
    available_seats = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            "id", "movie", "hall", "hall_name", "start_time", "end_time",
            "format", "base_price", "total_seats", "available_seats",
        ]

    def get_total_seats(self, obj):
        return obj.hall.seats.count()

    def get_available_seats(self, obj):
        return max(obj.hall.seats.count() - len(get_occupied_seat_ids(obj)), 0)


class TicketSerializer(serializers.ModelSerializer):
    seat = SeatSerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = ["id", "seat", "status"]


class BookingSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=True)
    session_info = SessionSerializer(source="session", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "session", "session_info", "created_at", "status",
            "expires_at", "total_price", "tickets",
        ]
        read_only_fields = fields


class BookingCreateSerializer(serializers.Serializer):
    session_id = serializers.IntegerField(min_value=1)
    seat_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=10,
        error_messages={"max_length": "За одну бронь можно выбрать не более 10 мест."},
    )

    def validate_seat_ids(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Одно и то же место указано несколько раз.")
        return value


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]
        read_only_fields = ["id"]
        extra_kwargs = {"email": {"required": False, "allow_blank": True}}

    def validate(self, attrs):
        candidate_user = User(
            username=attrs.get("username", ""),
            email=attrs.get("email", ""),
        )
        validate_password(attrs["password"], user=candidate_user)
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(trim_whitespace=True)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
