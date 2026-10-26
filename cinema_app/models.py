from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название жанра")

    class Meta:
        verbose_name = "Жанр"
        verbose_name_plural = "Жанры"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Movie(models.Model):
    class Status(models.TextChoices):
        NOW_SHOWING = "В прокате", "В прокате"
        COMING_SOON = "Скоро", "Скоро"
        FINISHED = "Завершён", "Завершён"

    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    duration = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], verbose_name="Продолжительность (мин)"
    )
    age_rating = models.CharField(max_length=10, verbose_name="Возрастной рейтинг")
    country = models.CharField(max_length=100, verbose_name="Страна")
    director = models.CharField(max_length=150, verbose_name="Режиссёр")
    poster = models.ImageField(
        upload_to="posters/", blank=True, null=True, verbose_name="Постер"
    )
    trailer_url = models.URLField(blank=True, null=True, verbose_name="Ссылка на трейлер")
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.NOW_SHOWING,
        verbose_name="Статус проката",
    )
    genres = models.ManyToManyField(
        Genre, related_name="movies", blank=True, verbose_name="Жанры"
    )

    class Meta:
        verbose_name = "Фильм"
        verbose_name_plural = "Фильмы"
        ordering = ["title"]

    def __str__(self):
        return self.title


class Hall(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="Название/номер зала")
    capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], verbose_name="Вместимость"
    )
    hall_type = models.CharField(max_length=50, default="2D", verbose_name="Тип зала")
    schema_json = models.JSONField(
        default=dict, blank=True, verbose_name="Дополнительная схема зала (JSON)"
    )

    class Meta:
        verbose_name = "Кинозал"
        verbose_name_plural = "Кинозалы"
        ordering = ["name"]

    def clean(self):
        super().clean()
        if self.pk and self.capacity < self.seats.count():
            raise ValidationError({
                "capacity": "Вместимость не может быть меньше количества созданных мест."
            })

    def __str__(self):
        return f"Зал {self.name}"


class Seat(models.Model):
    class SeatType(models.TextChoices):
        STANDARD = "Стандарт", "Стандарт"
        VIP = "VIP", "VIP"

    hall = models.ForeignKey(
        Hall, on_delete=models.CASCADE, related_name="seats", verbose_name="Зал"
    )
    row_number = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], verbose_name="Номер ряда"
    )
    seat_number = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], verbose_name="Номер места"
    )
    seat_type = models.CharField(
        max_length=50,
        choices=SeatType.choices,
        default=SeatType.STANDARD,
        verbose_name="Тип места",
    )

    class Meta:
        verbose_name = "Место"
        verbose_name_plural = "Места"
        ordering = ["row_number", "seat_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["hall", "row_number", "seat_number"],
                name="unique_seat_position_in_hall",
            )
        ]

    def clean(self):
        super().clean()
        if self.hall_id and self.hall.capacity:
            existing_count = Seat.objects.filter(hall_id=self.hall_id).exclude(pk=self.pk).count()
            if existing_count >= self.hall.capacity:
                raise ValidationError({"hall": "В этом зале уже достигнута указанная вместимость."})

    def __str__(self):
        return f"Зал {self.hall.name}: ряд {self.row_number}, место {self.seat_number}"


class Session(models.Model):
    movie = models.ForeignKey(
        Movie, on_delete=models.CASCADE, related_name="sessions", verbose_name="Фильм"
    )
    hall = models.ForeignKey(
        Hall, on_delete=models.CASCADE, related_name="sessions", verbose_name="Зал"
    )
    start_time = models.DateTimeField(verbose_name="Дата и время начала")
    end_time = models.DateTimeField(verbose_name="Дата и время окончания")
    format = models.CharField(max_length=20, default="2D", verbose_name="Формат")
    base_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Базовая цена билета",
    )

    class Meta:
        verbose_name = "Сеанс"
        verbose_name_plural = "Сеансы"
        ordering = ["start_time"]
        indexes = [models.Index(fields=["start_time", "movie"])]

    def clean(self):
        super().clean()
        errors = {}

        if self.start_time and self.end_time and self.end_time <= self.start_time:
            errors["end_time"] = "Время окончания должно быть позже времени начала."

        if (
            self.hall_id
            and self.start_time
            and self.end_time
            and self.end_time > self.start_time
        ):
            overlaps = Session.objects.filter(
                hall_id=self.hall_id,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            ).exclude(pk=self.pk)
            if overlaps.exists():
                errors["hall"] = "В этом зале уже запланирован пересекающийся по времени сеанс."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.movie.title} — {self.start_time:%d.%m.%Y %H:%M}"


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает подтверждения"
        PAID = "paid", "Подтверждена (демо)"
        CANCELLED = "cancelled", "Отменена"
        EXPIRED = "expired", "Истекла"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookings",
        verbose_name="Пользователь",
    )
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="bookings", verbose_name="Сеанс"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Статус",
    )
    expires_at = models.DateTimeField(verbose_name="Время истечения брони")
    total_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name="Общая сумма",
    )
    qr_code = models.ImageField(
        upload_to="qr_codes/", blank=True, null=True, verbose_name="QR-код"
    )

    class Meta:
        verbose_name = "Бронь"
        verbose_name_plural = "Брони"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "expires_at"])]

    def __str__(self):
        return f"Бронь #{self.pk} — {self.user}"


class Ticket(models.Model):
    class Status(models.TextChoices):
        BOOKED = "booked", "Забронирован"
        PAID = "paid", "Подтверждён (демо)"
        USED = "used", "Использован"
        CANCELLED = "cancelled", "Отменён"

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="tickets", verbose_name="Бронь"
    )
    session = models.ForeignKey(
        Session, on_delete=models.CASCADE, related_name="tickets", verbose_name="Сеанс"
    )
    seat = models.ForeignKey(
        Seat, on_delete=models.CASCADE, related_name="tickets", verbose_name="Место"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.BOOKED,
        verbose_name="Статус",
    )

    class Meta:
        verbose_name = "Билет"
        verbose_name_plural = "Билеты"
        constraints = [
            models.UniqueConstraint(
                fields=["session", "seat"],
                condition=Q(status__in=["booked", "paid", "used"]),
                name="unique_active_ticket_per_session_seat",
            )
        ]
        indexes = [models.Index(fields=["session", "status"])]

    def clean(self):
        super().clean()
        errors = {}

        if self.booking_id and self.session_id:
            if self.booking.session_id != self.session_id:
                errors["session"] = "Сеанс билета должен совпадать с сеансом брони."

        if self.seat_id and self.session_id:
            if self.seat.hall_id != self.session.hall_id:
                errors["seat"] = "Место должно принадлежать залу выбранного сеанса."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"Билет #{self.pk} — {self.seat}"
