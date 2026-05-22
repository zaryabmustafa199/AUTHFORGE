import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../lib/api';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await api.post('/auth/forgot-password', { email });
      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to request password reset');
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <div className="flex justify-center items-center" style={{ minHeight: '60vh' }}>
        <div className="card" style={{ maxWidth: '400px', width: '100%', textAlign: 'center' }}>
          <div style={{ width: '48px', height: '48px', borderRadius: '50%', backgroundColor: 'var(--accent-success)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px auto' }}>
            <span style={{ color: '#1e4620', fontSize: '24px' }}>✓</span>
          </div>
          <h2>Check your email</h2>
          <p style={{ marginTop: '8px', marginBottom: '24px' }}>
            If an account exists for <strong>{email}</strong>, we've sent instructions to reset your password.
          </p>
          <Link to="/login" className="btn btn-primary w-full">
            Return to Login
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-center items-center" style={{ minHeight: '60vh' }}>
      <div className="card" style={{ maxWidth: '400px', width: '100%' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <h2>Reset Password</h2>
          <p>Enter your email to receive a reset code.</p>
        </div>

        {error && <div className="error-text" style={{ marginBottom: '16px', textAlign: 'center', padding: '8px', backgroundColor: '#fdecea', borderRadius: '6px' }}>{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group" style={{ marginBottom: '24px' }}>
            <label className="form-label">Email Address</label>
            <input 
              type="email" 
              className="form-input" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required 
            />
          </div>

          <button type="submit" className="btn btn-primary w-full" disabled={isLoading}>
            {isLoading ? 'Sending...' : 'Send Reset Link'}
          </button>
        </form>

        <p style={{ textAlign: 'center', marginTop: '24px', fontSize: '0.9rem' }}>
          Remember your password? <Link to="/login" style={{ color: 'var(--text-primary)', fontWeight: '600', textDecoration: 'none' }}>Sign In</Link>
        </p>
      </div>
    </div>
  );
};

export default ForgotPassword;
