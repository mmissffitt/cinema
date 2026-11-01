import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import '../App.css';

const API_URL = 'http://127.0.0.1:8000/api/auth/';

function AuthPage({ mode }) {
  const isRegister = mode === 'register';
  const navigate = useNavigate();
  const location = useLocation();

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await fetch(
        `${API_URL}${isRegister ? 'register' : 'login'}/`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(
            isRegister
              ? { username, email, password }
              : { username, password },
          ),
        },
      );

      const data = await response.json();

      if (!response.ok) {
        const messages = Object.values(data).flat().join(' ');
        throw new Error(messages || 'Не удалось выполнить запрос.');
      }

      localStorage.setItem('cinemaToken', data.token);
      localStorage.setItem('cinemaUser', JSON.stringify(data.user));

      navigate(location.state?.from || '/profile');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <Link className="logo" to="/">
          CINEMA<span className="logo-accent">.</span>
        </Link>
        <nav className="navigation">
          <Link to="/">Фильмы</Link>
        </nav>
      </header>

      <main className="auth-page">
        <form className="auth-form" onSubmit={handleSubmit}>
          <span className="eyebrow">
            {isRegister ? 'НОВЫЙ АККАУНТ' : 'С РАДОСТЬЮ ВИДИМ СНОВА'}
          </span>

          <h1>{isRegister ? 'Регистрация' : 'Вход'}</h1>

          <p className="auth-description">
            {isRegister
              ? 'Создай аккаунт, чтобы бронировать места и управлять билетами.'
              : 'Войди в аккаунт, чтобы продолжить бронирование.'}
          </p>

          <label htmlFor="username">Логин</label>
          <input
            id="username"
            type="text"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
            autoComplete="username"
          />

          {isRegister && (
            <>
              <label htmlFor="email">Электронная почта</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
              />
            </>
          )}

          <label htmlFor="password">Пароль</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            minLength={isRegister ? 8 : undefined}
            autoComplete={isRegister ? 'new-password' : 'current-password'}
          />

          {error && <p className="form-error">{error}</p>}

          <button
            className="primary-button auth-submit"
            type="submit"
            disabled={loading}
          >
            {loading
              ? 'Подождите...'
              : isRegister
                ? 'Создать аккаунт →'
                : 'Войти →'}
          </button>

          <p className="auth-switch">
            {isRegister ? 'Уже есть аккаунт?' : 'Ещё нет аккаунта?'}
            {' '}
            <Link to={isRegister ? '/login' : '/register'}>
              {isRegister ? 'Войти' : 'Зарегистрироваться'}
            </Link>
          </p>
        </form>
      </main>

      <footer className="footer">
        <span>CINEMA. — Твой билет в другой мир.</span>
      </footer>
    </div>
  );
}

export default AuthPage;