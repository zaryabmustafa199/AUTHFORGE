import React, { useState } from 'react';
import { useNavigate, Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, Mail, Lock, AlertCircle } from 'lucide-react';
import api from '../lib/api';

import loginImage from '../assets/login-bg.png';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [shake, setShake] = useState(false);
  const [searchParams] = useSearchParams();
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  React.useEffect(() => {
    const accessToken = searchParams.get('access_token');
    const refreshToken = searchParams.get('refresh_token');
    
    if (accessToken && refreshToken) {
      // OAuth Login
      login(accessToken, refreshToken).then(() => {
        navigate('/dashboard');
      });
    } else if (isAuthenticated) {
      // Normal Login check
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate, searchParams, login]);

  const triggerShake = () => {
    setShake(true);
    setTimeout(() => setShake(false), 400);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      await login(response.data.access_token, response.data.refresh_token);
      navigate('/dashboard');
    } catch (err: any) {
      if (err.response?.status === 423) {
        setError('Account temporarily locked. Too many failed attempts.');
      } else {
        setError(err.response?.data?.detail || 'Invalid email or password');
      }
      triggerShake();
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="split-layout">
      <div className="split-image animate-fade-in">
        <img src={loginImage} alt="AuthForge Login" />
      </div>
      <div className="split-form animate-fade-in">
        <div className={`auth-card-wide ${shake ? 'animate-shake' : ''}`} style={{ maxWidth: '400px' }}>
          <div className="text-center mb-6">
            <h2>Welcome back</h2>
            <p style={{ marginTop: '6px', fontSize: '0.9rem' }}>Sign in to your AuthForge account</p>
          </div>

          {error && (
            <div className="alert alert-error">
              <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input
                id="email"
                type="email"
                className="form-input"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>

            <div className="form-group" style={{ marginBottom: '8px' }}>
              <div className="flex justify-between items-center">
                <label className="form-label">Password</label>
                <Link
                  to="/forgot-password"
                  style={{ fontSize: '0.775rem', color: 'var(--accent-hover)', textDecoration: 'none', fontWeight: 500 }}
                >
                  Forgot password?
                </Link>
              </div>
              <input
                id="password"
                type="password"
                className="form-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary w-full"
              style={{ marginTop: '20px' }}
              disabled={isLoading}
            >
              {isLoading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <div className="divider">OR</div>

          <button
            onClick={() => { window.location.href = 'http://localhost:8001/api/v1/auth/oauth/google'; }}
            className="btn btn-secondary w-full"
          >
            <img
              src="https://www.svgrepo.com/show/475656/google-color.svg"
              alt="Google"
              style={{ width: '16px', height: '16px' }}
            />
            Continue with Google
          </button>

          <p className="text-center mt-6" style={{ fontSize: '0.875rem' }}>
            No account?{' '}
            <Link to="/signup" style={{ color: 'var(--accent-hover)', fontWeight: 600, textDecoration: 'none' }}>
              Create one free
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
