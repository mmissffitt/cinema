import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import '../App.css';

const API_URL = 'http://127.0.0.1:8000/api/';
const API_BASE = 'http://127.0.0.1:8000';

function getYouTubeEmbedUrl(url) {
  if (!url) return null;
  const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
  const match = url.match(regExp);
  return (match && match[2].length === 11)
    ? `https://www.youtube.com/embed/${match[2]}?autoplay=1`
    : null;
}

function MoviePage() {
  const { id } = useParams();

  const [movie, setMovie] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sessionsError, setSessionsError] = useState('');
  const [isTrailerOpen, setIsTrailerOpen] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError('');

    fetch(`${API_URL}movies/${id}/`)
      .then((response) => {
        if (!response.ok) throw new Error();
        return response.json();
      })
      .then(setMovie)
      .catch(() => setError('Не удалось загрузить информацию о фильме.'))
      .finally(() => setLoading(false));

    fetch(`${API_URL}sessions/?movie_id=${id}`)
      .then((response) => {
        if (!response.ok) throw new Error();
        return response.json();
      })
      .then((data) => {
        setSessions(Array.isArray(data) ? data : data.results || []);
      })
      .catch(() => setSessionsError('Не удалось загрузить сеансы.'));
  }, [id]);

  if (loading) {
    return <div className="app page-message">Загружаем фильм...</div>;
  }

  if (error || !movie) {
    return (
      <div className="app page-message">
        <p>{error || 'Фильм не найден.'}</p>
        <Link to="/">Вернуться к афише</Link>
      </div>
    );
  }

  const posterUrl = movie.poster
    ? movie.poster.startsWith('http')
      ? movie.poster
      : `${API_BASE}${movie.poster}`
    : null;

  const genres = movie.genres?.length
    ? movie.genres.map((genre) => genre.name).join(' · ')
    : 'Жанр не указан';

  const embedUrl = getYouTubeEmbedUrl(movie.trailer_url);

  return (
    <div className="app">
      <header className="header">
        <Link className="logo" to="/">
          CINEMA<span className="logo-accent">.</span>
        </Link>

        <nav className="navigation">
          <Link to="/">Афиша</Link>
        </nav>

        <Link className="login-button" to="/profile">
          Личный кабинет
        </Link>
      </header>

      <main className="movies-section">
        <Link className="back-link" to="/">← Назад к афише</Link>

        <div className="movie-details">
          {posterUrl ? (
            <img
              className="poster"
              src={posterUrl}
              alt={`Постер фильма «${movie.title}»`}
            />
          ) : (
            <div className="poster poster-placeholder">
              Постер отсутствует
            </div>
          )}

          <div className="movie-details-info">
            <span className="eyebrow">ИНФОРМАЦИЯ О ФИЛЬМЕ</span>
            <h1>{movie.title}</h1>

            <p>{genres}</p>
            <p>{movie.duration} мин. · {movie.age_rating}</p>

            {movie.country && <p>Страна: {movie.country}</p>}
            {movie.director && <p>Режиссёр: {movie.director}</p>}

            <h2>Описание</h2>
            <p>{movie.description || 'Описание пока не добавлено.'}</p>

            {/* Кнопка открытия трейлера в модальном окне */}
            {embedUrl && (
              <div style={{ marginTop: '24px' }}>
                <button
                  className="primary-button"
                  onClick={() => setIsTrailerOpen(true)}
                >
                  ▶ Смотреть трейлер
                </button>
              </div>
            )}

            <h2>Расписание сеансов</h2>

            {sessionsError && <p className="form-error">{sessionsError}</p>}

            {!sessionsError && sessions.length === 0 && (
              <p>Для этого фильма пока нет будущих сеансов.</p>
            )}

            {sessions.map((session) => (
              <div className="session-card" key={session.id}>
                <div>
                  <strong>
                    {new Date(session.start_time).toLocaleString('ru-RU', {
                      day: 'numeric',
                      month: 'long',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </strong>
                  <p>{session.hall_name} · {session.format}</p>
                  <p>Свободно мест: {session.available_seats}</p>
                </div>

                <div className="session-price">
                  <strong>{Number(session.base_price).toLocaleString('ru-RU')} ₽</strong>
                  <Link
                    className="session-button"
                    to={`/sessions/${session.id}`}
                  >
                    Выбрать места
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>

      {/* Модальное окно для трейлера */}
      {isTrailerOpen && embedUrl && (
        <div className="trailer-modal" onClick={() => setIsTrailerOpen(false)}>
          <div className="trailer-modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="close-modal" onClick={() => setIsTrailerOpen(false)}>
              ✕
            </button>
            <div className="trailer-container">
              <iframe
                src={embedUrl}
                title={`Трейлер фильма ${movie.title}`}
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
          </div>
        </div>
      )}

      <footer className="footer">
        <span>CINEMA. — Твой билет в другой мир.</span>
      </footer>
    </div>
  );
}

export default MoviePage;