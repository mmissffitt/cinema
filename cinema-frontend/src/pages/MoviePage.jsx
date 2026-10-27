
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import '../App.css';

const API_URL = 'http://127.0.0.1:8000/api/movies/';
const API_BASE = 'http://127.0.0.1:8000';

function MoviePage() {
  const { id } = useParams();
  const [movie, setMovie] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(`${API_URL}${id}/`)
      .then((response) => {
        if (!response.ok) {
          throw new Error('Фильм не найден');
        }
        return response.json();
      })
      .then(setMovie)
      .catch(() => setError('Не удалось загрузить информацию о фильме.'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return <div className="app"><p>Загружаем фильм...</p></div>;
  }

  if (error || !movie) {
    return (
      <div className="app">
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

  return (
    <div className="app">
      <header className="header">
        <Link className="logo" to="/">
          CINEMA<span className="logo-accent">.</span>
        </Link>

        <nav className="navigation">
          <Link to="/">Фильмы</Link>
          <a href="/#about">О кинотеатре</a>
        </nav>

        <button
          className="login-button"
          onClick={() => alert('Авторизация появится позже')}
        >
          Войти
        </button>
      </header>

      <main className="movies-section">
        <Link to="/">← Назад к афише</Link>

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

            {movie.trailer_url && (
              <a
                className="primary-button"
                href={movie.trailer_url}
                target="_blank"
                rel="noreferrer"
              >
                Смотреть трейлер →
              </a>
            )}
          </div>
        </div>
      </main>

      <footer className="footer">
        <span>CINEMA. — Твой билет в другой мир.</span>
      </footer>
    </div>
  );
}

export default MoviePage;
