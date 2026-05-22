import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../lib/api';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.append('username', email);
      formData.append('password', password);

      const response = await api.post('/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      
      login(response.data.access_token, response.data.refresh_token);
      navigate('/dashboard');
    } catch (err: any) {
      if (err.response?.status === 423) {
        setError('Account locked due to too many failed attempts. Try again later.');
      } else {
        setError(err.response?.data?.detail || 'Invalid email or password');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = 'http://localhost:8001/api/v1/auth/oauth/google';
  };

  return (
    <div className="flex justify-center items-center" style={{ minHeight: '70vh' }}>
      <div className="card" style={{ maxWidth: '400px', width: '100%' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <h2>Welcome Back</h2>
          <p>Sign in to continue to AuthForge</p>
        </div>

        {error && <div className="error-text" style={{ marginBottom: '16px', textAlign: 'center', padding: '8px', backgroundColor: '#fdecea', borderRadius: '6px' }}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input 
              type="email" 
              className="form-input" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required 
            />
          </div>
          
          <div className="form-group" style={{ marginBottom: '24px' }}>
            <div className="flex justify-between items-center">
              <label className="form-label">Password</label>
              <Link to="/forgot-password" style={{ fontSize: '0.85rem', color: 'var(--accent-primary)', textDecoration: 'none' }}>Forgot Password?</Link>
            </div>
            <input 
              type="password" 
              className="form-input" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required 
            />
          </div>

          <button type="submit" className="btn btn-primary w-full" disabled={isLoading}>
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <div style={{ margin: '24px 0', textAlign: 'center', position: 'relative' }}>
          <hr style={{ border: 'none', borderTop: '1px solid var(--border-light)' }} />
          <span style={{ position: 'absolute', top: '-10px', left: '50%', transform: 'translateX(-50%)', backgroundColor: 'var(--surface-primary)', padding: '0 10px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>OR</span>
        </div>

        <button onClick={handleGoogleLogin} className="btn btn-secondary w-full">
          <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="Google" style={{ width: '18px', height: '18px' }} />
          Continue with Google
        </button>

        <p style={{ textAlign: 'center', marginTop: '24px', fontSize: '0.9rem' }}>
          Don't have an account? <Link to="/signup" style={{ color: 'var(--text-primary)', fontWeight: '600', textDecoration: 'none' }}>Sign Up</Link>
        </p>
      </div>
    </div>
  );
};

export default Login;
