from django.contrib import admin
from .models import Genre, Movie, Hall, Seat, Session, Booking, Ticket


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'status', 'duration')
    list_filter = ('status', 'genres')
    search_fields = ('title', 'director')


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'capacity', 'hall_type')


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ('id', 'hall', 'row_number', 'seat_number', 'seat_type')
    list_filter = ('hall', 'seat_type')
    search_fields = ('hall__name',)


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'movie', 'hall', 'start_time', 'format', 'base_price')
    list_filter = ('hall', 'format', 'start_time')
    search_fields = ('movie__title',)
    date_hierarchy = 'start_time'


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'session', 'status', 'total_price', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'id')


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'session', 'seat', 'status')
    list_filter = ('status', 'session')
