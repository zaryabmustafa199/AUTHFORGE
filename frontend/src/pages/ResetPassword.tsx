import React, { useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import api from '../lib/api';

const ResetPassword = () => {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  
  const [newPassword, setNewPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await api.post('/auth/reset-password', { token, new_password: newPassword });
      setSuccess('Password has been successfully reset. Redirecting to login...');
      setTimeout(() => navigate('/login'), 2000);
    } catch (err: any) {
      if (typeof err.response?.data?.detail === 'string') {
        setError(err.response.data.detail);
      } else if (Array.isArray(err.response?.data?.detail)) {
        setError(err.response.data.detail[0].msg);
      } else {
        setError('Failed to reset password');
      }
    } finally {
      setIsLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="flex justify-center items-center" style={{ minHeight: '60vh' }}>
        <div className="card" style={{ maxWidth: '400px', width: '100%', textAlign: 'center' }}>
          <h2>Invalid Link</h2>
          <p style={{ marginTop: '8px', marginBottom: '24px' }}>
            This password reset link is invalid or missing the security token.
          </p>
          <Link to="/forgot-password" className="btn btn-primary w-full">
            Request New Link
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-center items-center" style={{ minHeight: '60vh' }}>
      <div className="card" style={{ maxWidth: '400px', width: '100%' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <h2>Choose New Password</h2>
          <p>Please enter your new password.</p>
        </div>

        {error && <div className="error-text" style={{ marginBottom: '16px', textAlign: 'center', padding: '8px', backgroundColor: '#fdecea', borderRadius: '6px' }}>{error}</div>}
        {success && <div style={{ color: '#1e4620', marginBottom: '16px', textAlign: 'center', padding: '8px', backgroundColor: 'var(--accent-success)', borderRadius: '6px' }}>{success}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group" style={{ marginBottom: '24px' }}>
            <label className="form-label">New Password</label>
            <input 
              type="password" 
              className="form-input" 
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required 
              minLength={8}
            />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Must be at least 8 characters long.</span>
          </div>

          <button type="submit" className="btn btn-primary w-full" disabled={isLoading || !!success}>
            {isLoading ? 'Resetting...' : 'Reset Password'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default ResetPassword;
