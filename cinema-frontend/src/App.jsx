import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import './App.css';

const API_URL = 'http://127.0.0.1:8000/api/movies/';
const API_BASE = 'http://127.0.0.1:8000';

function App() {
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [user, setUser] = useState(null);

  useEffect(() => {
    fetch(API_URL)
      .then((response) => {
        if (!response.ok) throw new Error('Ошибка загрузки');
        return response.json();
      })
      .then((data) => {
        setMovies(Array.isArray(data) ? data : data.results || []);
      })
      .catch(() => {
        setError('Не удалось загрузить фильмы. Проверь, запущен ли Django.');
      })
      .finally(() => setLoading(false));

    const token = localStorage.getItem('cinemaToken');

    if (token) {
      fetch(`${API_BASE}/api/auth/me/`, {
        headers: { Authorization: `Token ${token}` },
      })
        .then((response) => {
          if (!response.ok) throw new Error();
          return response.json();
        })
        .then(setUser)
        .catch(() => {
          localStorage.removeItem('cinemaToken');
          localStorage.removeItem('cinemaUser');
        });
    }
  }, []);

  // Берем первый фильм как главную премьеру для баннера
  const featuredMovie = movies.length > 0 ? movies[0] : null;

  const featuredPosterUrl = featuredMovie?.poster
    ? featuredMovie.poster.startsWith('http')
      ? featuredMovie.poster
      : `${API_BASE}${featuredMovie.poster}`
    : null;

  return (
    <div className="app">
      <header className="header">
        <Link className="logo" to="/">
          CINEMA<span className="logo-accent">.</span>
        </Link>

        <nav className="navigation">
          <a className="active" href="#movies">Афиша</a>
          <a href="#about">О кинотеатре</a>
        </nav>

        {user ? (
          <Link className="login-button" to="/profile">
            {user.username}
          </Link>
        ) : (
          <Link className="login-button" to="/login">
            Войти
          </Link>
        )}
      </header>

      <main>
        {/* Кинематографичный баннер премьеры дня */}
        <section className="hero-banner">
          {featuredMovie ? (
            <>
              {featuredPosterUrl && (
                <div
                  className="hero-backdrop"
                  style={{ backgroundImage: `url(${featuredPosterUrl})` }}
                />
              )}
              <div className="hero-overlay" />
              <div className="hero-container">
                <div className="hero-content">
                  <span className="eyebrow">ПРЕМЬЕРА НЕДЕЛИ</span>
                  <h1>{featuredMovie.title}</h1>
                  <p className="hero-meta">
                    {featuredMovie.genres?.map((g) => g.name).join(' · ')}
                    {featuredMovie.duration ? ` · ${featuredMovie.duration} мин.` : ''}
                    {featuredMovie.age_rating ? ` · ${featuredMovie.age_rating}` : ''}
                  </p>
                  <p className="hero-desc">
                    {featuredMovie.description || 'Главная премьера на большом экране. Погрузитесь в незабываемую историю вместе с нашим кинотеатром.'}
                  </p>
                  <div className="hero-buttons">
                    <Link className="primary-button" to={`/movies/${featuredMovie.id}`}>
                      Выбрать сеанс <span>→</span>
                    </Link>
                    {featuredMovie.trailer_url && (
                      <a
                        className="secondary-button"
                        href={featuredMovie.trailer_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        ▶ Смотреть трейлер
                      </a>
                    )}
                  </div>
                </div>

                {featuredPosterUrl && (
                  <div className="hero-poster-preview">
                    <img src={featuredPosterUrl} alt={featuredMovie.title} />
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="hero-loading">
              {loading ? 'Загрузка афиши...' : 'Добавьте фильмы в панели администратора Django'}
            </div>
          )}
        </section>

        <section className="movies-section" id="movies">
          <div className="section-heading">
            <div>
              <span className="eyebrow">СЕЙЧАС В ПРОКАТЕ</span>
              <h2>Афиша фильмов</h2>
            </div>
            <span className="movie-count">{movies.length} фильмов</span>
          </div>

          {loading && <p>Загружаем фильмы...</p>}
          {error && <p className="form-error">{error}</p>}

          {!loading && !error && movies.length === 0 && (
            <p>Пока фильмов нет. Добавь их через панель администратора.</p>
          )}

          <div className="movie-grid">
            {movies.map((movie) => {
              const posterUrl = movie.poster
                ? movie.poster.startsWith('http')
                  ? movie.poster
                  : `${API_BASE}${movie.poster}`
                : null;

              const genres = movie.genres?.length
                ? movie.genres.map((genre) => genre.name).join(' · ')
                : 'Жанр не указан';

              return (
                <Link
                  className="movie-card"
                  key={movie.id}
                  to={`/movies/${movie.id}`}
                  aria-label={`Открыть фильм «${movie.title}»`}
                >
                  <div className="poster-wrap">
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

                    <span className="rating">{movie.age_rating}</span>
                    <span className="poster-button">Подробнее</span>
                  </div>

                  <div className="movie-info">
                    <p>{genres}</p>
                    <h3>{movie.title}</h3>
                    <p className="duration">{movie.duration} мин.</p>
                  </div>
                </Link>
              );
            })}
          </div>
        </section>

        <section className="about-section" id="about">
          <span className="eyebrow">О КИНОТЕАТРЕ</span>
          <h2>Магия большого экрана в <em>каждом сеансе</em></h2>
          <p>
            Выбирайте лучшие места, наслаждайтесь звуком Dolby Atmos
            и бронируйте билеты в пару кликов.
          </p>
        </section>
      </main>

      <footer className="footer">
        <span>CINEMA. — Твой билет в другой мир.</span>
      </footer>
    </div>
  );
}

export default App;