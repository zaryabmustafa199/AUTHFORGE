import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Shield, Mail, AlertCircle, CheckCircle } from 'lucide-react';
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
      setError(err.response?.data?.detail || 'Failed to send reset email');
    } finally {
      setIsLoading(false);
    }
  };

  if (success) {
    return (
      <div className="auth-page">
        <div className="auth-card animate-fade-in">
          <div className="card text-center">
            <div style={{
              width: 56, height: 56, borderRadius: '50%',
              background: 'var(--success-bg)', border: '1px solid rgba(16,185,129,0.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px'
            }}>
              <Mail size={26} color="var(--success)" />
            </div>
            <h2>Check your inbox</h2>
            <p style={{ marginTop: 8, marginBottom: 24 }}>
              If an account exists for <strong style={{ color: 'var(--text-primary)' }}>{email}</strong>, a reset link has been sent.
            </p>
            <Link to="/login" className="btn btn-primary w-full">Return to Login</Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card animate-fade-in">
        <div className="card">
          <div className="auth-logo">
            <Shield size={22} color="#fff" strokeWidth={2.5} />
          </div>
          <div className="text-center mb-6">
            <h2>Reset password</h2>
            <p style={{ marginTop: 6, fontSize: '0.9rem' }}>Enter your email to receive a reset code</p>
          </div>

          {error && (
            <div className="alert alert-error">
              <AlertCircle size={15} style={{ flexShrink: 0 }} />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group" style={{ marginBottom: 24 }}>
              <label className="form-label">Email Address</label>
              <input
                type="email"
                className="form-input"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
              />
            </div>
            <button type="submit" className="btn btn-primary w-full" disabled={isLoading}>
              {isLoading ? 'Sending...' : 'Send Reset Code'}
            </button>
          </form>

          <p className="text-center mt-6" style={{ fontSize: '0.875rem' }}>
            <Link to="/login" style={{ color: 'var(--accent-hover)', fontWeight: 600, textDecoration: 'none' }}>
              ← Back to login
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default ForgotPassword;
