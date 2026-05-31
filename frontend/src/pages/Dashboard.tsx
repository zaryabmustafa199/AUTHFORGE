import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, Monitor, Clock, User, CheckCircle, AlertCircle, TrendingUp } from 'lucide-react';
import api from '../lib/api';

import dashboardImage from '../assets/dashboard-bg.png';

const Dashboard = () => {
  const { user } = useAuth();
  const [sessions, setSessions] = useState<any[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const res = await api.get('/sessions/');
        setSessions(res.data || []);
      } catch (err) {
        console.error('Failed to load sessions', err);
      } finally {
        setSessionsLoading(false);
      }
    };
    fetchSessions();
  }, []);

  // Profile completeness
  const fields = [
    { label: 'Full Name', done: !!user?.full_name },
    { label: 'Username', done: !!user?.username },
    { label: 'Phone Number', done: !!user?.phone_number },
    { label: 'Date of Birth', done: !!user?.date_of_birth },
    { label: 'Email Verified', done: !!user?.is_verified },
  ];
  const completedCount = fields.filter(f => f.done).length;
  const completeness = Math.round((completedCount / fields.length) * 100);

  const roleName = user?.role?.name ?? 'user';
  const roleCapitalized = roleName.charAt(0).toUpperCase() + roleName.slice(1);

  return (
    <div className="animate-fade-in">
      {/* Header Banner */}
      <div className="card mb-8" style={{ display: 'flex', flexDirection: 'row', alignItems: 'center', padding: 0, overflow: 'hidden', minHeight: '160px' }}>
        <div style={{ flex: 1, padding: '32px' }}>
          <h2>
            Welcome back,{' '}
            <span className="gradient-text">{user?.full_name?.split(' ')[0] || user?.username || 'User'}</span>
          </h2>
          <p style={{ marginTop: 6 }}>Here's your security overview.</p>
        </div>
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center', alignItems: 'center', background: 'var(--accent-light)', alignSelf: 'stretch' }}>
          <img src={dashboardImage} alt="AuthForge Bodyguard" style={{ maxHeight: '160px', objectFit: 'contain' }} />
        </div>
      </div>

      <div className="grid-auto">
        {/* Identity Card */}
        <div className="card">
          <div className="flex items-center gap-3 mb-6">
            <div style={{
              width: 36, height: 36, borderRadius: 10,
              background: 'var(--accent-light)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <User size={18} color="var(--accent-hover)" />
            </div>
            <h3>Your Identity</h3>
          </div>

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
              <span className="stat-label">Email</span>
              <span className="stat-value">
                {user?.email}
                {user?.is_verified
                  ? <span className="badge badge-success"><CheckCircle size={10} />Verified</span>
                  : <span className="badge badge-warning"><AlertCircle size={10} />Unverified</span>}
              </span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Role</span>
              <span className="stat-value">
                <span className={`badge ${roleName === 'admin' ? 'badge-primary' : roleName === 'moderator' ? 'badge-warning' : 'badge-muted'}`}>
                  <Shield size={10} />
                  {roleCapitalized}
                </span>
              </span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Phone</span>
              <span className="stat-value">{user?.phone_number || <em style={{ color: 'var(--text-muted)' }}>Not set</em>}</span>
            </div>
            <div className="stat-row">
              <span className="stat-label">Date of Birth</span>
              <span className="stat-value">{user?.date_of_birth || <em style={{ color: 'var(--text-muted)' }}>Not set</em>}</span>
            </div>
          </div>
        </div>

        {/* Profile Completeness */}
        <div className="card">
          <div className="flex items-center gap-3 mb-6">
            <div style={{
              width: 36, height: 36, borderRadius: 10,
              background: 'rgba(139, 92, 246, 0.15)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <TrendingUp size={18} color="#c084fc" />
            </div>
            <div>
              <h3>Profile Completeness</h3>
            </div>
            <span style={{ marginLeft: 'auto', fontSize: '1.5rem', fontWeight: 800, color: completeness === 100 ? 'var(--success)' : 'var(--text-primary)' }}>
              {completeness}%
            </span>
          </div>

          <div className="progress-bar-track mb-6">
            <div className="progress-bar-fill" style={{ width: `${completeness}%` }} />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {fields.map(f => (
              <div key={f.label} className="flex items-center gap-3">
                {f.done
                  ? <CheckCircle size={16} color="var(--success)" />
                  : <div style={{ width: 16, height: 16, borderRadius: '50%', border: '2px solid var(--border-strong)', flexShrink: 0 }} />
                }
                <span style={{ fontSize: '0.875rem', color: f.done ? 'var(--text-secondary)' : 'var(--text-muted)' }}>
                  {f.label}
                </span>
              </div>
            ))}
          </div>

          {completeness < 100 && (
            <a
              href="/settings"
              className="btn btn-ghost btn-sm w-full"
              style={{ marginTop: 20, textDecoration: 'none' }}
            >
              Complete Profile →
            </a>
          )}
        </div>

        {/* Active Sessions */}
        <div className="card" style={{ gridColumn: '1 / -1' }}>
          <div className="flex items-center gap-3 mb-6">
            <div style={{
              width: 36, height: 36, borderRadius: 10,
              background: 'rgba(16, 185, 129, 0.12)',
              display: 'flex', alignItems: 'center', justifyContent: 'center'
            }}>
              <Monitor size={18} color="var(--success)" />
            </div>
            <h3>Active Sessions</h3>
            <span className="badge badge-success" style={{ marginLeft: 'auto' }}>{sessions.length} active</span>
          </div>

          {sessionsLoading ? (
            <div className="flex justify-center" style={{ padding: '20px 0' }}>
              <div className="spinner" />
            </div>
          ) : sessions.length === 0 ? (
            <p style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px 0' }}>No active sessions found.</p>
          ) : (
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Device</th>
                    <th>IP Address</th>
                    <th>Expires</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((session) => (
                    <tr key={session.id}>
                      <td style={{ color: 'var(--text-primary)', fontWeight: 500, maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {session.device_info || 'Unknown device'}
                      </td>
                      <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{session.ip_address || '—'}</td>
                      <td>
                        <div className="flex items-center gap-2">
                          <Clock size={13} />
                          {new Date(session.expires_at).toLocaleDateString()}
                        </div>
                      </td>
                      <td><span className="badge badge-success">Active</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
