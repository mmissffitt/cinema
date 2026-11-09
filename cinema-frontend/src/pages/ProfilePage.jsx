import { useCallback, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import '../App.css';

const API_URL = 'http://127.0.0.1:8000/api/';
const API_BASE = 'http://127.0.0.1:8000';

function ProfilePage() {
  const navigate = useNavigate();

  const [user, setUser] = useState(null);
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const token = localStorage.getItem('cinemaToken');

  const loadProfile = useCallback(async () => {
    if (!token) {
      navigate('/login');
      return;
    }

    try {
      const headers = { Authorization: `Token ${token}` };

      const [userResponse, bookingsResponse] = await Promise.all([
        fetch(`${API_URL}auth/me/`, { headers }),
        fetch(`${API_URL}bookings/`, { headers }),
      ]);

      if (userResponse.status === 401 || bookingsResponse.status === 401) {
        localStorage.removeItem('cinemaToken');
        localStorage.removeItem('cinemaUser');
        navigate('/login');
        return;
      }

      if (!userResponse.ok || !bookingsResponse.ok) {
        throw new Error('Не удалось загрузить личный кабинет.');
      }

      const userData = await userResponse.json();
      const bookingsData = await bookingsResponse.json();

      setUser(userData);
      setBookings(
        Array.isArray(bookingsData)
          ? bookingsData
          : bookingsData.results || [],
      );
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [navigate, token]);

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  async function handleBookingAction(bookingId, action) {
    setError('');

    try {
      const response = await fetch(
        `${API_URL}bookings/${bookingId}/${action === 'confirm' ? 'confirm/' : ''}`,
        {
          method: action === 'confirm' ? 'POST' : 'DELETE',
          headers: { Authorization: `Token ${token}` },
        },
      );

      if (!response.ok && response.status !== 204) {
        const data = await response.json();
        throw new Error(data.error || data.detail || 'Не удалось выполнить действие.');
      }

      await loadProfile();
    } catch (err) {
      setError(err.message);
    }
  }

  async function logout() {
    try {
      await fetch(`${API_URL}auth/logout/`, {
        method: 'POST',
        headers: { Authorization: `Token ${token}` },
      });
    } finally {
      localStorage.removeItem('cinemaToken');
      localStorage.removeItem('cinemaUser');
      navigate('/');
    }
  }

  if (loading) {
    return <div className="app page-message">Загружаем личный кабинет...</div>;
  }

  return (
    <div className="app">
      <header className="header">
        <Link className="logo" to="/">
          CINEMA<span className="logo-accent">.</span>
        </Link>

        <nav className="navigation">
          <Link to="/">Афиша</Link>
        </nav>

        <button className="login-button" onClick={logout}>
          Выйти
        </button>
      </header>

      <main className="movies-section profile-page">
        <span className="eyebrow">ЛИЧНЫЙ КАБИНЕТ</span>
        <h1 className="profile-title">
          Привет, {user?.username || 'зритель'}!
        </h1>
        <p className="profile-description">
          Здесь хранятся твои бронирования, билеты и статистика.
        </p>

        {user?.stats && (
          <div className="profile-stats-grid">
            <div className="stat-card">
              <span>Всего броней</span>
              <strong>{user.stats.total_bookings}</strong>
            </div>
            <div className="stat-card">
              <span>Оплачено билетов</span>
              <strong>{user.stats.paid_bookings}</strong>
            </div>
            <div className="stat-card">
              <span>Потрачено</span>
              <strong>{Number(user.stats.total_spent).toLocaleString('ru-RU')} ₽</strong>
            </div>
          </div>
        )}

        <h2 className="profile-section-title">Мои бронирования</h2>

        {error && <p className="form-error">{error}</p>}

        {bookings.length === 0 ? (
          <div className="empty-bookings">
            <p>У тебя пока нет бронирований.</p>
            <Link className="primary-button" to="/">
              Перейти к афише →
            </Link>
          </div>
        ) : (
          <div className="booking-list">
            {bookings.map((booking) => {
              const qrUrl = booking.qr_code
                ? booking.qr_code.startsWith('http')
                  ? booking.qr_code
                  : `${API_BASE}${booking.qr_code}`
                : null;

              return (
                <article className="booking-card" key={booking.id}>
                  <div className="booking-card-heading">
                    <div>
                      <span className="eyebrow">БРОНЬ №{booking.id}</span>
                      <h3>{booking.session_info.movie.title}</h3>
                    </div>

                    <span className={`booking-status ${booking.status}`}>
                      {booking.status === 'pending' && 'Ожидает подтверждения'}
                      {booking.status === 'paid' && 'Подтверждена'}
                      {booking.status === 'cancelled' && 'Отменена'}
                      {booking.status === 'expired' && 'Истекла'}
                    </span>
                  </div>

                  <p>
                    {new Date(booking.session_info.start_time).toLocaleString('ru-RU', {
                      day: 'numeric',
                      month: 'long',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>

                  <p>
                    {booking.session_info.hall_name} · {booking.session_info.format}
                  </p>

                  <div className="ticket-list">
                    {booking.tickets.map((ticket) => (
                      <span className="ticket-chip" key={ticket.id}>
                        Ряд {ticket.seat.row_number}, место {ticket.seat.seat_number}
                      </span>
                    ))}
                  </div>

                  {qrUrl && (
                    <div className="booking-qr-section">
                      <img src={qrUrl} alt="QR-код билета" className="qr-code-img" />
                      <span>Предъявите этот QR-код контроллёру при входе в кинозал.</span>
                    </div>
                  )}

                  <div className="booking-card-bottom">
                    <strong>
                      {Number(booking.total_price).toLocaleString('ru-RU')} ₽
                    </strong>

                    {booking.status === 'pending' && (
                      <div className="booking-actions">
                        <button
                          className="primary-button"
                          onClick={() => handleBookingAction(booking.id, 'confirm')}
                        >
                          Подтвердить
                        </button>

                        <button
                          className="cancel-button"
                          onClick={() => handleBookingAction(booking.id, 'cancel')}
                        >
                          Отменить
                        </button>
                      </div>
                    )}
                  </div>

                  {booking.status === 'pending' && (
                    <p className="booking-expiry">
                      Бронь действует до: {new Date(booking.expires_at).toLocaleString('ru-RU')}
                    </p>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </main>

      <footer className="footer">
        <span>CINEMA. — Твой билет в другой мир.</span>
      </footer>
    </div>
  );
}

export default ProfilePage;