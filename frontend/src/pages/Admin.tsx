import React, { useState, useEffect } from 'react';
import api from '../lib/api';

const Admin = () => {
  const [activeTab, setActiveTab] = useState<'users' | 'audit'>('users');
  
  // Users State
  const [users, setUsers] = useState<any[]>([]);
  const [usersPage, setUsersPage] = useState(1);
  const [usersTotal, setUsersTotal] = useState(0);

  // Audit Logs State
  const [logs, setLogs] = useState<any[]>([]);
  const [logsPage, setLogsPage] = useState(1);
  const [logsTotal, setLogsTotal] = useState(0);

  const fetchUsers = async () => {
    try {
      const res = await api.get(`/users/admin/users?page=${usersPage}&size=10`);
      setUsers(res.data.items);
      setUsersTotal(res.data.total);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchLogs = async () => {
    try {
      const res = await api.get(`/users/admin/audit-logs?page=${logsPage}&size=10`);
      setLogs(res.data.items);
      setLogsTotal(res.data.total);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (activeTab === 'users') fetchUsers();
    else fetchLogs();
  }, [activeTab, usersPage, logsPage]);

  const handleRoleChange = async (userId: string, newRoleId: number) => {
    try {
      await api.patch(`/users/admin/users/${userId}/role`, { role_id: newRoleId });
      fetchUsers(); // Refresh
    } catch (err) {
      console.error('Failed to change role', err);
      alert('Failed to change role. Ensure you are not demoting yourself.');
    }
  };

  return (
    <div className="flex-col gap-6">
      <div style={{ marginBottom: '24px' }}>
        <h2>Admin Panel</h2>
        <p>Manage users and view system security logs.</p>
      </div>

      <div className="flex gap-4" style={{ marginBottom: '24px', borderBottom: '1px solid var(--border-light)', paddingBottom: '16px' }}>
        <button 
          className={`btn ${activeTab === 'users' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('users')}
        >
          User Directory
        </button>
        <button 
          className={`btn ${activeTab === 'audit' ? 'btn-primary' : 'btn-secondary'}`}
          onClick={() => setActiveTab('audit')}
        >
          Audit Logs
        </button>
      </div>

      {activeTab === 'users' && (
        <div className="card">
          <h3 style={{ marginBottom: '16px' }}>Users ({usersTotal})</h3>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Name</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id}>
                    <td style={{ fontWeight: 500 }}>{u.email}</td>
                    <td>{u.full_name || '-'}</td>
                    <td>
                      <span className={`badge ${u.role_id === 3 ? 'badge-primary' : u.role_id === 2 ? 'badge-warning' : 'badge-success'}`}>
                        {u.role_id === 3 ? 'Admin' : u.role_id === 2 ? 'Moderator' : 'User'}
                      </span>
                    </td>
                    <td>{u.is_active ? 'Active' : 'Inactive'}</td>
                    <td>
                      <select 
                        value={u.role_id}
                        onChange={(e) => handleRoleChange(u.id, parseInt(e.target.value))}
                        className="form-input"
                        style={{ padding: '6px 12px', fontSize: '0.85rem' }}
                      >
                        <option value={1}>Make User</option>
                        <option value={2}>Make Moderator</option>
                        <option value={3}>Make Admin</option>
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex justify-between items-center" style={{ marginTop: '16px' }}>
            <button className="btn btn-secondary" disabled={usersPage === 1} onClick={() => setUsersPage(p => p - 1)}>Previous</button>
            <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Page {usersPage}</span>
            <button className="btn btn-secondary" disabled={usersPage * 10 >= usersTotal} onClick={() => setUsersPage(p => p + 1)}>Next</button>
          </div>
        </div>
      )}

      {activeTab === 'audit' && (
        <div className="card">
          <h3 style={{ marginBottom: '16px' }}>Security Audit Logs ({logsTotal})</h3>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Action</th>
                  <th>User ID</th>
                  <th>IP Address</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <tr key={log.id}>
                    <td style={{ fontSize: '0.9rem' }}>{new Date(log.created_at).toLocaleString()}</td>
                    <td><span className="badge badge-warning">{log.action}</span></td>
                    <td style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{log.user_id || 'System/Anonymous'}</td>
                    <td style={{ fontSize: '0.9rem' }}>{log.ip_address}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex justify-between items-center" style={{ marginTop: '16px' }}>
            <button className="btn btn-secondary" disabled={logsPage === 1} onClick={() => setLogsPage(p => p - 1)}>Previous</button>
            <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>Page {logsPage}</span>
            <button className="btn btn-secondary" disabled={logsPage * 10 >= logsTotal} onClick={() => setLogsPage(p => p + 1)}>Next</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default Admin;
