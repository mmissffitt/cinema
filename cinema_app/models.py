from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class Genre(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Название жанра")

    class Meta:
        verbose_name = "Жанр"
        verbose_name_plural = "Жанры"

    def __str__(self):
        return self.name


class Movie(models.Model):
    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(verbose_name="Описание")
    duration = models.PositiveIntegerField(verbose_name="Продолжительность (мин)")
    age_rating = models.CharField(max_length=10, verbose_name="Возрастной рейтинг")
    country = models.CharField(max_length=100, verbose_name="Страна")
    director = models.CharField(max_length=150, verbose_name="Режиссёр")
    poster = models.ImageField(upload_to='posters/', blank=True, null=True, verbose_name="Постер")
    trailer_url = models.URLField(blank=True, null=True, verbose_name="Трейлер")
    status = models.CharField(max_length=50, default='В прокате', verbose_name="Статус проката")
    genres = models.ManyToManyField(Genre, related_name='movies', verbose_name="Жанры")

    class Meta:
        verbose_name = "Фильм"
        verbose_name_plural = "Фильмы"

    def __str__(self):
        return self.title


class Hall(models.Model):
    name = models.CharField(max_length=50, verbose_name="Название/Номер зала")
    capacity = models.PositiveIntegerField(verbose_name="Вместимость")
    hall_type = models.CharField(max_length=50, default='2D', verbose_name="Тип зала")
    schema_json = models.JSONField(default=dict, blank=True, verbose_name="Схема зала")

    class Meta:
        verbose_name = "Кинозал"
        verbose_name_plural = "Кинозалы"

    def __str__(self):
        return f"Зал {self.name}"


class Seat(models.Model):
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='seats', verbose_name="Зал")
    row_number = models.PositiveIntegerField(verbose_name="Номер ряда")
    seat_number = models.PositiveIntegerField(verbose_name="Номер места")
    seat_type = models.CharField(max_length=50, default='Стандарт', verbose_name="Тип места")

    class Meta:
        verbose_name = "Место"
        verbose_name_plural = "Места"
        unique_together = ('hall', 'row_number', 'seat_number')

    def __str__(self):
        return f"Ряд {self.row_number}, место {self.seat_number}"


class Session(models.Model):
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='sessions', verbose_name="Фильм")
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='sessions', verbose_name="Зал")
    start_time = models.DateTimeField(verbose_name="Дата и время начала")
    end_time = models.DateTimeField(verbose_name="Дата и время окончания")
    format = models.CharField(max_length=20, default='2D', verbose_name="Формат")
    base_price = models.DecimalField(
        max_digits=8, decimal_places=2,
        validators=[MinValueValidator(0)], verbose_name="Базовая цена"
    )

    class Meta:
        verbose_name = "Сеанс"
        verbose_name_plural = "Сеансы"
        ordering = ['start_time']

    def __str__(self):
        return f"{self.movie.title} — {self.start_time:%d.%m.%Y %H:%M}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачена'),
        ('cancelled', 'Отменена'),
        ('expired', 'Истекла'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings', verbose_name="Пользователь")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='bookings', verbose_name="Сеанс")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    expires_at = models.DateTimeField(verbose_name="Время истечения")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Общая сумма")
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True, verbose_name="QR-код")

    class Meta:
        verbose_name = "Бронь"
        verbose_name_plural = "Брони"
        ordering = ['-created_at']

    def __str__(self):
        return f"Бронь #{self.id} — {self.user.username}"


class Ticket(models.Model):
    STATUS_CHOICES = [
        ('booked', 'Забронирован'),
        ('paid', 'Оплачен'),
        ('used', 'Использован'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='tickets', verbose_name="Бронь")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='tickets', verbose_name="Сеанс")
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, verbose_name="Место")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='booked', verbose_name="Статус")

    class Meta:
        verbose_name = "Билет"
        verbose_name_plural = "Билеты"

    def __str__(self):
        return f"Билет #{self.id} — {self.seat}"
