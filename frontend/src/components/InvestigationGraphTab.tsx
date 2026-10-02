import { useState, useEffect, useRef, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import { ShieldAlert, Activity, Search, Filter, ZoomIn, ZoomOut, Maximize, Play, Pause, SkipBack, RotateCcw, Download, Crosshair, X } from 'lucide-react';
import { getTrail, getTimeline, exportSubdataset, getAccount, getRisk, getDetections } from '../api';


export default function InvestigationGraphTab({ initialAccountId }: { initialAccountId: string }) {
  const [query, setQuery] = useState(initialAccountId);
  const [accountId, setAccountId] = useState(initialAccountId);
  const [isolatedNodeId, setIsolatedNodeId] = useState<string | null>(null);
  
  const [hops, setHops] = useState(4);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [fullGraphData, setFullGraphData] = useState({ nodes: [], edges: [], root_account: '' });
  const [graphData, setGraphData] = useState({ nodes: [], edges: [], root_account: '' });

  
  // Timeline State
  const [startTime, setStartTime] = useState<number | null>(null);
  const [endTime, setEndTime] = useState<number | null>(null);
  const [currentTime, setCurrentTime] = useState<number | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  
  // Evidence & UI State
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [selectedNodeProfile, setSelectedNodeProfile] = useState<any>(null);
  const [isLoadingNodeProfile, setIsLoadingNodeProfile] = useState(false);
  const [selectedEdge, setSelectedEdge] = useState<any>(null);
  const [evidencePanelOpen, setEvidencePanelOpen] = useState(false);
  const [evidence, setEvidence] = useState<any[]>([]);
  const [graphSize, setGraphSize] = useState({ width: 900, height: 420 });

  const graphRef = useRef<any>(null);
  const graphViewportRef = useRef<HTMLDivElement>(null);
  const playIntervalRef = useRef<any>(null);

  useEffect(() => {
    const viewport = graphViewportRef.current;
    if (!viewport) return;
    const updateSize = () => setGraphSize({
      width: Math.max(320, viewport.clientWidth),
      height: Math.max(280, viewport.clientHeight),
    });
    updateSize();
    const observer = new ResizeObserver(updateSize);
    observer.observe(viewport);
    return () => observer.disconnect();
  }, []);

  const loadGraph = useCallback(async (targetAccount: string, targetHops: number) => {
    if (!targetAccount) return;
    setIsLoading(true);
    setError(null);
    setSelectedNode(null);
    setSelectedNodeProfile(null);
    setSelectedEdge(null);
    setIsPlaying(false);
    
    try {
      const [trailRes, timelineRes] = await Promise.all([
        getTrail(targetAccount, targetHops),
        getTimeline(targetAccount).catch(() => [])
      ]);
      
      if (!trailRes || trailRes.nodes.length === 0) {
        setError("No downstream trail found.");
        setFullGraphData({ nodes: [], edges: [], root_account: targetAccount });
        setGraphData({ nodes: [], edges: [], root_account: targetAccount });
      } else {
        setFullGraphData(trailRes);
        
        let start = null;
        let end = null;
        if (timelineRes && timelineRes.length > 0) {
           const firstTx = new Date(timelineRes[0].Timestamp).getTime();
           const lastTx = new Date(timelineRes[timelineRes.length - 1].Timestamp).getTime();
           const edgeTimes = trailRes.edges.map((e: any) => new Date(e.timestamp).getTime());
           
           start = Math.min(firstTx, ...edgeTimes);
           end = Math.max(lastTx, ...edgeTimes);
           
           setStartTime(start);
           setEndTime(end);
           setCurrentTime(end);
        } else {
           setStartTime(null);
           setEndTime(null);
           setCurrentTime(null);
        }
        setGraphData(trailRes);
      }
    } catch (err: any) {
      if (err.response?.status === 404) {
        setError("Account not found.");
      } else {
        setError("TraceX backend is unavailable or unable to load investigation trail.");
      }
      setFullGraphData({ nodes: [], edges: [], root_account: targetAccount });
      setGraphData({ nodes: [], edges: [], root_account: targetAccount });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (accountId) {
      loadGraph(accountId, hops);
    }
  }, [accountId, hops, loadGraph]);

  useEffect(() => {
    if (currentTime !== null && fullGraphData.nodes.length > 0) {
         let visibleEdges = fullGraphData.edges.filter((e: any) => {
           const eTime = new Date(e.timestamp).getTime();
           return eTime <= currentTime;
       });

         if (isolatedNodeId) {
           const isolatedAccounts = new Set([isolatedNodeId]);
           let changed = true;
           while (changed) {
             changed = false;
             visibleEdges.forEach((edge: any) => {
               const source = edge.source.id || edge.source;
               const target = edge.target.id || edge.target;
               if (isolatedAccounts.has(source) && !isolatedAccounts.has(target)) {
                 isolatedAccounts.add(target);
                 changed = true;
               }
             });
           }
           visibleEdges = visibleEdges.filter((edge: any) => isolatedAccounts.has(edge.source.id || edge.source) && isolatedAccounts.has(edge.target.id || edge.target));
         }
       
       const visibleNodes = fullGraphData.nodes.filter((n: any) => {
           if (n.id === fullGraphData.root_account) return true;
           return visibleEdges.some((e: any) => e.source === n.id || e.target === n.id || e.source.id === n.id || e.target.id === n.id);
       });

       setGraphData({
           nodes: visibleNodes,
           edges: visibleEdges,
           root_account: fullGraphData.root_account
       });
       
       if (selectedEdge) {
           if (!visibleEdges.find((e: any) => e.transaction_id === selectedEdge.transaction_id)) {
               setSelectedEdge(null);
           }
       }
       if (selectedNode) {
           if (!visibleNodes.find((n: any) => n.id === selectedNode.id)) {
               setSelectedNode(null);
           }
       }
    }
  }, [currentTime, fullGraphData, isolatedNodeId]);

  useEffect(() => {
    if (isPlaying && startTime !== null && endTime !== null && currentTime !== null) {
      const tickRate = 200;
      const minuteMs = 60 * 1000;
      
      playIntervalRef.current = setInterval(() => {
        setCurrentTime(prev => {
          if (prev === null) return null;
          const nextTime = prev + (minuteMs * playbackSpeed * 10);
          if (nextTime >= endTime) {
            setIsPlaying(false);
            return endTime;
          }
          return nextTime;
        });
      }, tickRate);
    } else {
      clearInterval(playIntervalRef.current);
    }
    
    return () => clearInterval(playIntervalRef.current);
  }, [isPlaying, startTime, endTime, playbackSpeed]);

  const handleSearch = () => {
    if (query.trim()) {
      setAccountId(query);
      setIsolatedNodeId(null);
    }
  };

  const handleIsolate = () => {
    if (selectedNode && selectedNode.id !== accountId) {
      setIsolatedNodeId(selectedNode.id);
    }
  };

  const handleExitIsolation = () => {
    setIsolatedNodeId(null);
  };

  const handleResetGraph = () => {
    setIsolatedNodeId(null);
    setQuery(accountId);
    loadGraph(accountId, hops);
  };

  const handleExport = async () => {
    if (graphData.edges.length === 0) return;
    try {
      const txIds = graphData.edges.map((e: any) => e.transaction_id);
      const metadata = {
        source_account: accountId,
        hop_scope: hops,
        timeline_start: startTime ? new Date(startTime).toISOString() : 'N/A',
        timeline_end: currentTime ? new Date(currentTime).toISOString() : 'N/A',
        transaction_count: txIds.length,
        account_count: graphData.nodes.length,
        generated_at: new Date().toISOString()
      };
      
      const blob = await exportSubdataset(txIds, metadata);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `investigation_export_${accountId}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (e) {
      alert("Unable to generate investigation export. Backend unavailable.");
    }
  };

  const addEvidence = (item: any, type: string) => {
    const exists = evidence.find(e => e.id === item.id || e.transaction_id === item.transaction_id);
    if (!exists) {
      setEvidence(prev => [...prev, { ...item, type }]);
      setEvidencePanelOpen(true);
    }
  };

  const handleNodeSelect = async (node: any) => {
    setSelectedNode(node);
    setSelectedEdge(null);
    setSelectedNodeProfile(null);
    setIsLoadingNodeProfile(true);
    try {
      const [summary, risk, detections] = await Promise.all([
        getAccount(node.id),
        getRisk(node.id).catch(() => null),
        getDetections(node.id).catch(() => [])
      ]);
      setSelectedNodeProfile({ summary, risk, detections });
    } finally {
      setIsLoadingNodeProfile(false);
    }
  };

  const handleZoomIn = () => { if (graphRef.current) graphRef.current.zoom(graphRef.current.zoom() * 1.5, 400); };
  const handleZoomOut = () => { if (graphRef.current) graphRef.current.zoom(graphRef.current.zoom() / 1.5, 400); };
  const handleFit = () => { if (graphRef.current) graphRef.current.zoomToFit(400); };

  const drawGraphNode = (node: any, context: CanvasRenderingContext2D, globalScale: number) => {
    if (node.x === undefined || node.y === undefined) return;
    const isRoot = node.id === graphData.root_account;
    const isLayerOne = node.layer === 1;
    const nodeColor = isRoot ? '#2563eb' : isLayerOne ? '#e87979' : '#9aaabd';

    // Dense real trails stay readable as compact nodes at overview zoom.
    // Account cards appear when the investigator zooms into a local subgraph.
    const useCardLayout = graphData.nodes.length <= 80;
    if (!useCardLayout && globalScale < 0.85 && !isRoot) {
      context.save();
      context.beginPath();
      context.arc(node.x, node.y, 4.5, 0, Math.PI * 2);
      context.fillStyle = nodeColor;
      context.fill();
      context.restore();
      return;
    }

    const width = isRoot ? 142 : 118;
    const height = 42;
    const left = node.x - width / 2;
    const top = node.y - height / 2;
    const radius = 5;

    context.save();
    context.beginPath();
    context.roundRect(left, top, width, height, radius);
    context.fillStyle = '#ffffff';
    context.fill();
    context.lineWidth = isRoot ? 2 : 1.5;
    context.strokeStyle = isRoot ? '#4f8be8' : isLayerOne ? '#e87979' : '#b8c4d4';
    context.stroke();

    if (globalScale > 0.55) {
      context.fillStyle = '#253449';
      context.font = `${Math.max(7, 10 / globalScale)}px ui-sans-serif, sans-serif`;
      context.textAlign = 'left';
      context.textBaseline = 'middle';
      const label = String(node.id);
      context.fillText(label.length > 18 ? `${label.slice(0, 17)}...` : label, left + 9, top + 15);
      context.fillStyle = '#8c99aa';
      context.font = `${Math.max(6, 8 / globalScale)}px ui-sans-serif, sans-serif`;
      context.fillText(isRoot ? 'Source account' : `Hop ${node.layer} trail node`, left + 9, top + 30);
    }
    context.restore();
  };

  const drawGraphLink = (link: any, context: CanvasRenderingContext2D, globalScale: number) => {
    const source = link.source;
    const target = link.target;
    if (!source?.x || !target?.x) return;
    const text = `₹${Number(link.amount || 0).toLocaleString('en-IN')}`;
    const midX = (source.x + target.x) / 2;
    const midY = (source.y + target.y) / 2;
    context.save();
    context.fillStyle = '#e56f73';
    context.font = `${Math.max(7, 9 / globalScale)}px ui-sans-serif, sans-serif`;
    context.textAlign = 'center';
    context.textBaseline = 'bottom';
    if (graphData.nodes.length <= 80 || globalScale > 1.05) context.fillText(text, midX, midY - 3);
    context.restore();
  };

  const formatTime = (ts: number | null) => {
    if (!ts) return "--";
    const d = new Date(ts);
    return d.toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  };

  const timelinePercent = (startTime && endTime && currentTime) 
    ? Math.min(100, Math.max(0, ((currentTime - startTime) / (endTime - startTime)) * 100))
    : 100;

  return (
    <div className="graph-workspace flex flex-col bg-white text-[#4b586b] relative rounded-md overflow-hidden border border-[#e1e7ef]">
      <div className="bg-white border-b border-[#e1e7ef] p-4 shadow-sm z-10 shrink-0">
        <div className="graph-header-actions flex items-center justify-between mb-4">
          <div>
            <div className="graph-breadcrumb">Topology Engine / Entity Graph</div>
            <h2 className="text-xl font-bold flex items-center gap-3 text-[#1c2738]">
              Investigation Graph & Timeline
              {isolatedNodeId && (
                <span className="bg-[#e53e3e] text-white text-[10px] uppercase px-2 py-1 rounded shadow-sm">Isolated Mode</span>
              )}
            </h2>
          </div>
          
          {fullGraphData.nodes.length > 0 && (
            <div className="graph-action-buttons flex gap-2">
              <div className="graph-stat"><span>Entities</span><strong>{graphData.nodes.length}</strong></div>
              <div className="graph-stat"><span>Links</span><strong>{graphData.edges.length}</strong></div>
              {isolatedNodeId && (
                <button onClick={handleExitIsolation} className="px-3 py-1.5 bg-gray-50 border border-border text-xs font-bold rounded shadow-sm hover:bg-gray-100 flex items-center gap-2">
                   <X size={14} /> Exit Isolation
                </button>
              )}
              <button onClick={() => setEvidencePanelOpen(!evidencePanelOpen)} className="px-3 py-1.5 bg-gray-50 border border-border text-xs font-bold rounded shadow-sm hover:bg-gray-100">
                 Selected Evidence ({evidence.length})
              </button>
              <button onClick={handleExport} className="px-3 py-1.5 bg-primary text-white border border-primary text-xs font-bold rounded shadow-sm hover:bg-primary/90 flex items-center gap-2">
                 <Download size={14} /> Export Subdataset
              </button>
                <button onClick={handleResetGraph} className="px-3 py-1.5 bg-gray-50 border border-border text-xs font-bold rounded shadow-sm hover:bg-gray-100 flex items-center gap-2" title="Reset graph view">
                  <RotateCcw size={14} /> Reset Graph
                </button>
            </div>
          )}
        </div>

        <div className="graph-header-controls flex items-center gap-4">
          <div className="relative w-64">
             <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
             <input 
              type="text" 
              className="w-full bg-gray-50 border border-border rounded-md pl-8 pr-3 py-1.5 text-xs focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary shadow-sm"
              placeholder="Source Account ID..."
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
            />
          </div>
          <button onClick={handleSearch} className="px-4 py-1.5 bg-primary text-white text-xs font-semibold rounded shadow-sm border border-primary hover:bg-primary/90">
            Load Graph
          </button>
          <div className="h-6 w-px bg-border mx-2"></div>
          <div className="flex items-center gap-2">
            <Filter size={14} className="text-text-muted" />
            <span className="text-xs font-bold text-text-muted">HOP LIMIT:</span>
            <select value={hops} onChange={e => setHops(Number(e.target.value))} className="bg-gray-50 border border-border text-xs rounded px-2 py-1 shadow-sm font-medium">
              <option value={1}>1 Hop</option>
              <option value={2}>2 Hops</option>
              <option value={3}>3 Hops</option>
              <option value={4}>4 Hops</option>
            </select>
          </div>
          <div className="h-6 w-px bg-border mx-2"></div>
          <div className="flex items-center gap-2">
            <button onClick={handleZoomIn} aria-label="Zoom in" title="Zoom in" className="p-1.5 bg-gray-50 border border-border rounded shadow-sm"><ZoomIn size={14} /></button>
            <button onClick={handleZoomOut} aria-label="Zoom out" title="Zoom out" className="p-1.5 bg-gray-50 border border-border rounded shadow-sm"><ZoomOut size={14} /></button>
            <button onClick={handleFit} aria-label="Fit graph" title="Fit graph" className="p-1.5 bg-gray-50 border border-border rounded shadow-sm"><Maximize size={14} /></button>
          </div>
          <div className="h-6 w-px bg-border mx-2"></div>
          <div className="flex gap-4">
            <div className="flex items-center gap-1.5 text-xs font-bold"><span className="text-[10px] text-text-muted uppercase">Nodes:</span> {graphData.nodes.length}</div>
            <div className="flex items-center gap-1.5 text-xs font-bold"><span className="text-[10px] text-text-muted uppercase">Edges:</span> {graphData.edges.length}</div>
          </div>
        </div>
      </div>

      <div className="flex-1 relative overflow-hidden bg-[#f8fafc] min-h-0">
        <div ref={graphViewportRef} className={`graph-canvas-area ${startTime && endTime ? 'has-timeline' : ''}`}>
        {isLoading && (
          <div className="absolute inset-0 bg-white/50 backdrop-blur-sm z-20 flex flex-col items-center justify-center">
            <Activity size={32} className="text-primary animate-spin mb-4" />
            <div className="text-sm font-bold text-primary">Building investigation trail...</div>
          </div>
        )}
        
        {error && !isLoading && (
          <div className="absolute inset-0 z-20 flex items-center justify-center">
            <div className="bg-danger-light border border-danger/20 text-danger p-4 rounded-lg flex items-center gap-3 text-sm font-semibold shadow-sm">
              <ShieldAlert size={18} />
              {error}
            </div>
          </div>
        )}

        {!isLoading && graphData.nodes.length > 0 && (
          <ForceGraph2D
            ref={graphRef}
            graphData={{
              nodes: graphData.nodes.map((n: any) => ({ ...n, name: n.id })),
              links: graphData.edges.map((e: any) => ({ ...e, source: e.source.id || e.source, target: e.target.id || e.target }))
            }}
            nodeLabel="name"
            nodeCanvasObject={drawGraphNode}
            nodePointerAreaPaint={(node: any, color: string, context: CanvasRenderingContext2D) => {
              if (node.x === undefined || node.y === undefined) return;
              context.fillStyle = color;
              context.fillRect(node.x - 60, node.y - 22, 120, 44);
            }}
            nodeColor={(node: any) => node.id === graphData.root_account ? '#2563eb' : (node.layer === 1 ? '#0ea5e9' : '#94a3b8')}
            nodeRelSize={6}
            dagMode={graphData.nodes.length <= 80 ? 'lr' : undefined}
            dagLevelDistance={graphData.nodes.length <= 80 ? 180 : undefined}
            d3VelocityDecay={0.35}
            linkColor={() => '#e56f73'}
            linkLineDash={() => [5, 4]}
            linkCurvature={graphData.nodes.length <= 80 ? 0.12 : 0}
            linkDirectionalArrowLength={3.5}
            linkDirectionalArrowRelPos={1}
            linkDirectionalParticles={graphData.nodes.length <= 80 ? 2 : 0}
            linkDirectionalParticleWidth={2.5}
            linkDirectionalParticleSpeed={0.006}
            linkCanvasObject={drawGraphLink}
            onEngineStop={() => graphRef.current?.zoomToFit(500, 55)}
            onNodeClick={(node) => {
              void handleNodeSelect(node);
              if (graphRef.current) {
                graphRef.current.centerAt(node.x, node.y, 400);
                graphRef.current.zoom(2, 400);
              }
            }}
            onLinkClick={(link) => {
              setSelectedEdge(link);
              setSelectedNode(null);
            }}
            width={graphSize.width}
            height={graphSize.height}
          />
        )}
        </div>

        <div className="absolute bottom-[100px] left-4 bg-white/90 backdrop-blur border border-border p-3 rounded-lg shadow-sm z-10 pointer-events-none">
          <div className="text-[10px] font-bold text-text-muted uppercase mb-2">Legend</div>
          <div className="space-y-1.5 text-xs">
            <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-[#2563eb]"></div> Source Account</div>
            <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-[#0ea5e9]"></div> Hop 1 Account</div>
            <div className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-[#94a3b8]"></div> Hop 2+ Account</div>
            <div className="flex items-center gap-2"><div className="w-4 h-0.5 bg-[#cbd5e1]"></div> Transaction Edge</div>
          </div>
        </div>

        {(selectedNode || selectedEdge) && (
          <div className="absolute top-4 right-4 w-[min(320px,calc(100%-2rem))] bg-white/95 backdrop-blur border border-border rounded-lg shadow-lg z-10 flex flex-col max-h-[calc(100%-2rem)]">
            <div className="p-3 border-b border-border flex justify-between items-center bg-gray-50 rounded-t-lg">
              <span className="text-xs font-bold text-text-main uppercase tracking-wider">
                {selectedNode ? 'Node Intelligence' : 'Transaction Intelligence'}
              </span>
              <button onClick={() => { setSelectedNode(null); setSelectedEdge(null); }} className="text-text-muted hover:text-text-main font-bold">×</button>
            </div>
            
            <div className="p-4 overflow-y-auto flex-1 text-sm space-y-4">
              {selectedNode && (
                <>
                  <div className="flex justify-between items-start">
                     <div>
                        <div className="text-[10px] text-text-muted font-bold uppercase tracking-wider">Account ID</div>
                        <div className="font-mono text-text-main font-bold mt-1 break-all">{selectedNode.id}</div>
                     </div>
                     {selectedNode.id !== graphData.root_account && (
                        <button onClick={handleIsolate} className="p-1.5 bg-gray-50 border border-border rounded hover:bg-gray-100" title="Isolate Subgraph"><Crosshair size={14} /></button>
                     )}
                  </div>
                  <div>
                    <div className="text-[10px] text-text-muted font-bold uppercase tracking-wider">Hop Distance</div>
                    <div className="text-text-main font-bold">{selectedNode.layer}</div>
                  </div>
                  <div className="p-3 bg-blue-50 border border-blue-100 rounded-md text-xs text-blue-900 leading-relaxed">
                    {isLoadingNodeProfile && 'Loading real account context...'}
                    {!isLoadingNodeProfile && selectedNodeProfile && (
                      <>
                        <div className="font-bold mb-1">Why this node is shown</div>
                        <div>{selectedNode.id === graphData.root_account
                          ? 'This is the source account selected for the investigation.'
                          : `This account is connected through the backend trail at hop ${selectedNode.layer}. The graph includes it because a real outgoing transaction links it to the investigated flow.`}</div>
                        <div className="mt-2 text-[11px]">{selectedNodeProfile.summary.incoming_count} incoming, {selectedNodeProfile.summary.outgoing_count} outgoing transactions and {selectedNodeProfile.summary.unique_counterparties} unique counterparties.</div>
                        {selectedNodeProfile.risk && selectedNodeProfile.risk.signals.length > 0 && (
                          <div className="mt-2"><strong>Detected signals:</strong> {selectedNodeProfile.risk.signals.map((signal: any) => signal.type).join(', ')}.</div>
                        )}
                        {selectedNodeProfile.detections.length === 0 && <div className="mt-2">No detector output is available for this account.</div>}
                      </>
                    )}
                  </div>
                  <button onClick={() => addEvidence(selectedNode, 'Account')} className="w-full px-3 py-1.5 bg-gray-50 border border-border text-xs font-bold rounded shadow-sm hover:bg-gray-100">Add to Evidence</button>
                </>
              )}

              {selectedEdge && (
                <>
                  <div>
                    <div className="text-[10px] text-text-muted font-bold uppercase tracking-wider">Transaction ID</div>
                    <div className="font-mono text-text-main font-bold mt-1 break-all">{selectedEdge.transaction_id || 'N/A'}</div>
                  </div>
                  <div className="p-3 bg-gray-50 border border-border rounded-md">
                    <div className="text-[10px] text-text-muted font-bold uppercase tracking-wider mb-1">Flow Direction</div>
                    <div className="flex flex-col gap-2">
                      <div className="font-mono text-xs font-bold text-text-main truncate">{selectedEdge.source.id || selectedEdge.source}</div>
                      <div className="flex justify-center"><div className="w-px h-4 bg-border relative"><div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-2 h-2 border-r-2 border-b-2 border-border rotate-45"></div></div></div>
                      <div className="font-mono text-xs font-bold text-primary truncate">{selectedEdge.target.id || selectedEdge.target}</div>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div><div className="text-[10px] text-text-muted font-bold uppercase">Amount</div><div className="font-bold">₹{(selectedEdge.amount || 0).toLocaleString()}</div></div>
                    <div><div className="text-[10px] text-text-muted font-bold uppercase">Timestamp</div><div className="font-bold text-xs">{selectedEdge.timestamp || 'N/A'}</div></div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div><div className="text-[10px] text-text-muted font-bold uppercase">Sender IFSC</div><div className="font-mono font-bold">{selectedEdge.sender_ifsc || 'Not available'}</div></div>
                    <div><div className="text-[10px] text-text-muted font-bold uppercase">Receiver IFSC</div><div className="font-mono font-bold">{selectedEdge.receiver_ifsc || 'Not available'}</div></div>
                  </div>
                  <button onClick={() => addEvidence(selectedEdge, 'Transaction')} className="w-full px-3 py-1.5 bg-gray-50 border border-border text-xs font-bold rounded shadow-sm hover:bg-gray-100">Add to Evidence</button>
                </>
              )}
            </div>
          </div>
        )}

        {/* Evidence Panel */}
        {evidencePanelOpen && (
          <div className="absolute top-4 right-[min(340px,calc(100%-2rem))] w-[min(320px,calc(100%-2rem))] bg-white/95 backdrop-blur border border-border rounded-lg shadow-lg z-10 flex flex-col max-h-[calc(100%-2rem)]">
            <div className="p-3 border-b border-border flex justify-between items-center bg-gray-50 rounded-t-lg">
              <span className="text-xs font-bold text-text-main uppercase tracking-wider">Selected Evidence</span>
              <button onClick={() => setEvidencePanelOpen(false)} className="text-text-muted hover:text-text-main font-bold">×</button>
            </div>
            <div className="p-4 overflow-y-auto flex-1 text-sm space-y-3">
              {evidence.length === 0 ? (
                <div className="text-center py-4 text-xs text-text-muted border-2 border-dashed border-border rounded-lg">No evidence selected.</div>
              ) : (
                evidence.map((ev, i) => (
                  <div key={i} className="p-3 bg-gray-50 border border-border rounded-md relative group">
                     <button onClick={() => setEvidence(prev => prev.filter((_, idx) => idx !== i))} className="absolute top-2 right-2 text-text-muted hover:text-danger opacity-0 group-hover:opacity-100 transition-opacity"><X size={12} /></button>
                     <div className="text-[10px] font-bold text-primary uppercase mb-1">{ev.type} Evidence</div>
                     <div className="font-mono text-xs font-bold">{ev.id || ev.transaction_id}</div>
                  </div>
                ))
              )}
            </div>
            {evidence.length > 0 && (
              <div className="p-3 border-t border-border bg-gray-50 rounded-b-lg">
                <button onClick={() => setEvidence([])} className="w-full px-3 py-1.5 text-danger border border-danger/20 text-xs font-bold rounded shadow-sm hover:bg-danger-light">Clear Evidence</button>
              </div>
            )}
          </div>
        )}

        {startTime && endTime && (
          <div className="absolute bottom-0 left-0 w-full bg-white border-t border-border p-4 shadow-sm z-20">
             <div className="flex flex-col max-w-5xl mx-auto">
                <div className="flex justify-between items-center mb-2">
                  <div className="text-xs font-bold text-text-main flex items-center gap-2"><span className="text-[10px] text-text-muted uppercase tracking-wider">Investigation Timeline</span></div>
                  <div className="text-xs font-bold text-primary bg-primary-light px-2 py-0.5 rounded border border-primary/20 shadow-sm">{formatTime(currentTime)}</div>
                </div>
                <div className="relative h-6 flex items-center group mb-4">
                  <div className="absolute w-full h-1.5 bg-gray-200 rounded-full cursor-pointer" onClick={(e) => { const rect = e.currentTarget.getBoundingClientRect(); const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width)); setCurrentTime(startTime + pct * (endTime - startTime)); }}>
                    <div className="absolute h-full bg-primary rounded-full" style={{ width: `${timelinePercent}%` }}></div>
                  </div>
                  <div className="absolute w-4 h-4 bg-white border-2 border-primary rounded-full shadow-sm -ml-2 cursor-grab transition-transform group-hover:scale-110" style={{ left: `${timelinePercent}%` }}></div>
                </div>
                <div className="flex items-center justify-between">
                   <div className="text-[10px] font-bold text-text-muted">{formatTime(startTime)}</div>
                   <div className="flex items-center gap-4">
                      <div className="flex bg-gray-50 rounded-md border border-border shadow-sm p-0.5">
                        <button onClick={() => setCurrentTime(startTime)} className="p-1.5 text-text-muted hover:bg-gray-100 rounded" title="Reset to Start"><SkipBack size={14} /></button>
                        <button onClick={() => { if (currentTime === endTime) setCurrentTime(startTime); setIsPlaying(!isPlaying); }} className={`p-1.5 rounded flex items-center gap-1 px-3 ${isPlaying ? 'bg-primary text-white font-bold' : 'text-text-main hover:bg-gray-100 font-bold'}`}>
                          {isPlaying ? <Pause size={14} /> : <Play size={14} />} {isPlaying ? 'Pause' : 'Play'}
                        </button>
                        <button onClick={() => setCurrentTime(prev => prev === null || startTime === null ? prev : Math.max(startTime, prev - 60 * 1000))} className="p-1.5 text-text-muted hover:bg-gray-100 rounded" title="Previous minute">Previous</button>
                        <button onClick={() => setCurrentTime(prev => prev === null || endTime === null ? prev : Math.min(endTime, prev + 60 * 1000))} className="p-1.5 text-text-muted hover:bg-gray-100 rounded" title="Next minute">Next</button>
                        <button onClick={() => setCurrentTime(endTime)} className="p-1.5 text-text-muted hover:bg-gray-100 rounded" title="Skip to End"><RotateCcw size={14} className="scale-x-[-1]" /></button>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-bold text-text-muted uppercase">Speed</span>
                        <select value={playbackSpeed} onChange={(e) => setPlaybackSpeed(Number(e.target.value))} className="text-xs border border-border bg-gray-50 rounded px-1.5 py-1 font-bold shadow-sm">
                          <option value={0.5}>0.5x</option><option value={1}>1x</option><option value={2}>2x</option><option value={5}>5x</option><option value={10}>10x</option>
                        </select>
                      </div>
                   </div>
                   <div className="text-[10px] font-bold text-text-muted">{formatTime(endTime)}</div>
                </div>
             </div>
          </div>
        )}
      </div>
    </div>
  );
}
