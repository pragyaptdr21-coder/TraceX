import { useState, useEffect, useCallback } from 'react';
import ReactFlow, { Background, Controls, useNodesState, useEdgesState, MarkerType } from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import { ShieldAlert, Activity, X, AlertTriangle, Download, Maximize, Minimize2, Moon, Sun } from 'lucide-react';
import { getTrail, getAccount, exportSubdataset, getRisk } from '../api';

export default function InvestigationGraphTab({ initialAccountId, fullscreen, initialHops = 3 }: { initialAccountId: string, fullscreen?: boolean, initialHops?: number }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  
  const [isFullscreen, setIsFullscreen] = useState(fullscreen || false);
  const [isDarkMode, setIsDarkMode] = useState(document.documentElement.classList.contains('dark'));

  useEffect(() => {
    const handler = () => setIsDarkMode(document.documentElement.classList.contains('dark'));
    window.addEventListener('theme-change', handler);
    return () => window.removeEventListener('theme-change', handler);
  }, []);
  const [hops, setHops] = useState(initialHops);
  const [query, setQuery] = useState(initialAccountId);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [nodeProfile, setNodeProfile] = useState<any>(null);

  const loadGraph = useCallback(async (accountId: string) => {
    setIsLoading(true);
    setError('');
    setSelectedNode(null);
    setNodeProfile(null);
    try {
      const data = await getTrail(accountId, hops);
      if (!data || !data.nodes || data.nodes.length === 0) {
        throw new Error('No connections found for this account.');
      }
      
      // Dagre layout
      const dagreGraph = new dagre.graphlib.Graph();
      dagreGraph.setDefaultEdgeLabel(() => ({}));
      dagreGraph.setGraph({ rankdir: 'LR', nodesep: 80, ranksep: 350 }); // Left-to-Right with huge spacing to fix congestion
      
      data.nodes.forEach((n: any) => {
        dagreGraph.setNode(n.id, { width: 220, height: 80 });
      });
      data.edges.forEach((e: any) => {
        dagreGraph.setEdge(e.source.id || e.source, e.target.id || e.target);
      });
      dagre.layout(dagreGraph);

      const formattedNodes = data.nodes.map((n: any) => {
        const nodeWithPosition = dagreGraph.node(n.id);
        
        let color = isDarkMode ? '#38bdf8' : '#64748b';
        let label = 'Account';
        let bg = isDarkMode ? 'bg-slate-900/80' : 'bg-slate-50';
        let textC = isDarkMode ? 'text-cyan-400' : 'text-slate-600';
        let borderC = isDarkMode ? 'border-cyan-900/50' : 'border-slate-200';
        let glow = isDarkMode ? '0 0 10px 1px rgba(56, 189, 248, 0.2)' : '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)';
        
        if (n.role === 'victim') { color = isDarkMode ? '#0ea5e9' : '#3b82f6'; label = 'Victim (Start)'; bg = isDarkMode ? 'bg-sky-950' : 'bg-blue-100'; textC = isDarkMode ? 'text-sky-300' : 'text-blue-700'; borderC = isDarkMode ? 'border-sky-500' : 'border-blue-300'; glow = isDarkMode ? '0 0 25px 5px rgba(14, 165, 233, 0.6)' : '0 0 20px 2px rgba(59, 130, 246, 0.5)'; }
        if (n.role === 'terminal') { color = '#f59e0b'; label = 'Cash-Out'; bg = isDarkMode ? 'bg-amber-950' : 'bg-amber-50'; textC = isDarkMode ? 'text-amber-400' : 'text-amber-600'; borderC = isDarkMode ? 'border-amber-600' : 'border-amber-200'; glow = isDarkMode ? '0 0 15px 2px rgba(245, 158, 11, 0.4)' : glow; }
        if (n.role === 'mule') { color = '#ef4444'; label = 'Mule'; bg = isDarkMode ? 'bg-red-950' : 'bg-red-50'; textC = isDarkMode ? 'text-red-400' : 'text-red-600'; borderC = isDarkMode ? 'border-red-600' : 'border-red-200'; glow = isDarkMode ? '0 0 15px 2px rgba(239, 68, 68, 0.4)' : glow; }
        if (n.role === 'distributor') { color = '#8b5cf6'; label = 'Distributor'; bg = isDarkMode ? 'bg-purple-950' : 'bg-purple-50'; textC = isDarkMode ? 'text-purple-400' : 'text-purple-600'; borderC = isDarkMode ? 'border-purple-600' : 'border-purple-200'; glow = isDarkMode ? '0 0 15px 2px rgba(139, 92, 246, 0.4)' : glow; }

        return {
          id: n.id,
          position: { x: nodeWithPosition.x - 110, y: nodeWithPosition.y - 40 },
          data: { 
            raw: n,
            label: (
              <div className="text-left relative w-full">
                {n.role === 'victim' && (
                  <div className="absolute -top-6 -left-3 bg-blue-600 text-white px-2 py-0.5 rounded shadow-lg animate-pulse text-[10px] font-black uppercase border border-blue-400 z-10 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-white rounded-full"></span> START
                  </div>
                )}
                <div className="flex justify-between items-center mb-2">
                  <div className="font-semibold text-sm ${isDarkMode ? 'text-white' : 'text-slate-800'} truncate pr-2" title={n.id}>{n.id.length > 12 ? n.id.slice(0, 10) + '...' : n.id}</div>
                  <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${bg} ${textC} ${borderC}`}>{label}</span>
                </div>
                <div className="text-[10px] text-slate-500 font-medium px-2 py-1 ${isDarkMode ? 'bg-slate-900 border-slate-700 text-slate-400' : 'bg-slate-50 border-slate-100 text-slate-500'} rounded border flex justify-between">
                  <span>Hop: {n.layer}</span>
                  <span>Risk: {Math.round(n.intensity * 100)}</span>
                </div>
              </div>
            )
          },
          style: {
            background: isDarkMode ? '#020617' : 'white',
            color: isDarkMode ? '#f8fafc' : '#020617',
            border: n.role === 'victim' ? `3px solid ${color}` : `2px solid ${color}`,
            padding: '12px',
            borderRadius: '8px',
            width: n.role === 'victim' ? 220 : 200,
            boxShadow: glow
          }
        };
      });

      const formattedEdges = data.edges.map((e: any) => {
        const amt = e.amount ? `₹${e.amount.toLocaleString()}` : 'Transfer';
        return {
          id: `${e.source.id || e.source}-${e.target.id || e.target}-${e.transaction_id || Math.random()}`,
          source: e.source.id || e.source,
          target: e.target.id || e.target,
          animated: true,
          type: 'smoothstep',
          label: amt,
          labelStyle: { fill: isDarkMode ? '#f8fafc' : '#0f172a', fontWeight: 600, fontSize: 10 },
          labelBgStyle: { fill: isDarkMode ? '#020617' : '#f8fafc', fillOpacity: 0.9, stroke: isDarkMode ? '#475569' : '#cbd5e1', strokeWidth: 1, rx: 4, ry: 4 },
          style: { stroke: '#94a3b8', strokeWidth: 1.5 },
          markerEnd: { type: MarkerType.ArrowClosed, color: '#94a3b8' },
          data: { raw: e }
        };
      });

      setNodes(formattedNodes);
      setEdges(formattedEdges);
    } catch (err: any) {
      setError(err.message || 'Failed to load graph.');
    } finally {
      setIsLoading(false);
    }
  }, [hops, setNodes, setEdges, isDarkMode]);

  useEffect(() => {
    loadGraph(initialAccountId);
  }, [initialAccountId, loadGraph]);

  const handleSearch = () => { if (query.trim()) loadGraph(query.trim()); };

  const onNodeClick = useCallback(async (_: any, node: any) => {
    setSelectedNode(node);
    setNodeProfile(null);
    try {
      const p = await getAccount(node.id);
      let risk = null;
      try { risk = await getRisk(node.id); } catch(err) {}
      setNodeProfile({ summary: p, risk });
    } catch (e) {
      console.error(e);
    }
  }, []);

  const handleExport = async () => {
    try {
      const transactionIds = edges.map((e: any) => e.data?.raw?.Transaction_ID || e.data?.raw?.transaction_id).filter(Boolean);
      const data = await exportSubdataset(transactionIds, { hops, query });
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tracex_export_${query}.json`;
      a.click();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div className={`flex flex-col ${isDarkMode ? 'bg-slate-950 text-slate-200' : 'bg-slate-50 text-slate-800'} ${isFullscreen ? 'fixed inset-0 z-50 p-6' : 'h-full'}`}>
      
      {/* HEADER */}
      <div className="border-b ${isDarkMode ? 'border-slate-800' : 'border-slate-200'} pb-4 mb-4 shrink-0 flex flex-wrap gap-4 justify-between items-end">
        <div>
          <div className="text-xs font-semibold ${isDarkMode ? 'text-slate-500' : 'text-slate-400'} mb-1">Topology Engine / Entity Graph</div>
          <h2 className="text-2xl font-bold ${isDarkMode ? 'text-white' : 'text-slate-800'} flex items-center gap-3">
             Investigation Graph
             {isLoading && <Activity size={18} className="text-blue-500 animate-spin" />}
          </h2>
        </div>
        
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex ${isDarkMode ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-200'} rounded shadow-sm">
            <input 
              type="text" 
              className="px-3 py-1.5 text-sm outline-none w-48 rounded-l" 
              placeholder="Source Account..." 
              value={query} 
              onChange={e => setQuery(e.target.value)} 
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
            />
            <div className="border-l ${isDarkMode ? 'border-slate-700 bg-slate-950/50' : 'border-slate-200 bg-slate-50'} px-2 flex items-center">
              <span className="text-xs font-semibold ${isDarkMode ? 'text-slate-400' : 'text-slate-500'} mr-2">HOPS</span>
              <select value={hops} onChange={e => setHops(Number(e.target.value))} className="text-sm bg-transparent outline-none font-medium">
                <option value={1}>1</option><option value={2}>2</option><option value={3}>3</option><option value={4}>4</option>
              </select>
            </div>
            <button onClick={handleSearch} className="px-3 py-1.5 bg-blue-600 text-white text-sm font-semibold rounded-r hover:bg-blue-700">Load</button>
          </div>

          <div className="${isDarkMode ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-200'} px-4 py-1.5 rounded shadow-sm text-sm flex items-center space-x-6">
            <div><span className="text-[10px] font-semibold ${isDarkMode ? 'text-slate-400' : 'text-slate-500'} block">Entities</span><span className="font-semibold ${isDarkMode ? 'text-white' : 'text-slate-800'}">{nodes.length}</span></div>
            <div><span className="text-[10px] font-semibold ${isDarkMode ? 'text-slate-400' : 'text-slate-500'} block">Links</span><span className="font-semibold ${isDarkMode ? 'text-white' : 'text-slate-800'}">{edges.length}</span></div>
          </div>
          
          <button onClick={() => setIsDarkMode(!isDarkMode)} className={`px-4 py-2 font-bold uppercase tracking-wider text-xs flex items-center gap-2 ${isDarkMode ? 'bg-indigo-600 text-white border-indigo-500 hover:bg-indigo-500 shadow-[0_0_10px_rgba(79,70,229,0.5)]' : 'bg-slate-900 text-white border-slate-900 hover:bg-slate-800'} border rounded`} title="Toggle Theme">
            {isDarkMode ? <><Sun size={16} className="text-amber-300" /> Light Mode</> : <><Moon size={16} className="text-indigo-300" /> Cyber Mode</>}
          </button>
          
          <button onClick={handleExport} className="p-2 ${isDarkMode ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-200'} rounded shadow-sm hover:bg-slate-100" title="Export Dataset"><Download size={18} className="${isDarkMode ? 'text-slate-300' : 'text-slate-600'}" /></button>
          
          <button onClick={() => setIsFullscreen(!isFullscreen)} className="p-2 ${isDarkMode ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-200'} rounded shadow-sm hover:bg-slate-100" title="Toggle Fullscreen">
            {isFullscreen ? <Minimize2 size={18} className="${isDarkMode ? 'text-slate-300' : 'text-slate-600'}" /> : <Maximize size={18} className="${isDarkMode ? 'text-slate-300' : 'text-slate-600'}" />}
          </button>
          
          {error && (
            <div className="bg-red-50 text-red-700 border border-red-200 px-3 py-1.5 rounded shadow-sm text-sm flex items-center gap-2">
               <ShieldAlert size={14} /> <span className="font-semibold">{error}</span>
            </div>
          )}
        </div>
      </div>

      {/* GRAPH WORKSPACE */}
      <div className="flex-1 flex space-x-4 min-h-0 relative">
        <div className="flex-1 border ${isDarkMode ? 'border-slate-700 bg-slate-950' : 'border-slate-200 bg-white'} rounded-lg overflow-hidden relative shadow-inner">
          <ReactFlow 
            nodes={nodes} 
            edges={edges} 
            onNodesChange={onNodesChange} 
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            fitView
            attributionPosition="bottom-left"
            panOnScroll={true}
            panOnDrag={true}
            zoomOnScroll={false}
            zoomOnPinch={true}
            nodesDraggable={true}
          >
            <Background color={isDarkMode ? '#1e293b' : '#cbd5e1'} gap={24} size={2} />
            <Controls className="${isDarkMode ? 'bg-slate-900 fill-slate-300 border-slate-700' : 'bg-white fill-slate-700 border-slate-200'} shadow-sm" showInteractive={false} />
          </ReactFlow>
        </div>

        {/* SIDE PANEL */}
        {selectedNode && (
          <div className="absolute right-4 top-4 bottom-4 w-[400px] ${isDarkMode ? 'bg-slate-900 border-slate-700' : 'bg-white border-slate-200'} rounded-lg shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-right-8 z-10">
            <div className="${isDarkMode ? 'bg-slate-950/50 border-slate-700' : 'bg-slate-50 border-slate-200'} border-b p-4 flex justify-between items-start">
              <div>
                <div className="text-[10px] font-bold text-blue-600 bg-blue-100 px-2 py-0.5 rounded border border-blue-200 inline-block mb-2 uppercase tracking-wider">Entity Profile</div>
                <h3 className="text-lg font-bold ${isDarkMode ? 'text-white' : 'text-slate-900'} font-mono break-all">{selectedNode.id}</h3>
              </div>
              <div className="flex space-x-1 text-slate-400">
                <button className="p-1.5 ${isDarkMode ? 'hover:bg-slate-800 hover:text-white' : 'hover:bg-slate-200 hover:text-slate-700'} rounded transition-colors" onClick={() => setSelectedNode(null)}><X className="w-4 h-4" /></button>
              </div>
            </div>
            
            <div className="flex-1 overflow-y-auto p-5">
              <div className="flex justify-between items-center mb-6">
                <div>
                  <div className="text-xs font-semibold text-slate-500 mb-1 uppercase tracking-wider">Classification</div>
                  <div className="text-sm font-bold ${isDarkMode ? 'text-white' : 'text-slate-800'} capitalize">{selectedNode.data.raw.role}</div>
                </div>
                {selectedNode.data.raw.role !== 'victim' && (
                  <div className="text-center ${isDarkMode ? 'bg-red-900/20 border-red-800/50' : 'bg-red-50 border-red-200'} rounded p-2">
                    <div className="text-[10px] font-bold ${isDarkMode ? 'text-red-400' : 'text-red-600'} mb-1 uppercase">Risk Score</div>
                    <div className="text-xl font-bold text-red-700">{Math.round((nodeProfile?.risk?.mule_risk_index || selectedNode.data.raw.intensity * 100))}/100</div>
                  </div>
                )}
              </div>
              
              {selectedNode.data.raw.role !== 'victim' && (
                <div className="${isDarkMode ? 'bg-red-900/20 border-red-800/50' : 'bg-red-50 border-red-200'} rounded-lg p-4 mb-6 shadow-sm">
                  <div className="flex items-center ${isDarkMode ? 'text-red-400' : 'text-red-700'} font-bold mb-3 text-sm">
                    <AlertTriangle className="w-4 h-4 mr-2" /> Why is this node flagged?
                  </div>
                  <ul className="text-sm font-medium ${isDarkMode ? 'text-slate-300' : 'text-slate-700'} space-y-3">
                    {nodeProfile?.risk?.signals && nodeProfile.risk.signals.length > 0 ? (
                       nodeProfile.risk.signals.map((sig: any, idx: number) => (
                         <li key={idx} className="leading-relaxed border-l-2 border-red-300 pl-3">
                            <strong className="${isDarkMode ? 'text-white' : 'text-slate-900'} block">{sig.type}</strong>
                            <span className="${isDarkMode ? 'text-slate-300' : 'text-slate-600'} text-xs">Evidence contribution: {sig.contribution}</span>
                         </li>
                       ))
                    ) : (
                      <li className="leading-relaxed ${isDarkMode ? 'text-slate-300' : 'text-slate-600'}">
                        {isLoading ? 'Analyzing behavioral signals...' : `Connected to the flow at Hop ${selectedNode.data.raw.layer} with high transaction velocity.`}
                      </li>
                    )}
                  </ul>
                </div>
              )}

              <div className="space-y-4">
                <h4 className="text-xs font-bold text-slate-800 uppercase tracking-wider border-b ${isDarkMode ? 'border-slate-700' : 'border-slate-200'} pb-2">Account Telemetry</h4>
                <div className="grid grid-cols-2 gap-4 text-sm font-normal">
                  <div className="${isDarkMode ? 'bg-slate-950/50 border-slate-700' : 'bg-slate-50 border-slate-100'} p-3 rounded border">
                    <div className="text-[10px] font-bold text-slate-500 uppercase mb-1">Incoming</div>
                    <div className="${isDarkMode ? 'text-emerald-400' : 'text-emerald-600'} font-bold">₹{nodeProfile ? nodeProfile.summary.incoming_amount.toLocaleString() : '...'}</div>
                    <div className="text-xs text-slate-500 mt-1">{nodeProfile?.summary.incoming_count || 0} transfers</div>
                  </div>
                  <div className="${isDarkMode ? 'bg-slate-950/50 border-slate-700' : 'bg-slate-50 border-slate-100'} p-3 rounded border">
                    <div className="text-[10px] font-bold text-slate-500 uppercase mb-1">Outgoing</div>
                    <div className="${isDarkMode ? 'text-red-400' : 'text-red-600'} font-bold">₹{nodeProfile ? nodeProfile.summary.outgoing_amount.toLocaleString() : '...'}</div>
                    <div className="text-xs text-slate-500 mt-1">{nodeProfile?.summary.outgoing_count || 0} transfers</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
