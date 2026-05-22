import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../lib/api';

const Settings = () => {
  const { user, fetchProfile } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [sessions, setSessions] = useState<any[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState('');

  const loadSessions = async () => {
    try {
      const res = await api.get('/sessions/');
      setSessions(res.data.sessions || []);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setMessage('');
    try {
      await api.patch('/users/me', { full_name: fullName });
      await fetchProfile();
      setMessage('Profile updated successfully.');
    } catch (err) {
      setMessage('Failed to update profile.');
    } finally {
      setIsSaving(false);
    }
  };

  const handleRevokeSession = async (sessionId: string) => {
    try {
      await api.delete(`/sessions/${sessionId}`);
      await loadSessions();
    } catch (err) {
      console.error('Failed to revoke session', err);
    }
  };

  return (
    <div className="flex-col gap-6">
      <div style={{ marginBottom: '24px' }}>
        <h2>Settings</h2>
        <p>Manage your profile and security settings.</p>
      </div>

      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ marginBottom: '24px' }}>Profile Information</h3>
        {message && <div style={{ marginBottom: '16px', padding: '8px', backgroundColor: 'var(--bg-secondary)', borderRadius: '6px', fontSize: '0.9rem', color: 'var(--text-primary)' }}>{message}</div>}
        
        <form onSubmit={handleUpdateProfile} style={{ maxWidth: '400px' }}>
          <div className="form-group" style={{ marginBottom: '16px' }}>
            <label className="form-label">Email Address</label>
            <input type="email" className="form-input" value={user?.email || ''} disabled style={{ backgroundColor: 'var(--bg-secondary)', color: 'var(--text-secondary)' }} />
          </div>
          
          <div className="form-group" style={{ marginBottom: '24px' }}>
            <label className="form-label">Full Name</label>
            <input 
              type="text" 
              className="form-input" 
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="John Doe"
            />
          </div>

          <button type="submit" className="btn btn-primary" disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save Changes'}
          </button>
        </form>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: '24px' }}>Active Sessions</h3>
        <p style={{ marginBottom: '24px', fontSize: '0.9rem' }}>Review and revoke your active devices.</p>
        
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Device</th>
                <th>IP Address</th>
                <th>Expires</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr key={session.id}>
                  <td style={{ fontWeight: 500 }}>{session.device_info}</td>
                  <td>{session.ip_address}</td>
                  <td>{new Date(session.expires_at).toLocaleString()}</td>
                  <td>
                    <button 
                      onClick={() => handleRevokeSession(session.id)}
                      className="btn btn-danger"
                      style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Settings;
