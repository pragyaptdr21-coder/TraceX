import { 
  ShieldAlert, Activity, Search, Link2, ArrowUpRight,
  TriangleAlert, ArrowLeftRight, FileCheck, Network
} from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { getHealth } from '../api';
import DetectionEvaluation from '../components/DetectionEvaluation';

export default function Dashboard() {
  const [search, setSearch] = useState("");
  const [apiStatus, setApiStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const navigate = useNavigate();

  useEffect(() => {
    getHealth().then(result => setApiStatus(result.status === 'ok' ? 'online' : 'offline')).catch(() => setApiStatus('offline'));
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (search.trim()) {
      navigate(`/investigate?q=${encodeURIComponent(search.trim())}`);
    }
  };

  return (
    <div className="tracex-page command-center-page">
      <div className="tracex-page-heading">
        <div><div className="tracex-eyebrow">Unified Cyber Fraud Intelligence Overview</div><h1>Command Center</h1></div>
        <form onSubmit={handleSearch} className="command-search"><Search size={15} /><input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search account ID to begin investigation" /><button type="submit">Investigate</button></form>
      </div>
      <div className="command-case-summary"><div><span>Workspace state</span><strong>READY</strong></div><div><span>Data source</span><b>Live TraceX API + DuckDB</b></div><div><span>Backend status</span><b className={apiStatus === 'online' ? 'status-online' : apiStatus === 'offline' ? 'status-offline' : ''}>{apiStatus === 'checking' ? 'Checking...' : apiStatus === 'online' ? 'Online' : 'Unavailable'}</b></div></div>
      <div className="command-metrics">
        <Metric icon={<TriangleAlert />} label="Risk analysis" value="Per account" tone="danger" />
        <Metric icon={<Activity />} label="Detection signals" value="Live API" tone="warning" />
        <Metric icon={<Link2 />} label="Trail graph" value="1-4 hops" tone="blue" />
        <Metric icon={<FileCheck />} label="Evidence" value="Selectable" tone="green" />
        <Metric icon={<ArrowLeftRight />} label="Transactions" value="Paginated" tone="purple" />
        <Metric icon={<ShieldAlert />} label="Human review" value="Required" tone="danger" />
      </div>
      <div className="command-columns">
        <section className="reference-panel"><div className="panel-title"><Network size={16} /> Investigation Graph <Link to="/investigate">Open graph <ArrowUpRight size={14} /></Link></div><div className="graph-preview"><span><Network size={28} /> No account selected</span><small>Search an account to load its real multi-hop trail</small></div></section>
        <section className="reference-panel"><div className="panel-title"><TriangleAlert size={16} /> Investigation Workflow</div><ul className="finding-list"><li>Search a real account from the TraceX dataset.</li><li>Review risk indicators and detector evidence.</li><li>Open graph, timeline, evidence, and case review from the investigation.</li></ul><Link to="/investigate" className="panel-action">Open Investigation Workspace <ArrowUpRight size={14} /></Link></section>
      </div>
      <DetectionEvaluation />
    </div>
  );
}

function Metric({ icon, label, value, tone }: { icon: React.ReactNode; label: string; value: string; tone: string }) {
  return <div className={`command-metric tone-${tone}`}><div className="metric-icon">{icon}</div><div><span>{label}</span><strong>{value}</strong></div></div>;
}
