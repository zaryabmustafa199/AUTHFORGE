import React from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { Shield, LogOut, LayoutDashboard, Settings, Users } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

import logo from '../assets/logo.png';

const Layout = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const location = useLocation();
  const isAdmin = user?.role?.name === 'admin';

  const isActive = (path: string) => location.pathname.startsWith(path);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <nav className="navbar">
        <div className="container flex items-center justify-between">
          <Link to="/" className="nav-brand">
            <img src={logo} alt="AuthForge Logo" style={{ height: '32px' }} />
            <span>AuthForge</span>
          </Link>

          <div className="nav-links">
            {isAuthenticated ? (
              <>
                {isAdmin && (
                  <Link
                    to="/admin"
                    className={`nav-link ${isActive('/admin') ? 'active' : ''}`}
                  >
                    <Users size={15} />
                    Admin
                  </Link>
                )}
                <Link
                  to="/dashboard"
                  className={`nav-link ${isActive('/dashboard') ? 'active' : ''}`}
                >
                  <LayoutDashboard size={15} />
                  Dashboard
                </Link>
                <Link
                  to="/settings"
                  className={`nav-link ${isActive('/settings') ? 'active' : ''}`}
                >
                  <Settings size={15} />
                  Settings
                </Link>
                <button onClick={logout} className="btn btn-ghost btn-sm" style={{ marginLeft: '4px' }}>
                  <LogOut size={15} />
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="nav-link">Sign In</Link>
                <Link to="/signup" className="btn btn-primary btn-sm">Get Started</Link>
              </>
            )}
          </div>
        </div>
      </nav>

      <main style={{ flex: 1, padding: '40px 0' }}>
        <div className="container">
          <Outlet />
        </div>
      </main>

      <footer style={{ padding: '20px 0', borderTop: '1px solid var(--border)', textAlign: 'center' }}>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          © 2026 AuthForge · Production-Grade Identity Platform
        </p>
      </footer>
    </div>
  );
};

export default Layout;
