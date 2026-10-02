import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { useState } from 'react';
import { 
  LayoutDashboard, ShieldAlert, Search, FolderOpen,
  Database, GitMerge, Network, Clock3, TriangleAlert, FileCheck, Settings,
  UserRound, Bell, CircleDot
} from 'lucide-react';
import Dashboard from './pages/Dashboard';
import AccountInvestigation from './pages/AccountInvestigation';
import CaseDiary from './pages/CaseDiary';
import { useNavigate } from 'react-router-dom';

function Sidebar() {
  const location = useLocation();
  const accountQuery = new URLSearchParams(location.search).get('q');
  const navItems = [
    { name: 'Command Center', path: '/', icon: LayoutDashboard },
    { name: 'Cases', path: '/investigate', icon: FolderOpen },
    { name: 'Evidence Vault', path: '/diary', icon: Database },
    { name: 'Correlation Engine', path: '/investigate?view=overview', icon: GitMerge },
    { name: 'Investigation Graph', path: '/investigate?view=graph', icon: Network },
    { name: 'Timeline', path: '/investigate?view=graph', icon: Clock3 },
    { name: 'Risk Analysis', path: '/investigate?view=risk', icon: TriangleAlert },
    { name: 'Investigation Briefs', path: '/diary', icon: FileCheck },
  ];

  return (
    <aside className="tracex-sidebar">
      <div className="tracex-brand">
        <div className="tracex-brand-mark"><ShieldAlert size={18} /></div>
        <div>
          <h1>TRACEX</h1>
          <p>Unified Intelligence</p>
        </div>
      </div>

      <div className="tracex-sidebar-body">
        <div className="tracex-section-label">Investigation Suite</div>
        <nav className="tracex-nav">
          {navItems.map((item) => {
            const isActive = item.path === '/' ? location.pathname === '/' : location.pathname.startsWith('/investigate') && ((item.name === 'Cases' && !location.search) || location.search.includes(item.path.split('view=')[1] || ''));
            const targetPath = accountQuery && item.path.startsWith('/investigate')
              ? `${item.path}${item.path.includes('?') ? '&' : '?'}q=${encodeURIComponent(accountQuery)}`
              : item.path;
            return (
              <Link
                key={item.name}
                to={targetPath}
                className={`tracex-nav-item ${isActive ? 'active' : ''}`}
              >
                <item.icon size={18} />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="tracex-sidebar-footer">
        <Settings size={15} /> <span>Settings</span>
        <div className="tracex-node-status"><CircleDot size={11} /> API ready</div>
        <small>Local TraceX workspace</small>
      </div>
    </aside>
  );
}

function TopBar() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault();
    if (query.trim()) navigate(`/investigate?q=${encodeURIComponent(query.trim())}`);
  };

  return (
    <header className="tracex-topbar">
      <div className="tracex-case-pill"><span /> Workspace: <strong>Live investigation</strong></div>
      <div className="tracex-case-type">Evidence-backed intelligence console</div>
      <form onSubmit={submitSearch} className="tracex-top-search">
        <Search size={14} />
        <input type="text" placeholder="Search by Case or Account" value={query} onChange={event => setQuery(event.target.value)} />
      </form>
      <div className="tracex-alert"><Bell size={14} /> Review signals after selecting an account</div>
      <div className="tracex-user"><div><strong>Investigator workspace</strong><small>Local session</small></div><UserRound size={17} /></div>
    </header>
  );
}

export default function App() {
  return (
    <div className="tracex-app-shell">
      <Sidebar />
      <main className="tracex-main">
        <TopBar />
        <div className="tracex-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/investigate" element={<AccountInvestigation />} />
            <Route path="/diary" element={<CaseDiary />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
