import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, Clock } from 'lucide-react';
import api from '../lib/api';

const Dashboard = () => {
  const { user } = useAuth();
  const [sessions, setSessions] = useState<any[]>([]);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const res = await api.get('/sessions/');
        setSessions(res.data.sessions || []);
      } catch (err) {
        console.error('Failed to load sessions', err);
      }
    };
    fetchSessions();
  }, []);

  return (
    <div className="flex-col gap-6">
      <div style={{ marginBottom: '24px' }}>
        <h2>Dashboard</h2>
        <p>Welcome back, {user?.full_name || user?.email}</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '24px' }}>
        {/* Profile Summary Card */}
        <div className="card">
          <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Shield size={20} color="var(--accent-primary)" /> Account Status
          </h3>
          <div className="flex-col gap-4">
            <div className="flex justify-between items-center" style={{ paddingBottom: '12px', borderBottom: '1px solid var(--border-light)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Email</span>
              <span className="flex items-center gap-2" style={{ fontWeight: 500 }}>
                {user?.email} 
                {user?.is_verified && <span className="badge badge-success">Verified</span>}
              </span>
            </div>
            <div className="flex justify-between items-center" style={{ paddingBottom: '12px', borderBottom: '1px solid var(--border-light)' }}>
              <span style={{ color: 'var(--text-secondary)' }}>Role</span>
              <span className="badge badge-primary">{user?.role_id === 3 ? 'Admin' : user?.role_id === 2 ? 'Moderator' : 'User'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span style={{ color: 'var(--text-secondary)' }}>Status</span>
              <span className="badge badge-success">Active</span>
            </div>
          </div>
        </div>

        {/* Active Sessions Card */}
        <div className="card">
          <h3 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Clock size={20} color="var(--accent-primary)" /> Active Devices
          </h3>
          <div className="flex-col gap-4">
            {sessions.slice(0, 3).map((session) => (
              <div key={session.id} className="flex justify-between items-center" style={{ paddingBottom: '12px', borderBottom: '1px solid var(--border-light)' }}>
                <div className="flex-col">
                  <span style={{ fontWeight: 500, fontSize: '0.95rem' }}>{session.device_info}</span>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>IP: {session.ip_address}</span>
                </div>
                <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                  Expires: {new Date(session.expires_at).toLocaleDateString()}
                </span>
              </div>
            ))}
            {sessions.length > 3 && (
              <div style={{ textAlign: 'center', fontSize: '0.85rem', marginTop: '8px' }}>
                <a href="/settings" style={{ color: 'var(--accent-primary)', textDecoration: 'none', fontWeight: 500 }}>View all {sessions.length} sessions in Settings &rarr;</a>
              </div>
            )}
            {sessions.length === 0 && <p style={{ fontSize: '0.85rem' }}>Loading active sessions...</p>}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
