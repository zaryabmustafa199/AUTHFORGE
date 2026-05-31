import React, { useState, useRef, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Shield, CheckCircle, AlertCircle } from 'lucide-react';
import api from '../lib/api';

import verifyImage from '../assets/verify-bg.png';

const VerifyEmail = () => {
  const [searchParams] = useSearchParams();
  const emailParam = searchParams.get('email') || '';
  const [email, setEmail] = useState(emailParam);
  const [digits, setDigits] = useState<string[]>(['', '', '', '', '', '']);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const navigate = useNavigate();

  const otp = digits.join('');
  const isFilled = otp.length === 6;

  // Auto-submit when all 6 boxes are filled
  useEffect(() => {
    if (isFilled && !isLoading && !success) {
      handleSubmit();
    }
  }, [otp]);

  const handleDigitChange = (index: number, value: string) => {
    const char = value.replace(/\D/g, '').slice(-1);
    const next = [...digits];
    next[index] = char;
    setDigits(next);
    setError('');
    if (char && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pasted.length > 0) {
      const next = Array(6).fill('');
      pasted.split('').forEach((c, i) => { next[i] = c; });
      setDigits(next);
      inputRefs.current[Math.min(pasted.length, 5)]?.focus();
    }
  };

  const handleSubmit = async () => {
    if (!isFilled || isLoading) return;
    setError('');
    setIsLoading(true);
    try {
      await api.post('/auth/verify-email', { email, otp });
      setSuccess(true);
      setTimeout(() => navigate('/login'), 2200);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid verification code');
      setDigits(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
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
              width: 60, height: 60, borderRadius: '50%',
              background: 'var(--success-bg)', border: '1px solid rgba(16,185,129,0.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px'
            }}>
              <CheckCircle size={30} color="var(--success)" />
            </div>
            <h2>Email verified!</h2>
            <p style={{ marginTop: 8 }}>Redirecting you to login...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="split-layout">
      <div className="split-image animate-fade-in">
        <img src={verifyImage} alt="Verify Email" />
      </div>
      <div className="split-form animate-fade-in">
        <div className="auth-card-wide" style={{ maxWidth: '420px' }}>
          <div className="text-center mb-6">
            <h2>Verify your email</h2>
            <p style={{ marginTop: 6, fontSize: '0.9rem' }}>
              Enter the 6-digit code sent to{' '}
              <strong style={{ color: 'var(--text-primary)' }}>{email || 'your email'}</strong>
            </p>
          </div>

          {!emailParam && (
            <div className="form-group mb-4">
              <label className="form-label">Email Address</label>
              <input
                type="email"
                className="form-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </div>
          )}

          {error && (
            <div className="alert alert-error mb-4">
              <AlertCircle size={15} style={{ flexShrink: 0 }} />
              {error}
            </div>
          )}

          <div className="otp-container" onPaste={handlePaste}>
            {digits.map((d, i) => (
              <input
                key={i}
                ref={el => { inputRefs.current[i] = el; }}
                className={`otp-input ${d ? 'filled' : ''}`}
                type="text"
                inputMode="numeric"
                maxLength={1}
                value={d}
                onChange={(e) => handleDigitChange(i, e.target.value)}
                onKeyDown={(e) => handleKeyDown(i, e)}
                autoFocus={i === 0}
              />
            ))}
          </div>

          <button
            className="btn btn-primary w-full"
            style={{ marginTop: 24 }}
            onClick={handleSubmit}
            disabled={!isFilled || isLoading}
          >
            {isLoading ? 'Verifying...' : 'Verify Email'}
          </button>

          <p className="text-center mt-4" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Code expires in 10 minutes. Check your spam folder if needed.
          </p>
        </div>
      </div>
    </div>
  );
};

export default VerifyEmail;
