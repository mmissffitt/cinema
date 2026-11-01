import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import '../App.css';

const API_URL = 'http://127.0.0.1:8000/api/';

function BookingPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [session, setSession] = useState(null);
  const [seats, setSeats] = useState([]);
  const [selectedSeats, setSelectedSeats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [booking, setBooking] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [sessionResponse, seatsResponse] = await Promise.all([
          fetch(`${API_URL}sessions/${id}/`),
          fetch(`${API_URL}sessions/${id}/seats/`),
        ]);

        if (!sessionResponse.ok || !seatsResponse.ok) {
          throw new Error('Не удалось загрузить данные сеанса.');
        }

        const sessionData = await sessionResponse.json();
        const seatsData = await seatsResponse.json();

        setSession(sessionData);
        setSeats(seatsData);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [id]);

  const rows = useMemo(() => {
    const grouped = {};

    seats.forEach((seat) => {
      if (!grouped[seat.row_number]) grouped[seat.row_number] = [];
      grouped[seat.row_number].push(seat);
    });

    return Object.entries(grouped).sort(
      ([a], [b]) => Number(a) - Number(b),
    );
  }, [seats]);

  const totalPrice = session
    ? Number(session.base_price) * selectedSeats.length
    : 0;

  function toggleSeat(seat) {
    if (!seat.is_available) return;

    setSelectedSeats((current) => {
      if (current.includes(seat.id)) {
        return current.filter((seatId) => seatId !== seat.id);
      }

      if (current.length >= 10) {
        setError('За одну бронь можно выбрать не более 10 мест.');
        return current;
      }

      setError('');
      return [...current, seat.id];
    });
  }

  async function createBooking() {
    const token = localStorage.getItem('cinemaToken');

    if (!token) {
      navigate('/login', {
        state: { from: `/sessions/${id}` },
      });
      return;
    }

    if (selectedSeats.length === 0) {
      setError('Сначала выбери места.');
      return;
    }

    setBooking(true);
    setError('');

    try {
      const response = await fetch(`${API_URL}bookings/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Token ${token}`,
        },
        body: JSON.stringify({
          session_id: Number(id),
          seat_ids: selectedSeats,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
          data.detail ||
          'Не удалось создать бронирование. Обнови схему мест.',
        );
      }

      navigate('/profile', {
        state: { newBooking: data.id },
      });
    } catch (err) {
      setError(err.message);
      setSelectedSeats([]);
      fetch(`${API_URL}sessions/${id}/seats/`)
        .then((response) => response.json())
        .then(setSeats)
        .catch(() => {});
    } finally {
      setBooking(false);
    }
  }

  if (loading) {
    return <div className="app page-message">Загружаем схему зала...</div>;
  }

  if (error && !session) {
    return (
      <div className="app page-message">
        <p>{error}</p>
        <Link to="/">Вернуться к афише</Link>
      </div>
    );
  }

  return (
    <div className="app">
      <header className="header">
        <Link className="logo" to="/">
          CINEMA<span className="logo-accent">.</span>
        </Link>
        <nav className="navigation">
          <Link to="/">Фильмы</Link>
          <Link to="/profile">Мои бронирования</Link>
        </nav>
        <Link className="login-button" to="/login">Войти</Link>
      </header>

      <main className="movies-section booking-page">
        <Link className="back-link" to={`/movies/${session.movie.id}`}>
          ← Вернуться к фильму
        </Link>

        <span className="eyebrow">БРОНИРОВАНИЕ БИЛЕТОВ</span>
        <h1 className="booking-title">{session.movie.title}</h1>

        <p className="booking-subtitle">
          {new Date(session.start_time).toLocaleString('ru-RU', {
            day: 'numeric',
            month: 'long',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
          {' · '}{session.hall_name} · {session.format}
        </p>

        <div className="seat-legend">
          <span><i className="seat-example available" /> Свободно</span>
          <span><i className="seat-example selected" /> Выбрано</span>
          <span><i className="seat-example occupied" /> Занято</span>
        </div>

        {seats.length === 0 ? (
          <div className="empty-seats">
            <h2>В этом зале пока нет мест</h2>
            <p>
              Сначала необходимо создать места в панели администратора Django.
            </p>
          </div>
        ) : (
          <>
            <div className="cinema-screen">
              ЭКРАН
            </div>

            <div className="seat-map">
              {rows.map(([rowNumber, rowSeats]) => (
                <div className="seat-row" key={rowNumber}>
                  <span className="row-number">{rowNumber}</span>

                  {rowSeats.map((seat) => {
                    const isSelected = selectedSeats.includes(seat.id);

                    return (
                      <button
                        key={seat.id}
                        type="button"
                        title={`Ряд ${seat.row_number}, место ${seat.seat_number} — ${seat.seat_type}`}
                        className={[
                          'seat',
                          !seat.is_available ? 'occupied' : '',
                          isSelected ? 'selected' : '',
                          seat.seat_type === 'VIP' ? 'vip' : '',
                        ].join(' ')}
                        disabled={!seat.is_available}
                        onClick={() => toggleSeat(seat)}
                      >
                        {seat.seat_number}
                      </button>
                    );
                  })}

                  <span className="row-number">{rowNumber}</span>
                </div>
              ))}
            </div>
          </>
        )}

        <div className="booking-summary">
          <div>
            <span className="eyebrow">ВАШ ЗАКАЗ</span>
            <p>
              Выбрано мест: <strong>{selectedSeats.length}</strong>
            </p>
            <p>
              Стоимость: <strong>{totalPrice.toLocaleString('ru-RU')} ₽</strong>
            </p>
            {selectedSeats.length > 0 && (
              <p>
                Номера мест: {selectedSeats.map((seatId) => {
                  const seat = seats.find((item) => item.id === seatId);
                  return seat ? `${seat.row_number} ряд, ${seat.seat_number}` : '';
                }).join('; ')}
              </p>
            )}
          </div>

          <button
            className="primary-button booking-submit"
            disabled={selectedSeats.length === 0 || booking}
            onClick={createBooking}
          >
            {booking ? 'Оформляем...' : 'Забронировать →'}
          </button>
        </div>

        {error && <p className="form-error">{error}</p>}
      </main>

      <footer className="footer">
        <span>CINEMA. — Твой билет в другой мир.</span>
      </footer>
    </div>
  );
}

export default BookingPage;