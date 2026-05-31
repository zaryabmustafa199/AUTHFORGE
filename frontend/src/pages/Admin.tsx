import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Shield, Users, Activity, Search, RefreshCw, AlertCircle, CheckCircle, Power } from 'lucide-react';
import api from '../lib/api';

const Admin = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'users' | 'audit'>('users');
  
  // Data States
  const [users, setUsers] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Pagination States
  const [userPage, setUserPage] = useState(1);
  const [userTotal, setUserTotal] = useState(0);
  const [logPage, setLogPage] = useState(1);
  const [logTotal, setLogTotal] = useState(0);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      if (activeTab === 'users') {
        const res = await api.get(`/users/admin/users?page=${userPage}&per_page=10`);
        setUsers(res.data.users || []);
        setUserTotal(res.data.total || 0);
      } else {
        const res = await api.get(`/users/admin/audit-logs?page=${logPage}&per_page=15`);
        setLogs(res.data.logs || []);
        setLogTotal(res.data.total || 0);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeTab, userPage, logPage]);

  const handleRoleChange = async (userId: string, newRoleId: number) => {
    try {
      await api.patch(`/users/admin/users/${userId}`, { role_id: newRoleId });
      fetchData(); // Refresh list
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update role');
    }
  };

  const handleStatusToggle = async (userId: string, currentStatus: boolean) => {
    try {
      await api.patch(`/users/admin/users/${userId}`, { is_active: !currentStatus });
      fetchData(); // Refresh list
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to update status');
    }
  };

  const renderUserRoleBadge = (roleName: string) => {
    if (roleName === 'admin') return <span className="badge badge-primary"><Shield size={10}/>Admin</span>;
    if (roleName === 'moderator') return <span className="badge badge-warning"><Shield size={10}/>Mod</span>;
    return <span className="badge badge-muted">User</span>;
  };

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2>Admin Control Center</h2>
          <p style={{ marginTop: 6 }}>Manage users, roles, and view system audit logs.</p>
        </div>
        <button onClick={fetchData} className="btn btn-secondary btn-sm">
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="alert alert-error mb-6">
          <AlertCircle size={15} style={{ flexShrink: 0 }} />
          {error}
        </div>
      )}

      {/* Custom Tabs */}
      <div className="tab-bar" style={{ maxWidth: 300 }}>
        <button 
          className={`tab-btn ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => { setActiveTab('users'); setUserPage(1); }}
        >
          <div className="flex justify-center items-center gap-2">
            <Users size={16} /> Users
          </div>
        </button>
        <button 
          className={`tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
          onClick={() => { setActiveTab('audit'); setLogPage(1); }}
        >
          <div className="flex justify-center items-center gap-2">
            <Activity size={16} /> Audit Logs
          </div>
        </button>
      </div>

      <div className="card">
        {loading ? (
          <div className="flex justify-center items-center" style={{ minHeight: 300 }}>
            <div className="spinner" />
          </div>
        ) : activeTab === 'users' ? (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 style={{ fontSize: '1.1rem' }}>User Management <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontWeight: 400 }}>({userTotal} total)</span></h3>
            </div>
            
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Status</th>
                    <th>Role</th>
                    <th>Joined</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.length === 0 ? (
                    <tr><td colSpan={5} style={{ textAlign: 'center' }}>No users found</td></tr>
                  ) : (
                    users.map(u => (
                      <tr key={u.id}>
                        <td>
                          <div style={{ fontWeight: 500, color: 'var(--text-primary)' }}>
                            {u.full_name || u.username || 'Unnamed User'}
                          </div>
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{u.email}</div>
                        </td>
                        <td>
                          {u.is_active 
                            ? <span className="badge badge-success"><CheckCircle size={10}/>Active</span>
                            : <span className="badge badge-danger"><AlertCircle size={10}/>Inactive</span>
                          }
                        </td>
                        <td>
                          {renderUserRoleBadge(u.role?.name || 'user')}
                        </td>
                        <td>{new Date(u.created_at).toLocaleDateString()}</td>
                        <td style={{ textAlign: 'right' }}>
                          <div className="flex justify-end items-center gap-2">
                            <select 
                              className="form-input" 
                              style={{ width: 'auto', padding: '4px 8px', fontSize: '0.8rem', height: 32 }}
                              value={u.role_id}
                              onChange={(e) => handleRoleChange(u.id, parseInt(e.target.value))}
                              disabled={u.id === user?.id} // Can't change own role
                            >
                              <option value={1}>User</option>
                              <option value={2}>Moderator</option>
                              <option value={3}>Admin</option>
                            </select>
                            
                            <button
                              onClick={() => handleStatusToggle(u.id, u.is_active)}
                              className={`btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-success'}`}
                              style={{ height: 32, padding: '0 12px' }}
                              disabled={u.id === user?.id} // Can't deactivate self
                              title={u.is_active ? "Deactivate user" : "Activate user"}
                            >
                              <Power size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
            
            {/* Pagination Controls */}
            {userTotal > 10 && (
              <div className="flex justify-between items-center mt-6">
                <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                  Showing {(userPage - 1) * 10 + 1} to {Math.min(userPage * 10, userTotal)} of {userTotal}
                </span>
                <div className="flex gap-2">
                  <button 
                    className="btn btn-secondary btn-sm" 
                    disabled={userPage === 1}
                    onClick={() => setUserPage(p => p - 1)}
                  >
                    Previous
                  </button>
                  <button 
                    className="btn btn-secondary btn-sm" 
                    disabled={userPage * 10 >= userTotal}
                    onClick={() => setUserPage(p => p + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : (
          <div>
            <div className="flex justify-between items-center mb-4">
              <h3 style={{ fontSize: '1.1rem' }}>System Audit Logs <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontWeight: 400 }}>({logTotal} total)</span></h3>
            </div>
            
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Time</th>
                    <th>Action</th>
                    <th>User ID</th>
                    <th>IP Address</th>
                    <th>Metadata</th>
                  </tr>
                </thead>
                <tbody>
                  {logs.length === 0 ? (
                    <tr><td colSpan={5} style={{ textAlign: 'center' }}>No audit logs found</td></tr>
                  ) : (
                    logs.map(log => (
                      <tr key={log.id}>
                        <td style={{ whiteSpace: 'nowrap' }}>
                          {new Date(log.created_at).toLocaleString(undefined, { 
                            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                          })}
                        </td>
                        <td>
                          <span className="badge badge-muted" style={{ fontFamily: 'monospace' }}>
                            {log.action}
                          </span>
                        </td>
                        <td style={{ fontFamily: 'monospace', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          {log.user_id ? log.user_id.split('-')[0] + '...' : 'System'}
                        </td>
                        <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>
                          {log.ip_address || '—'}
                        </td>
                        <td>
                          <div style={{ 
                            background: 'var(--bg-base)', padding: '6px 10px', 
                            borderRadius: 'var(--radius-sm)', fontSize: '0.75rem',
                            fontFamily: 'monospace', color: 'var(--text-secondary)',
                            maxWidth: 300, overflowX: 'auto', whiteSpace: 'nowrap'
                          }}>
                            {JSON.stringify(log.metadata_info)}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Controls */}
            {logTotal > 15 && (
              <div className="flex justify-between items-center mt-6">
                <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                  Showing {(logPage - 1) * 15 + 1} to {Math.min(logPage * 15, logTotal)} of {logTotal}
                </span>
                <div className="flex gap-2">
                  <button 
                    className="btn btn-secondary btn-sm" 
                    disabled={logPage === 1}
                    onClick={() => setLogPage(p => p - 1)}
                  >
                    Previous
                  </button>
                  <button 
                    className="btn btn-secondary btn-sm" 
                    disabled={logPage * 15 >= logTotal}
                    onClick={() => setLogPage(p => p + 1)}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default Admin;
