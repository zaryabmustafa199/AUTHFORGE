import React, { useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { Shield, AlertCircle, CheckCircle } from 'lucide-react';
import api from '../lib/api';

const PasswordRequirements = ({ password }: { password: string }) => {
  if (!password) return null;
  const requirements = [
    { label: 'At least 8 characters', met: password.length >= 8 },
    { label: 'At least one uppercase letter', met: /[A-Z]/.test(password) },
    { label: 'At least one lowercase letter', met: /[a-z]/.test(password) },
    { label: 'At least one number', met: /[0-9]/.test(password) },
    { label: 'At least one special character', met: /[^A-Za-z0-9]/.test(password) }
  ];

  return (
    <div style={{ marginTop: 12, fontSize: '0.8rem', display: 'flex', flexDirection: 'column', gap: 6 }}>
      {requirements.map((req, i) => (
        <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, color: req.met ? 'var(--success)' : 'var(--text-muted)', transition: 'color 0.2s' }}>
          {req.met ? <CheckCircle size={14} /> : <div style={{ width: 14, height: 14, borderRadius: '50%', border: '1px solid var(--text-muted)' }} />}
          <span>{req.label}</span>
        </div>
      ))}
    </div>
  );
};

const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const urlEmail = searchParams.get('email') || '';

  const [email, setEmail] = useState(urlEmail);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    setIsLoading(true);
    try {
      await api.post('/auth/reset-password', {
        email,
        token,
        new_password: newPassword,
      });
      setSuccess(true);
      setTimeout(() => navigate('/login'), 2500);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setError(detail);
      } else if (Array.isArray(detail)) {
        setError(detail[0].msg || 'Failed to reset password');
      } else {
        setError('Failed to reset password. The link may have expired.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="auth-page">
        <div className="auth-card animate-fade-in">
          <div className="card text-center">
            <h2 style={{ color: 'var(--danger)' }}>Invalid Link</h2>
            <p style={{ marginTop: 8, marginBottom: 24 }}>
              This password reset link is missing or invalid.
            </p>
            <Link to="/forgot-password" className="btn btn-primary w-full">
              Request New Reset Link
            </Link>
          </div>
        </div>
      </div>
    );
  }

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
              <CheckCircle size={28} color="var(--success)" />
            </div>
            <h2>Password reset!</h2>
            <p style={{ marginTop: 8 }}>Redirecting you to login...</p>
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
            <h2>Choose new password</h2>
            <p style={{ marginTop: 6, fontSize: '0.9rem' }}>Enter your email and a new password</p>
          </div>

          {error && (
            <div className="alert alert-error">
              <AlertCircle size={15} style={{ flexShrink: 0 }} />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input
                type="email"
                className="form-input"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                readOnly={!!urlEmail}
                style={urlEmail ? { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-muted)' } : {}}
              />
            </div>

            <div className="form-group">
              <label className="form-label">New Password</label>
              <input
                type="password"
                className="form-input"
                placeholder="Min. 8 characters"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
                autoFocus
              />
              <PasswordRequirements password={newPassword} />
            </div>

            <div className="form-group" style={{ marginBottom: 24, marginTop: 16 }}>
              <label className="form-label">Confirm New Password</label>
              <input
                type="password"
                className="form-input"
                placeholder="Re-type new password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary w-full"
              disabled={isLoading}
            >
              {isLoading ? 'Resetting...' : 'Reset Password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ResetPassword;
