import React, { useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import api from '../lib/api';

const VerifyEmail = () => {
  const [searchParams] = useSearchParams();
  const emailParam = searchParams.get('email') || '';
  
  const [email, setEmail] = useState(emailParam);
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await api.post('/auth/verify-email', { email, otp });
      setSuccess('Email verified successfully! Redirecting to login...');
      setTimeout(() => navigate('/login'), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid verification code');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex justify-center items-center" style={{ minHeight: '60vh' }}>
      <div className="card" style={{ maxWidth: '400px', width: '100%' }}>
        <div style={{ textAlign: 'center', marginBottom: '24px' }}>
          <h2>Verify Email</h2>
          <p>Enter the 6-digit code sent to your email</p>
        </div>

        {error && <div className="error-text" style={{ marginBottom: '16px', textAlign: 'center', padding: '8px', backgroundColor: '#fdecea', borderRadius: '6px' }}>{error}</div>}
        {success && <div style={{ color: '#1e4620', marginBottom: '16px', textAlign: 'center', padding: '8px', backgroundColor: 'var(--accent-success)', borderRadius: '6px' }}>{success}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input 
              type="email" 
              className="form-input" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required 
              disabled={!!emailParam}
              style={emailParam ? { backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' } : {}}
            />
          </div>
          
          <div className="form-group" style={{ marginBottom: '24px' }}>
            <label className="form-label">Verification Code (OTP)</label>
            <input 
              type="text" 
              className="form-input" 
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').substring(0, 6))}
              required 
              maxLength={6}
              placeholder="123456"
              style={{ letterSpacing: '0.25em', textAlign: 'center', fontSize: '1.25rem', fontWeight: 'bold' }}
            />
          </div>

          <button type="submit" className="btn btn-primary w-full" disabled={isLoading || !!success || otp.length !== 6}>
            {isLoading ? 'Verifying...' : 'Verify Email'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default VerifyEmail;
