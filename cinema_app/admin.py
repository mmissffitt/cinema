from django.contrib import admin
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError

from .models import Booking, Genre, Hall, Movie, Seat, Session, Ticket


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "duration", "country", "director")
    list_filter = ("status", "genres", "country")
    search_fields = ("title", "director", "country")
    filter_horizontal = ("genres",)


class SeatInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        actual_count = 0
        for form in self.forms:
            if not hasattr(form, "cleaned_data") or not form.cleaned_data:
                continue
            if form.cleaned_data.get("DELETE", False):
                continue
            # Existing filled forms and new filled forms both have cleaned data.
            if form.cleaned_data.get("row_number") and form.cleaned_data.get("seat_number"):
                actual_count += 1

        if self.instance.capacity and actual_count > self.instance.capacity:
            raise ValidationError(
                f"Вместимость зала — {self.instance.capacity}; мест в форме — {actual_count}."
            )


class SeatInline(admin.TabularInline):
    model = Seat
    formset = SeatInlineFormSet
    extra = 0


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ("name", "capacity", "hall_type")
    search_fields = ("name",)
    inlines = (SeatInline,)


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("hall", "row_number", "seat_number", "seat_type")
    list_filter = ("hall", "seat_type")
    ordering = ("hall", "row_number", "seat_number")


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("movie", "hall", "start_time", "end_time", "format", "base_price")
    list_filter = ("hall", "format")
    search_fields = ("movie__title", "hall__name")
    date_hierarchy = "start_time"


class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 0
    can_delete = False
    readonly_fields = ("session", "seat", "status")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session", "status", "created_at", "expires_at", "total_price")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "session__movie__title")
    readonly_fields = (
        "user", "session", "created_at", "status", "expires_at", "total_price", "qr_code"
    )
    inlines = (TicketInline,)

    def has_add_permission(self, request):
        # Брони создаются через API, чтобы всегда выполнялись проверки мест.
        return False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("id", "booking", "session", "seat", "status")
    list_filter = ("status", "session")
    search_fields = ("booking__user__username", "session__movie__title")
    readonly_fields = ("booking", "session", "seat", "status")

    def has_add_permission(self, request):
        # Билеты создаются только внутри транзакции создания брони.
        return False
