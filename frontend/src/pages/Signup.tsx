import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../lib/api';

const Signup = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await api.post('/auth/signup', { email, password });
      setSuccess(true);
    } catch (err: any) {
      if (typeof err.response?.data?.detail === 'string') {
        setError(err.response.data.detail);
      } else if (Array.isArray(err.response?.data?.detail)) {
        setError(err.response.data.detail[0].msg);
      } else {
        setError('Failed to create account');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleGoogleSignup = () => {
    window.location.href = 'http://localhost:8001/api/v1/auth/oauth/google';
  };

  if (success) {
    return (
      <div className="flex justify-center items-center" style={{ minHeight: '70vh' }}>
        <div className="card" style={{ maxWidth: '400px', width: '100%', textAlign: 'center' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '50%', backgroundColor: 'var(--accent-success)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px auto' }}>
            <span style={{ color: '#1e4620', fontSize: '24px' }}>✓</span>
          </div>
          <h2>Check your email</h2>
          <p style={{ marginTop: '8px', marginBottom: '24px' }}>
            We've sent an OTP verification code to <strong>{email}</strong>.
          </p>
          <Link to={`/verify-email?email=${encodeURIComponent(email)}`} className="btn btn-primary w-full">
            Enter Verification Code
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-center items-center" style={{ minHeight: '70vh' }}>
      <div className="card" style={{ maxWidth: '400px', width: '100%' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <h2>Create an Account</h2>
          <p>Join AuthForge today</p>
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
            <label className="form-label">Password</label>
            <input 
              type="password" 
              className="form-input" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required 
              minLength={8}
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Must be at least 8 characters long.</span>
          </div>

          <button type="submit" className="btn btn-primary w-full" disabled={isLoading}>
            {isLoading ? 'Creating account...' : 'Sign Up'}
          </button>
        </form>

        <div style={{ margin: '24px 0', textAlign: 'center', position: 'relative' }}>
          <hr style={{ border: 'none', borderTop: '1px solid var(--border-light)' }} />
          <span style={{ position: 'absolute', top: '-10px', left: '50%', transform: 'translateX(-50%)', backgroundColor: 'var(--surface-primary)', padding: '0 10px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>OR</span>
        </div>

        <button onClick={handleGoogleSignup} className="btn btn-secondary w-full">
          <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="Google" style={{ width: '18px', height: '18px' }} />
          Continue with Google
        </button>

        <p style={{ textAlign: 'center', marginTop: '24px', fontSize: '0.9rem' }}>
          Already have an account? <Link to="/login" style={{ color: 'var(--text-primary)', fontWeight: '600', textDecoration: 'none' }}>Sign In</Link>
        </p>
      </div>
    </div>
  );
};

export default Signup;
