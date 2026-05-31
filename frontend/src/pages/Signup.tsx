import React, { useState, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Shield, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import api from '../lib/api';

import signupImage from '../assets/signup-bg.png';

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

const Signup = () => {
  const [form, setForm] = useState({
    email: '',
    username: '',
    full_name: '',
    phone_number: '',
    date_of_birth: '',
    password: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [globalError, setGlobalError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [usernameStatus, setUsernameStatus] = useState<'idle' | 'checking' | 'available' | 'taken'>('idle');
  const [usernameTimer, setUsernameTimer] = useState<ReturnType<typeof setTimeout> | null>(null);
  
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  React.useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm(f => ({ ...f, [field]: e.target.value }));
    setErrors(er => ({ ...er, [field]: '' }));
  };

  const checkUsername = useCallback((val: string) => {
    if (usernameTimer) clearTimeout(usernameTimer);
    if (!val || val.length < 3) { setUsernameStatus('idle'); return; }
    setUsernameStatus('checking');
    const t = setTimeout(async () => {
      try {
        const res = await api.get(`/auth/check-username?username=${encodeURIComponent(val)}`);
        setUsernameStatus(res.data.available ? 'available' : 'taken');
      } catch {
        setUsernameStatus('idle');
      }
    }, 500);
    setUsernameTimer(t);
  }, [usernameTimer]);

  const handleUsernameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setForm(f => ({ ...f, username: val }));
    setErrors(er => ({ ...er, username: '' }));
    checkUsername(val);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setGlobalError('');
    setErrors({});
    setIsLoading(true);

    const body: any = {
      email: form.email,
      username: form.username,
      full_name: form.full_name,
      password: form.password,
    };
    if (form.phone_number) body.phone_number = form.phone_number;
    if (form.date_of_birth) body.date_of_birth = form.date_of_birth;

    try {
      await api.post('/auth/signup', body);
      setSuccess(true);
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        const fieldMap: Record<string, string> = {};
        detail.forEach((d: any) => {
          const field = d.loc?.[d.loc.length - 1];
          if (field) fieldMap[field] = d.msg.replace('Value error, ', '');
        });
        setErrors(fieldMap);
      } else if (typeof detail === 'string') {
        setGlobalError(detail);
      } else {
        setGlobalError('Failed to create account. Please try again.');
      }
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
              <CheckCircle size={28} color="var(--success)" />
            </div>
            <h2>Check your email</h2>
            <p style={{ marginTop: 8, marginBottom: 24 }}>
              We sent a verification code to <strong style={{ color: 'var(--text-primary)' }}>{form.email}</strong>
            </p>
            <Link
              to={`/verify-email?email=${encodeURIComponent(form.email)}`}
              className="btn btn-primary w-full"
            >
              Enter Verification Code
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="split-layout">
      <div className="split-image animate-fade-in">
        <img src={signupImage} alt="AuthForge Bodyguard" />
      </div>
      <div className="split-form animate-fade-in">
        <div className="auth-card-wide" style={{ maxWidth: '440px' }}>
          <div className="text-center mb-6">
            <h2>Create your account</h2>
            <p style={{ marginTop: 6, fontSize: '0.9rem' }}>Join AuthForge — it's free</p>
          </div>

          {globalError && (
            <div className="alert alert-error">
              <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
              {globalError}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {/* Row 1: Full Name + Username */}
            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Full Name *</label>
                <input
                  type="text"
                  className={`form-input ${errors.full_name ? 'error' : ''}`}
                  placeholder="John Doe"
                  value={form.full_name}
                  onChange={set('full_name')}
                  required
                />
                {errors.full_name && <span className="field-error"><AlertCircle size={11} />{errors.full_name}</span>}
              </div>

              <div className="form-group">
                <label className="form-label">Username *</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type="text"
                    className={`form-input ${errors.username ? 'error' : usernameStatus === 'available' ? 'success' : usernameStatus === 'taken' ? 'error' : ''}`}
                    placeholder="johndoe"
                    value={form.username}
                    onChange={handleUsernameChange}
                    required
                    autoComplete="off"
                  />
                  {usernameStatus === 'available' && (
                    <CheckCircle size={16} color="var(--success)" style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)' }} />
                  )}
                  {usernameStatus === 'taken' && (
                    <XCircle size={16} color="var(--danger)" style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)' }} />
                  )}
                </div>
                {errors.username && <span className="field-error"><AlertCircle size={11} />{errors.username}</span>}
                {!errors.username && usernameStatus === 'available' && <span className="field-success"><CheckCircle size={11} />Available</span>}
                {!errors.username && usernameStatus === 'taken' && <span className="field-error"><XCircle size={11} />Username taken</span>}
              </div>
            </div>

            {/* Email */}
            <div className="form-group">
              <label className="form-label">Email Address *</label>
              <input
                type="email"
                className={`form-input ${errors.email ? 'error' : ''}`}
                placeholder="you@example.com"
                value={form.email}
                onChange={set('email')}
                required
                autoComplete="email"
              />
              {errors.email && <span className="field-error"><AlertCircle size={11} />{errors.email}</span>}
            </div>

            {/* Row 2: Phone + DOB */}
            <div className="grid-2">
              <div className="form-group">
                <label className="form-label">Phone Number</label>
                <input
                  type="tel"
                  className={`form-input ${errors.phone_number ? 'error' : ''}`}
                  placeholder="+923001234567"
                  value={form.phone_number}
                  onChange={set('phone_number')}
                />
                {errors.phone_number
                  ? <span className="field-error"><AlertCircle size={11} />{errors.phone_number}</span>
                  : <span className="form-hint">E.164 format with country code</span>
                }
              </div>

              <div className="form-group">
                <label className="form-label">Date of Birth</label>
                <input
                  type="date"
                  className={`form-input ${errors.date_of_birth ? 'error' : ''}`}
                  value={form.date_of_birth}
                  onChange={set('date_of_birth')}
                  max={new Date(new Date().setFullYear(new Date().getFullYear() - 13)).toISOString().split('T')[0]}
                />
                {errors.date_of_birth && <span className="field-error"><AlertCircle size={11} />{errors.date_of_birth}</span>}
              </div>
            </div>

            {/* Password */}
            <div className="form-group">
              <label className="form-label">Password *</label>
              <input
                type="password"
                className={`form-input ${errors.password ? 'error' : ''}`}
                placeholder="Min. 8 characters"
                value={form.password}
                onChange={set('password')}
                required
                minLength={8}
                autoComplete="new-password"
              />
              <PasswordRequirements password={form.password} />
              {errors.password && <span className="field-error"><AlertCircle size={11} />{errors.password}</span>}
            </div>

            <button
              type="submit"
              className="btn btn-primary w-full"
              style={{ marginTop: '8px' }}
              disabled={isLoading || usernameStatus === 'taken'}
            >
              {isLoading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>

          <div className="divider">OR</div>

          <button
            onClick={() => { window.location.href = 'http://localhost:8001/api/v1/auth/oauth/google'; }}
            className="btn btn-secondary w-full"
          >
            <img src="https://www.svgrepo.com/show/475656/google-color.svg" alt="Google" style={{ width: 16, height: 16 }} />
            Continue with Google
          </button>

          <p className="text-center mt-6" style={{ fontSize: '0.875rem' }}>
            Already have an account?{' '}
            <Link to="/login" style={{ color: 'var(--accent-hover)', fontWeight: 600, textDecoration: 'none' }}>
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Signup;
