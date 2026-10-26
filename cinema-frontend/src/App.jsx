
import { useEffect, useState } from 'react';
import './App.css';

const API_URL = 'http://127.0.0.1:8000/api/movies/';
const API_BASE = 'http://127.0.0.1:8000';

function App() {
  const [movies, setMovies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(API_URL)
      .then((response) => {
        if (!response.ok) {
          throw new Error('Ошибка загрузки');
        }
        return response.json();
      })
      .then((data) => {
        setMovies(Array.isArray(data) ? data : data.results || []);
      })
      .catch(() => {
        setError('Не удалось загрузить фильмы. Проверь, запущен ли Django.');
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="app">
      <header className="header">
        <a className="logo" href="/">
          CINEMA<span className="logo-accent">.</span>
        </a>

        <nav className="navigation">
          <a className="active" href="#movies">Фильмы</a>
          <a href="#about">О кинотеатре</a>
        </nav>

        <button className="login-button" onClick={() => alert('Авторизация появится позже')}>
          Войти
        </button>
      </header>

      <main>
        <section className="hero">
          <div className="hero-content">
            <span className="eyebrow">ТВОЙ КИНОТЕАТР</span>
            <h1>
              Большие истории.
              <br />
              <span>Большой экран.</span>
            </h1>
            <p>
              Выбирай фильм, находи подходящий сеанс
              <br />
              и готовься к незабываемым впечатлениям.
            </p>
            <a className="primary-button" href="#movies">
              Смотреть афишу <span>→</span>
            </a>
          </div>

          <div className="hero-decoration">
            <div className="hero-circle">
              <span>▶</span>
            </div>
            <div className="hero-caption">YOUR MOVIE EXPERIENCE</div>
          </div>
        </section>

        <section className="movies-section" id="movies">
          <div className="section-heading">
            <div>
              <span className="eyebrow">СЕЙЧАС В КИНО</span>
              <h2>Афиша фильмов</h2>
            </div>
            <span className="movie-count">{movies.length} фильмов</span>
          </div>

          {loading && <p>Загружаем фильмы...</p>}
          {error && <p>{error}</p>}
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
                <article className="movie-card" key={movie.id}>
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

                    <button
                      className="poster-button"
                      onClick={() =>
                        alert(`${movie.title}\n\n${movie.description}`)
                      }
                    >
                      Подробнее
                    </button>
                  </div>

                  <div className="movie-info">
                    <p>{genres}</p>
                    <h3>{movie.title}</h3>
                    <p className="duration">{movie.duration} мин.</p>
                  </div>
                </article>
              );
            })}
          </div>
        </section>

        <section className="about-section" id="about">
          <span className="eyebrow">О НАС</span>
          <h2>Кино — это больше, чем экран</h2>
          <p>
            Выбирай фильмы, изучай расписание сеансов
            и бронируй места в несколько кликов.
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
