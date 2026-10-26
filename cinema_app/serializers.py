from rest_framework import serializers
from .models import Genre, Movie, Hall, Seat, Session, Booking, Ticket


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name']


class MovieShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ['id', 'title', 'poster', 'duration', 'age_rating']


class MovieSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Movie
        fields = '__all__'


class HallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hall
        fields = '__all__'


class SeatSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seat
        fields = ['id', 'row_number', 'seat_number', 'seat_type']


class SessionSerializer(serializers.ModelSerializer):
    movie = MovieShortSerializer(read_only=True)
    hall_name = serializers.CharField(source='hall.name', read_only=True)
    available_seats = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = ['id', 'movie', 'hall', 'hall_name', 'start_time',
                  'end_time', 'format', 'base_price', 'available_seats']

    def get_available_seats(self, obj):
        total = obj.hall.seats.count()
        booked = obj.tickets.filter(status__in=['booked', 'paid']).count()
        return total - booked


class TicketSerializer(serializers.ModelSerializer):
    seat = SeatSerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = ['id', 'seat', 'status']


class BookingSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, read_only=True)
    session_info = SessionSerializer(source='session', read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'session', 'session_info', 'created_at', 'status',
                  'expires_at', 'total_price', 'tickets']
        read_only_fields = ['status', 'total_price', 'expires_at']


class BookingCreateSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    seat_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )
