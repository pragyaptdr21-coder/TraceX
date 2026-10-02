import React, { useState, useEffect, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import ReactFlow, { 
  MiniMap, Controls, Background, useNodesState, useEdgesState, MarkerType, type Edge, type Node
} from 'reactflow';
import 'reactflow/dist/style.css';
import dagre from 'dagre';
import { Search, Loader2, Network, ShieldAlert, AlertTriangle } from 'lucide-react';
import { getTrail, getAccount, getRisk } from '../api';

const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

export default function SubgraphInvestigation() {
  const location = useLocation();
  const navigate = useNavigate();
  const queryParams = new URLSearchParams(location.search);
  const initialQuery = queryParams.get('q') || '';

  const [query, setQuery] = useState(initialQuery);
  const [rootAccount, setRootAccount] = useState<string | null>(initialQuery || null);
  const [hops, setHops] = useState(2);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [selectedEdge, setSelectedEdge] = useState<any>(null);
  
  const [rootSummary, setRootSummary] = useState<any>(null);
  const [rootRisk, setRootRisk] = useState<any>(null);

  // Layout function
  const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = 'LR') => {
    dagreGraph.setGraph({ rankdir: direction, ranksep: 200, nodesep: 60 });

    nodes.forEach((node) => {
      dagreGraph.setNode(node.id, { width: 220, height: 80 });
    });

    edges.forEach((edge) => {
      dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    const layoutedNodes = nodes.map((node) => {
      const nodeWithPosition = dagreGraph.node(node.id);
      return {
        ...node,
        position: {
          x: nodeWithPosition.x - 110,
          y: nodeWithPosition.y - 40,
        },
      };
    });

    return { nodes: layoutedNodes, edges };
  };

  const loadData = async (accountId: string, currentHops: number) => {
    setLoading(true);
    setError(null);
    try {
      const [trailData, summaryData, riskData] = await Promise.all([
        getTrail(accountId, currentHops),
        getAccount(accountId).catch(() => null),
        getRisk(accountId).catch(() => null)
      ]);

      setRootSummary(summaryData);
      setRootRisk(riskData);

      const isDarkMode = document.documentElement.classList.contains('dark');
      
      const newNodes = trailData.nodes.map((n: any) => {
        const isRoot = n.id === accountId;
        
        const bg = isRoot ? (isDarkMode ? '#082f49' : '#eff6ff') : (isDarkMode ? '#0f172a' : '#f8fafc');
        const borderC = isRoot ? (isDarkMode ? '#0ea5e9' : '#3b82f6') : (isDarkMode ? '#1e293b' : '#e2e8f0');
        const textC = isDarkMode ? '#f8fafc' : '#0f172a';
        
        let riskColor = 'text-slate-400';
        if (n.intensity > 0.7) riskColor = 'text-red-500';
        else if (n.intensity > 0.4) riskColor = 'text-amber-500';

        return {
          id: n.id,
          data: { 
            raw: n, 
            label: (
              <div className={`relative text-left w-full h-full p-3 rounded-lg border-2`} style={{ backgroundColor: bg, borderColor: borderC, color: textC }}>
                {isRoot && (
                  <div className="absolute -top-3 -left-2 bg-blue-600 text-white px-2 py-0.5 rounded shadow text-[9px] font-bold uppercase tracking-widest border border-blue-400 z-10 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></span> ROOT
                  </div>
                )}
                <div className="flex justify-between items-start mb-2">
                  <div className="font-bold text-sm truncate pr-2" title={n.id}>
                    {n.id.length > 15 ? n.id.slice(0, 15) + '...' : n.id}
                  </div>
                  {n.intensity > 0.4 && <AlertTriangle size={14} className={riskColor} />}
                </div>
                <div className="text-[10px] opacity-75 flex justify-between font-mono">
                  <span>Hop {n.layer}</span>
                  <span>Risk {Math.round(n.intensity * 100)}</span>
                </div>
              </div>
            )
          },
          style: {
            width: isRoot ? 220 : 180,
            padding: 0,
            border: 'none',
            background: 'transparent',
            boxShadow: isRoot ? (isDarkMode ? '0 0 20px 2px rgba(14, 165, 233, 0.4)' : '0 0 15px 2px rgba(59, 130, 246, 0.3)') : 'none',
            borderRadius: '8px'
          }
        };
      });

      const newEdges = trailData.edges.map((e: any) => {
        return {
          id: `${e.source.id || e.source}-${e.target.id || e.target}`,
          source: e.source.id || e.source,
          target: e.target.id || e.target,
          type: 'smoothstep',
          animated: true,
          label: `₹${(e.amount || 0).toLocaleString()}`,
          labelStyle: { fill: isDarkMode ? '#f8fafc' : '#0f172a', fontWeight: 600, fontSize: 10 },
          labelBgStyle: { fill: isDarkMode ? '#1e293b' : '#ffffff', fillOpacity: 0.9, stroke: isDarkMode ? '#334155' : '#e2e8f0', strokeWidth: 1, rx: 4, ry: 4 },
          data: e,
          style: { stroke: isDarkMode ? '#475569' : '#94a3b8', strokeWidth: 1.5 },
          markerEnd: { type: MarkerType.ArrowClosed, color: isDarkMode ? '#475569' : '#94a3b8' }
        };
      });

      const layouted = getLayoutedElements(newNodes, newEdges);
      setNodes(layouted.nodes);
      setEdges(layouted.edges);
      
    } catch (err) {
      console.error(err);
      setError("Unable to load subgraph.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (rootAccount) {
      loadData(rootAccount, hops);
    }
  }, [rootAccount, hops]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      navigate(`/subgraph?q=${encodeURIComponent(query.trim())}`);
      setRootAccount(query.trim());
      setSelectedNode(null);
      setSelectedEdge(null);
    }
  };

  const onNodeClick = useCallback((_: any, node: Node) => {
    setSelectedNode(node.data.raw);
    setSelectedEdge(null);
    
    // Highlight path logic
    if (rootAccount) {
      setNodes((nds) => nds.map((n) => {
        
        return {
          ...n,
          style: { ...n.style, opacity: 1 } // Simplified for now, real path finding is complex on frontend without full graph
        };
      }));
      setEdges((eds) => eds.map((e) => {
        const isRelated = e.source === node.id || e.target === node.id;
        return {
          ...e,
          style: { ...e.style, strokeOpacity: isRelated ? 1 : 0.2 },
          animated: isRelated
        };
      }));
    }
  }, [rootAccount, setNodes, setEdges]);

  const onEdgeClick = useCallback((_: any, edge: Edge) => {
    setSelectedEdge(edge.data);
    setSelectedNode(null);
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNode(null);
    setSelectedEdge(null);
    // Reset edges
    setEdges((eds) => eds.map((e) => ({
      ...e,
      style: { ...e.style, strokeOpacity: 1 },
      animated: true
    })));
  }, [setEdges]);

  return (
    <div className="flex flex-col h-full bg-slate-50 dark:bg-[#020617] text-slate-900 dark:text-slate-200">
      
      {/* HEADER & SEARCH */}
      <div className="p-4 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0f172a]">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2 text-slate-800 dark:text-white">
              <Network size={20} className="text-blue-600 dark:text-blue-400" />
              Subgraph Investigation
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">Explore the focused money trail around a selected account.</p>
          </div>
          
          <form onSubmit={handleSearch} className="flex items-center gap-2">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input 
                type="text" 
                placeholder="Search Account ID..." 
                value={query}
                onChange={e => setQuery(e.target.value)}
                className="pl-9 pr-4 py-2 text-sm border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 rounded-md w-64 focus:outline-none focus:border-blue-500"
              />
            </div>
            <button type="submit" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-md transition-colors">
              Investigate
            </button>
          </form>
        </div>
      </div>

      {/* WORKSPACE */}
      <div className="flex-1 flex overflow-hidden">
        
        {/* LEFT PANEL */}
        <div className="w-80 border-r border-slate-200 dark:border-slate-800 bg-white dark:bg-[#0f172a] flex flex-col overflow-y-auto">
          <div className="p-4 border-b border-slate-200 dark:border-slate-800">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-3">Hop Control</h2>
            <div className="flex gap-2">
              {[1, 2, 3, 4].map(h => (
                <button 
                  key={h}
                  onClick={() => setHops(h)}
                  disabled={!rootAccount || loading}
                  className={`flex-1 py-1.5 text-xs font-semibold border rounded ${hops === h ? 'bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800' : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50 dark:bg-slate-800 dark:text-slate-400 dark:border-slate-700 dark:hover:bg-slate-700'} disabled:opacity-50`}
                >
                  {h} Hop{h>1?'s':''}
                </button>
              ))}
            </div>
          </div>

          <div className="p-4 flex-1">
            {!rootAccount ? (
              <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 dark:text-slate-400">
                <Network size={32} className="mb-2 opacity-50" />
                <p className="text-sm">Select an account to start a subgraph investigation.</p>
              </div>
            ) : error ? (
              <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/50 rounded-lg text-center">
                <ShieldAlert size={24} className="mx-auto text-red-500 mb-2" />
                <p className="text-sm font-bold text-red-700 dark:text-red-400 mb-2">{error}</p>
                <button onClick={() => loadData(rootAccount, hops)} className="text-xs font-bold text-blue-600 dark:text-blue-400 hover:underline">Retry</button>
              </div>
            ) : (
              <div className="space-y-6">
                
                {/* NODE DETAILS */}
                {selectedNode ? (
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">Selected Account</h3>
                    <div className="p-3 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 space-y-3">
                      <div>
                        <div className="text-[10px] text-slate-500">Account ID</div>
                        <div className="font-mono font-bold text-sm text-slate-900 dark:text-white break-all">{selectedNode.id}</div>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        <div className="p-2 bg-white dark:bg-[#0f172a] rounded border border-slate-100 dark:border-slate-700">
                          <div className="text-[9px] uppercase text-slate-500">Risk Score</div>
                          <div className="font-bold text-red-600 dark:text-red-400">{Math.round((selectedNode.intensity || 0) * 100)}</div>
                        </div>
                        <div className="p-2 bg-white dark:bg-[#0f172a] rounded border border-slate-100 dark:border-slate-700">
                          <div className="text-[9px] uppercase text-slate-500">Role</div>
                          <div className="font-bold text-slate-700 dark:text-slate-300 capitalize">{selectedNode.role || 'Unknown'}</div>
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-500 mb-1">Flow Summary</div>
                        <div className="text-xs space-y-1">
                          <div className="flex justify-between"><span className="text-slate-500">Inbound:</span> <span className="font-mono">₹{selectedNode.in_amount?.toLocaleString() || 0}</span></div>
                          <div className="flex justify-between"><span className="text-slate-500">Outbound:</span> <span className="font-mono">₹{selectedNode.out_amount?.toLocaleString() || 0}</span></div>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : selectedEdge ? (
                   <div>
                   <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">Transaction Details</h3>
                   <div className="p-3 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-800 space-y-3">
                     <div>
                       <div className="text-[10px] text-slate-500">Amount</div>
                       <div className="font-mono font-bold text-lg text-emerald-600 dark:text-emerald-400">₹{selectedEdge.amount?.toLocaleString() || 0}</div>
                     </div>
                     <div className="space-y-1 text-xs">
                       <div className="text-[10px] text-slate-500">From</div>
                       <div className="font-mono text-slate-900 dark:text-slate-300 break-all">{selectedEdge.source?.id || selectedEdge.source}</div>
                     </div>
                     <div className="space-y-1 text-xs">
                       <div className="text-[10px] text-slate-500">To</div>
                       <div className="font-mono text-slate-900 dark:text-slate-300 break-all">{selectedEdge.target?.id || selectedEdge.target}</div>
                     </div>
                   </div>
                 </div>
                ) : (
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">Root Account Summary</h3>
                    {rootSummary ? (
                      <div className="p-3 bg-blue-50 dark:bg-sky-950/30 rounded-lg border border-blue-100 dark:border-sky-900/50 space-y-3">
                        <div>
                          <div className="text-[10px] text-slate-500 dark:text-slate-400">Account ID</div>
                          <div className="font-mono font-bold text-sm text-blue-900 dark:text-sky-300 break-all">{rootSummary.account_id}</div>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <div className="text-[10px] text-slate-500">Total In</div>
                            <div className="font-mono text-xs font-bold text-slate-700 dark:text-slate-300">₹{(rootSummary.incoming_amount || 0).toLocaleString()}</div>
                          </div>
                          <div>
                            <div className="text-[10px] text-slate-500">Total Out</div>
                            <div className="font-mono text-xs font-bold text-slate-700 dark:text-slate-300">₹{(rootSummary.outgoing_amount || 0).toLocaleString()}</div>
                          </div>
                        </div>
                        {rootRisk && rootRisk.signals && rootRisk.signals.length > 0 && (
                          <div className="pt-2 border-t border-blue-200 dark:border-sky-800/50">
                            <div className="text-[10px] text-slate-500 dark:text-slate-400 mb-1">Risk Signals</div>
                            <ul className="text-[10px] space-y-1">
                              {rootRisk.signals.map((s: any, idx: number) => (
                                <li key={idx} className="text-red-600 dark:text-red-400 flex items-start gap-1">
                                  <span className="mt-0.5">•</span> <span>{s.type} ({(s.contribution * 100).toFixed(0)}%)</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-xs text-slate-500">Loading summary...</div>
                    )}
                  </div>
                )}
                
                {/* LEGEND */}
                <div className="mt-8">
                  <h3 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">Legend</h3>
                  <div className="text-[10px] space-y-1.5 text-slate-600 dark:text-slate-400">
                    <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-blue-500"></span> Root Account</div>
                    <div className="flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-slate-400"></span> Connected Account</div>
                    <div className="flex items-center gap-2"><AlertTriangle size={10} className="text-amber-500" /> Risk Indicator</div>
                    <div className="flex items-center gap-2"><span className="text-slate-400">→</span> Money Flow</div>
                  </div>
                </div>

              </div>
            )}
          </div>
        </div>

        {/* RIGHT GRAPH CANVAS */}
        <div className="flex-1 relative bg-[#f8fafc] dark:bg-[#020617]">
          {loading && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-white/50 dark:bg-[#020617]/50 backdrop-blur-sm">
              <Loader2 size={32} className="animate-spin text-blue-600 dark:text-blue-400 mb-2" />
              <div className="text-sm font-semibold text-slate-700 dark:text-slate-300">Constructing Subgraph...</div>
            </div>
          )}
          
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            onEdgeClick={onEdgeClick}
            onPaneClick={onPaneClick}
            fitView
            panOnScroll={true}
            panOnDrag={true}
            zoomOnScroll={false}
            zoomOnPinch={true}
            nodesDraggable={true}
            attributionPosition="bottom-left"
          >
            <Background color="var(--color-border)" gap={24} size={2} />
            <Controls className="bg-white dark:bg-slate-800 fill-slate-700 dark:fill-slate-300 border-slate-200 dark:border-slate-700 shadow-sm" showInteractive={false} />
            <MiniMap 
              className="bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800"
              nodeColor={(n: any) => n.id === rootAccount ? '#3b82f6' : '#94a3b8'}
              maskColor="rgba(0,0,0,0.1)"
            />
          </ReactFlow>
        </div>
        
      </div>
    </div>
  );
}
