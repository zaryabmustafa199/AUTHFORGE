import React from 'react';
import { Link, Outlet } from 'react-router-dom';
import { Shield, LogOut, User, Settings, Users } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const Layout = () => {
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <div className="flex-col min-h-screen" style={{ display: 'flex' }}>
      <nav className="navbar">
        <div className="container flex items-center justify-between">
          <Link to="/" className="nav-brand">
            <Shield size={24} color="var(--accent-primary)" />
            AuthForge
          </Link>
          
          <div className="nav-links">
            {isAuthenticated ? (
              <>
                {user?.role_id === 3 && (
                  <Link to="/admin" className="nav-link flex items-center gap-2">
                    <Users size={18} /> Admin
                  </Link>
                )}
                <Link to="/dashboard" className="nav-link flex items-center gap-2">
                  <User size={18} /> Dashboard
                </Link>
                <Link to="/settings" className="nav-link flex items-center gap-2">
                  <Settings size={18} /> Settings
                </Link>
                <button onClick={logout} className="btn btn-secondary flex items-center gap-2">
                  <LogOut size={16} /> Logout
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="nav-link">Login</Link>
                <Link to="/signup" className="btn btn-primary">Sign Up</Link>
              </>
            )}
          </div>
        </div>
      </nav>

      <main className="container" style={{ padding: '40px 24px', flex: 1 }}>
        <Outlet />
      </main>

      <footer style={{ padding: '24px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
        <p>&copy; 2026 AuthForge. All rights reserved.</p>
      </footer>
    </div>
  );
};

export default Layout;
