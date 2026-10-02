import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { Sun, Moon } from 'lucide-react';
import { 
  LayoutDashboard, Search, FolderOpen,
  Database, GitMerge, Network, Clock3, TriangleAlert, FileCheck, Settings,
  UserRound, Bell, CircleDot
} from 'lucide-react';
import Dashboard from './pages/Dashboard';
import AccountInvestigation from './pages/AccountInvestigation';
import CaseDiary from './pages/CaseDiary';
import GraphFullscreen from './pages/GraphFullscreen';
import SubgraphInvestigation from './pages/SubgraphInvestigation';
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
    { name: 'Subgraph Investigation', path: '/subgraph', icon: Network },
    { name: 'Investigation Briefs', path: '/diary', icon: FileCheck },
  ];

  return (
    <aside className="tracex-sidebar">
      <div className="tracex-brand">
        <div className="tracex-brand-mark"><img src="/WhatsApp%20Image%202026-09-12%20at%207.57.38%20AM.jpeg" alt="TraceX logo" /></div>
        <div>
          <h1>TRACEX</h1>
          <p>Unified Intelligence</p>
        </div>
      </div>

      <div className="tracex-sidebar-body">
        <div className="tracex-section-label">Investigation Suite</div>
        <nav className="tracex-nav">
          {navItems.map((item) => {
            const isActive = item.path === '/' 
              ? location.pathname === '/' 
              : item.path.startsWith('/investigate')
                ? location.pathname.startsWith('/investigate') && ((item.name === 'Cases' && !location.search) || location.search.includes(item.path.split('view=')[1] || ''))
                : location.pathname.startsWith(item.path);
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

  const [isDark, setIsDark] = useState(document.documentElement.classList.contains('dark'));
  
  useEffect(() => {
    // Default to dark mode globally on load
    document.documentElement.classList.add('dark');
    setIsDark(true);
  }, []);

  const toggleTheme = () => {
    const nextDark = !isDark;
    setIsDark(nextDark);
    if (nextDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    window.dispatchEvent(new Event('theme-change'));
  };

  return (
    <header className="tracex-topbar">
      <div className="tracex-case-pill"><span /> Workspace: <strong>Live investigation</strong></div>
      <div className="tracex-case-type">Evidence-backed intelligence console</div>
      <form onSubmit={submitSearch} className="tracex-top-search">
        <Search size={14} />
        <input type="text" placeholder="Search by Case or Account" value={query} onChange={event => setQuery(event.target.value)} />
      </form>
      <button onClick={toggleTheme} className="ml-2 px-3 py-1.5 flex items-center gap-2 border rounded font-bold text-xs uppercase" style={{
        backgroundColor: isDark ? '#4f46e5' : '#f1f5f9',
        color: isDark ? 'white' : '#0f172a',
        borderColor: isDark ? '#4338ca' : '#cbd5e1'
      }}>
        {isDark ? <Sun size={14} className="text-amber-300" /> : <Moon size={14} className="text-indigo-500" />}
        {isDark ? 'Light' : 'Cyber'} Mode
      </button>
      <div className="tracex-alert ml-auto"><Bell size={14} /> Review signals after selecting an account</div>
      <div className="tracex-user"><div><strong>Investigator workspace</strong><small>Local session</small></div><UserRound size={17} /></div>
    </header>
  );
}

export default function App() {
  const location = useLocation();

  // The graph viewer is a dedicated surface: sidebar, topbar and page chrome are
  // all dropped so the network gets the whole viewport.
  if (location.pathname === '/graph') {
    return <GraphFullscreen />;
  }

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
            <Route path="/subgraph" element={<SubgraphInvestigation />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
