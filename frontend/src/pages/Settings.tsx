import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { User, LogOut, Trash2, CheckCircle, AlertCircle, Phone, Calendar, AtSign, Settings as SettingsIcon } from 'lucide-react';
import api from '../lib/api';

const Settings = () => {
  const { user, fetchProfile } = useAuth();
  
  // Profile Form State
  const [form, setForm] = useState({
    full_name: '',
    username: '',
    phone_number: '',
  });
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [profileSuccess, setProfileSuccess] = useState('');
  const [profileError, setProfileError] = useState('');
  const [isProfileSaving, setIsProfileSaving] = useState(false);

  // Sessions State
  const [sessions, setSessions] = useState<any[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);

  // Initialize form when user loads
  useEffect(() => {
    if (user) {
      setForm({
        full_name: user.full_name || '',
        username: user.username || '',
        phone_number: user.phone_number || '',
      });
    }
  }, [user]);

  // Load Sessions
  const loadSessions = async () => {
    setSessionsLoading(true);
    try {
      const res = await api.get('/sessions/');
      setSessions(res.data || []);
    } catch (err) {
      console.error('Failed to load sessions', err);
    } finally {
      setSessionsLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setProfileError('');
    setProfileSuccess('');
    setIsProfileSaving(true);

    try {
      // Only send changed fields
      const payload: any = {};
      if (form.full_name !== user?.full_name) payload.full_name = form.full_name;
      if (form.username !== user?.username) payload.username = form.username;
      if (form.phone_number !== user?.phone_number) payload.phone_number = form.phone_number;

      if (Object.keys(payload).length === 0) {
        setIsEditingProfile(false);
        setIsProfileSaving(false);
        return;
      }

      await api.patch('/users/me', payload);
      await fetchProfile();
      setProfileSuccess('Profile updated successfully');
      setIsEditingProfile(false);
      
      // Clear success message after 3 seconds
      setTimeout(() => setProfileSuccess(''), 3000);
    } catch (err: any) {
      setProfileError(err.response?.data?.detail || 'Failed to update profile');
    } finally {
      setIsProfileSaving(false);
    }
  };

  const handleRevokeSession = async (sessionId: string) => {
    try {
      await api.delete(`/sessions/${sessionId}`);
      loadSessions();
    } catch (err) {
      console.error('Failed to revoke session', err);
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <h2>Account Settings</h2>
        <p style={{ marginTop: 6 }}>Manage your profile and security preferences.</p>
      </div>

      <div className="grid-auto">
        {/* Profile Details Card */}
        <div className="card">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: 'var(--accent-light)',
                display: 'flex', alignItems: 'center', justifyContent: 'center'
              }}>
                <User size={18} color="var(--accent-hover)" />
              </div>
              <h3>Profile Details</h3>
            </div>
            {!isEditingProfile && (
              <button 
                onClick={() => setIsEditingProfile(true)}
                className="btn btn-secondary btn-sm"
              >
                Edit Profile
              </button>
            )}
          </div>

          {profileSuccess && (
            <div className="alert alert-success">
              <CheckCircle size={15} style={{ flexShrink: 0 }} />
              {profileSuccess}
            </div>
          )}

          {profileError && (
            <div className="alert alert-error">
              <AlertCircle size={15} style={{ flexShrink: 0 }} />
              {profileError}
            </div>
          )}

          {isEditingProfile ? (
            <form onSubmit={handleProfileSubmit}>
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input
                  type="text"
                  className="form-input"
                  value={form.full_name}
                  onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                  placeholder="John Doe"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Username</label>
                <div style={{ position: 'relative' }}>
                  <div style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>
                    <AtSign size={16} />
                  </div>
                  <input
                    type="text"
                    className="form-input"
                    value={form.username}
                    onChange={(e) => setForm({ ...form, username: e.target.value.toLowerCase() })}
                    placeholder="johndoe"
                    style={{ paddingLeft: 36 }}
                  />
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Phone Number</label>
                <div style={{ position: 'relative' }}>
                  <div style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>
                    <Phone size={16} />
                  </div>
                  <input
                    type="tel"
                    className="form-input"
                    value={form.phone_number}
                    onChange={(e) => setForm({ ...form, phone_number: e.target.value })}
                    placeholder="+923001234567"
                    style={{ paddingLeft: 36 }}
                  />
                </div>
                <span className="form-hint">Must be in E.164 format (e.g. +923001234567)</span>
              </div>

              <div className="form-group">
                <label className="form-label">Date of Birth</label>
                <div style={{ position: 'relative' }}>
                  <div style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>
                    <Calendar size={16} />
                  </div>
                  <input
                    type="text"
                    className="form-input"
                    value={user?.date_of_birth || 'Not set'}
                    disabled
                    style={{ paddingLeft: 36, opacity: 0.7 }}
                  />
                </div>
                <span className="form-hint">Date of birth cannot be changed after registration.</span>
              </div>

              <div className="flex gap-3 mt-6">
                <button type="submit" className="btn btn-primary flex-1" disabled={isProfileSaving}>
                  {isProfileSaving ? 'Saving...' : 'Save Changes'}
                </button>
                <button 
                  type="button" 
                  className="btn btn-secondary flex-1"
                  onClick={() => {
                    setIsEditingProfile(false);
                    // Reset form
                    if (user) {
                      setForm({
                        full_name: user.full_name || '',
                        username: user.username || '',
                        phone_number: user.phone_number || '',
                      });
                    }
                    setProfileError('');
                  }}
                  disabled={isProfileSaving}
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <div>
              <div className="stat-row">
                <span className="stat-label">Full Name</span>
                <span className="stat-value">{user?.full_name || <em style={{ color: 'var(--text-muted)' }}>Not set</em>}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Username</span>
                <span className="stat-value" style={{ fontFamily: 'monospace' }}>
                  {user?.username ? `@${user.username}` : <em style={{ color: 'var(--text-muted)' }}>Not set</em>}
                </span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Email Address</span>
                <span className="stat-value">{user?.email}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Phone Number</span>
                <span className="stat-value">{user?.phone_number || <em style={{ color: 'var(--text-muted)' }}>Not set</em>}</span>
              </div>
              <div className="stat-row">
                <span className="stat-label">Date of Birth</span>
                <span className="stat-value">{user?.date_of_birth || <em style={{ color: 'var(--text-muted)' }}>Not set</em>}</span>
              </div>
            </div>
          )}
        </div>

        {/* Security & Sessions Card */}
        <div className="card">
          <div className="flex items-center gap-3 mb-6">
            <div style={{
              width: 36, height: 36, borderRadius: 10,
              background: 'rgba(239, 68, 68, 0.12)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <SettingsIcon size={18} color="var(--danger)" />
            </div>
            <h3>Security & Devices</h3>
          </div>

          <div style={{ marginBottom: 24 }}>
            <h4 style={{ marginBottom: 12, fontSize: '0.95rem' }}>Active Sessions</h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: 16 }}>
              These devices are currently logged into your account. Revoke any sessions you don't recognize.
            </p>

            {sessionsLoading ? (
              <div className="flex justify-center" style={{ padding: '20px 0' }}>
                <div className="spinner" />
              </div>
            ) : sessions.length === 0 ? (
              <p style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No active sessions.</p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {sessions.map(session => (
                  <div key={session.id} style={{ 
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '12px 16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border)'
                  }}>
                    <div>
                      <div style={{ fontWeight: 500, fontSize: '0.9rem', marginBottom: 4 }}>
                        {session.device_info || 'Unknown Device'}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', gap: 12 }}>
                        <span>IP: {session.ip_address || '—'}</span>
                        <span>Expires: {new Date(session.expires_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    <button 
                      onClick={() => handleRevokeSession(session.id)}
                      className="btn btn-ghost btn-sm"
                      title="Revoke session"
                    >
                      <LogOut size={16} color="var(--text-secondary)" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
