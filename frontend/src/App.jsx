import React, { useEffect, useState } from 'react';
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Link,
  Navigate,
  useLocation,
  useNavigate,
} from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Setup from './pages/Setup';
import Caregiver from './pages/Caregiver';
import Wellbeing from './pages/Wellbeing';
import Login from './pages/Login';
import Register from './pages/Register';
import { isLoggedIn, getUser } from './services/auth';
import api from './services/api';
import './App.css';

const TEXT_SIZE_KEY = 'dosewise_text_size';
const TEXT_SIZES = [
  { value: 'normal', label: 'A' },
  { value: 'large', label: 'A+' },
  { value: 'xlarge', label: 'A++' },
];

function ProtectedRoute({ children }) {
  if (!isLoggedIn()) {
    return <Navigate to="/login" replace />;
  }
  return children;
}

// Big, icon-forward navigation for the patient-facing screens
function Navigation() {
  const location = useLocation();
  const navigate = useNavigate();

  const handleLogout = () => {
    api.logout();
    navigate('/login');
  };

  return (
    <nav className="app-nav" aria-label="Main navigation">
      <Link to="/" className={`nav-btn ${location.pathname === '/' ? 'active' : ''}`}>
        <span className="nav-icon" aria-hidden="true">🏠</span>
        <span>Home</span>
      </Link>
      <Link to="/wellbeing" className={`nav-btn ${location.pathname === '/wellbeing' ? 'active' : ''}`}>
        <span className="nav-icon" aria-hidden="true">💬</span>
        <span>How I feel</span>
      </Link>
      <Link to="/setup" className={`nav-btn ${location.pathname === '/setup' ? 'active' : ''}`}>
        <span className="nav-icon" aria-hidden="true">💊</span>
        <span>My Meds</span>
      </Link>
      <Link to="/caregiver" className={`nav-btn ${location.pathname === '/caregiver' ? 'active' : ''}`}>
        <span className="nav-icon" aria-hidden="true">🧑‍⚕️</span>
        <span>Caregiver</span>
      </Link>
      <button type="button" className="nav-btn nav-logout" onClick={handleLogout}>
        <span className="nav-icon" aria-hidden="true">🚪</span>
        <span>Sign out</span>
      </button>
    </nav>
  );
}

function TextSizeToggle({ size, onChange }) {
  return (
    <div className="text-size-toggle" role="group" aria-label="Text size">
      {TEXT_SIZES.map((s) => (
        <button
          key={s.value}
          type="button"
          className={size === s.value ? 'active' : ''}
          onClick={() => onChange(s.value)}
          aria-pressed={size === s.value}
          title={`Text size: ${s.value}`}
        >
          {s.label}
        </button>
      ))}
    </div>
  );
}

function AppShell() {
  const location = useLocation();
  const authed = isLoggedIn();
  const user = getUser();
  const isAuthPage = location.pathname === '/login' || location.pathname === '/register';

  const [textSize, setTextSize] = useState(
    () => localStorage.getItem(TEXT_SIZE_KEY) || 'normal'
  );

  useEffect(() => {
    document.documentElement.dataset.textSize = textSize;
    localStorage.setItem(TEXT_SIZE_KEY, textSize);
  }, [textSize]);

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-brand">
          <h1>DoseWise</h1>
          {authed && user?.name && <span className="header-user">Hi, {user.name.split(' ')[0]}</span>}
        </div>
        <div className="header-controls">
          <TextSizeToggle size={textSize} onChange={setTextSize} />
        </div>
        {authed && !isAuthPage && <Navigation />}
      </header>

      <main className="app-main">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/wellbeing" element={<ProtectedRoute><Wellbeing /></ProtectedRoute>} />
          <Route path="/setup" element={<ProtectedRoute><Setup /></ProtectedRoute>} />
          <Route path="/caregiver" element={<ProtectedRoute><Caregiver /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppShell />
    </Router>
  );
}

export default App;
