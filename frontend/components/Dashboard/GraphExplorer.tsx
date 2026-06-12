'use client';

import React, { useState, useEffect, useRef } from 'react';
import { api, GraphNode, GraphRelationship } from '../../services/api';
import { Search, ZoomIn, ZoomOut, RotateCcw, AlertCircle, Info, RefreshCw } from 'lucide-react';

interface SimulationNode extends GraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  color: string;
}

interface SimulationRelationship extends GraphRelationship {
  sourceNode: SimulationNode;
  targetNode: SimulationNode;
}

const CATEGORY_COLORS: Record<string, string> = {
  disease: '#ef4444', // Red
  drug: '#3b82f6',    // Blue
  symptom: '#f59e0b', // Amber
  organ: '#10b981',   // Emerald
  treatment: '#8b5cf6', // Violet
  default: '#6b7280',   // Gray
};

export function GraphExplorer() {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [relationships, setRelationships] = useState<GraphRelationship[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Search and Filter states
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedLabel, setSelectedLabel] = useState<string>('all');
  const [selectedNode, setSelectedNode] = useState<SimulationNode | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const simNodesRef = useRef<SimulationNode[]>([]);
  const simRelsRef = useRef<SimulationRelationship[]>([]);
  const animationFrameRef = useRef<number | null>(null);

  // Zoom and Pan states
  const transformRef = useRef({ x: 0, y: 0, zoom: 1 });
  const isDraggingCanvasRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });
  const draggedNodeRef = useRef<SimulationNode | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getGraph();
      setNodes(data.nodes);
      setRelationships(data.relationships);
    } catch (err: any) {
      console.error(err);
      setError('Failed to load knowledge graph from Neo4j database. Ensure Neo4j is running and populated.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Initialize simulation data when nodes/relationships load
  useEffect(() => {
    if (nodes.length === 0) return;

    const canvas = canvasRef.current;
    const width = canvas?.parentElement?.clientWidth || 800;
    const height = canvas?.parentElement?.clientHeight || 500;

    // Create simulation nodes with random starting points
    const simNodes: SimulationNode[] = nodes.map((n, idx) => {
      // Find color based on labels (case insensitive)
      let color = CATEGORY_COLORS.default;
      const primaryLabel = n.labels[0]?.toLowerCase() || 'default';
      for (const [key, val] of Object.entries(CATEGORY_COLORS)) {
        if (primaryLabel.includes(key)) {
          color = val;
          break;
        }
      }

      // Arrange in a soft circle around center
      const angle = (idx / nodes.length) * 2 * Math.PI;
      const radius = 100 + Math.random() * 100;

      return {
        ...n,
        x: width / 2 + Math.cos(angle) * radius,
        y: height / 2 + Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
        radius: 20 + Math.min(n.name.length * 0.5, 12),
        color,
      };
    });

    // Match relationship strings to simulated node references
    const simRels: SimulationRelationship[] = relationships
      .map(r => {
        const sourceNode = simNodes.find(n => n.name.toLowerCase() === r.source.toLowerCase());
        const targetNode = simNodes.find(n => n.name.toLowerCase() === r.target.toLowerCase());
        if (sourceNode && targetNode) {
          return {
            ...r,
            sourceNode,
            targetNode,
          };
        }
        return null;
      })
      .filter((r): r is SimulationRelationship => r !== null);

    simNodesRef.current = simNodes;
    simRelsRef.current = simRels;

    // Reset center transform
    transformRef.current = { x: 0, y: 0, zoom: 0.95 };

    // Start force-directed loop
    const runSimulation = () => {
      const kRepulsion = 1500; // Node push-back force
      const kAttraction = 0.04; // Link pull-back force
      const gravity = 0.03;    // Pull nodes to center
      const friction = 0.82;   // Speed decay
      
      const cx = width / 2;
      const cy = height / 2;

      // 1. Repulsion between all node pairs
      for (let i = 0; i < simNodes.length; i++) {
        const n1 = simNodes[i];
        for (let j = i + 1; j < simNodes.length; j++) {
          const n2 = simNodes[j];
          const dx = n2.x - n1.x;
          const dy = n2.y - n1.y;
          const distSq = dx * dx + dy * dy + 0.1;
          const dist = Math.sqrt(distSq);

          if (dist < 400) {
            const force = kRepulsion / distSq;
            const fx = (dx / dist) * force;
            const fy = (dy / dist) * force;

            if (n1 !== draggedNodeRef.current) {
              n1.vx -= fx;
              n1.vy -= fy;
            }
            if (n2 !== draggedNodeRef.current) {
              n2.vx += fx;
              n2.vy += fy;
            }
          }
        }
      }

      // 2. Attraction along relationships
      for (const rel of simRels) {
        const n1 = rel.sourceNode;
        const n2 = rel.targetNode;
        const dx = n2.x - n1.x;
        const dy = n2.y - n1.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const force = (dist - 140) * kAttraction; // 140 is target link length
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        if (n1 !== draggedNodeRef.current) {
          n1.vx += fx;
          n1.vy += fy;
        }
        if (n2 !== draggedNodeRef.current) {
          n2.vx -= fx;
          n2.vy -= fy;
        }
      }

      // 3. Central gravity and integration
      for (const n of simNodes) {
        if (n === draggedNodeRef.current) continue;

        // Pull to center
        n.vx += (cx - n.x) * gravity;
        n.vy += (cy - n.y) * gravity;

        // Apply velocity & friction
        n.x += n.vx;
        n.y += n.vy;
        n.vx *= friction;
        n.vy *= friction;
      }

      // Render updated positions to canvas
      drawCanvas(width, height);
      animationFrameRef.current = requestAnimationFrame(runSimulation);
    };

    animationFrameRef.current = requestAnimationFrame(runSimulation);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [nodes, relationships, searchQuery, selectedLabel]);

  // Main canvas draw routine
  const drawCanvas = (w: number, h: number) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Handle high-DPI scaling
    const dpr = window.devicePixelRatio || 1;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Apply zoom & pan transformations
    ctx.save();
    ctx.translate(transformRef.current.x, transformRef.current.y);
    ctx.scale(transformRef.current.zoom, transformRef.current.zoom);

    // Filter nodes/relationships based on search and tabs
    const filteredNodes = simNodesRef.current.filter(n => {
      const matchQuery = n.name.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          (n.labels[0] || '').toLowerCase().includes(searchQuery.toLowerCase());
      const matchLabel = selectedLabel === 'all' || 
                         (n.labels[0] || '').toLowerCase().includes(selectedLabel.toLowerCase());
      return matchQuery && matchLabel;
    });

    const filteredRels = simRelsRef.current.filter(rel => {
      const sourceVisible = filteredNodes.some(n => n.name === rel.source);
      const targetVisible = filteredNodes.some(n => n.name === rel.target);
      return sourceVisible && targetVisible;
    });

    // 1. Draw relationship lines
    ctx.lineWidth = 2.5;
    for (const rel of filteredRels) {
      const s = rel.sourceNode;
      const t = rel.targetNode;

      const isHighlighted = selectedNode && (selectedNode.name === s.name || selectedNode.name === t.name);

      ctx.beginPath();
      ctx.moveTo(s.x, s.y);
      ctx.lineTo(t.x, t.y);
      ctx.strokeStyle = isHighlighted ? '#14b8a6' : '#e2e8f0';
      ctx.lineWidth = isHighlighted ? 3.5 : 1.5;
      ctx.stroke();

      // Relation type label in center
      const mx = (s.x + t.x) / 2;
      const my = (s.y + t.y) / 2;
      ctx.save();
      ctx.fillStyle = isHighlighted ? '#0d9488' : '#94a3b8';
      ctx.font = 'bold 9px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      
      // Draw small backing label bubble
      const textWidth = ctx.measureText(rel.relation).width + 6;
      ctx.fillStyle = '#ffffff';
      ctx.fillRect(mx - textWidth / 2, my - 6, textWidth, 12);
      ctx.fillStyle = isHighlighted ? '#0d9488' : '#64748b';
      ctx.fillText(rel.relation, mx, my);
      ctx.restore();
    }

    // 2. Draw nodes
    for (const n of filteredNodes) {
      const isSelected = selectedNode && selectedNode.name === n.name;

      // Outer ring for selected node
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius + 6, 0, 2 * Math.PI);
        ctx.fillStyle = 'rgba(20, 184, 166, 0.25)';
        ctx.fill();
        ctx.strokeStyle = '#14b8a6';
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Base circle
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius, 0, 2 * Math.PI);
      ctx.fillStyle = n.color;
      ctx.shadowColor = 'rgba(0,0,0,0.06)';
      ctx.shadowBlur = 4;
      ctx.shadowOffsetY = 2;
      ctx.fill();
      ctx.shadowColor = 'transparent'; // Reset shadow

      // White inner text container
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 11px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      
      // Wrap text if too long
      const words = n.name.split(' ');
      if (words.length > 1 && n.name.length > 10) {
        ctx.fillText(words[0], n.x, n.y - 6);
        ctx.fillText(words.slice(1).join(' '), n.x, n.y + 6);
      } else {
        ctx.fillText(n.name, n.x, n.y);
      }

      // Small bubble showing node label type
      const label = n.labels[0] || '';
      ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
      ctx.font = '7px Inter, sans-serif';
      const typeW = ctx.measureText(label.toUpperCase()).width + 4;
      ctx.fillRect(n.x - typeW / 2, n.y + n.radius - 2, typeW, 8);
      ctx.fillStyle = '#1e293b';
      ctx.fillText(label.toUpperCase(), n.x, n.y + n.radius + 2);
    }

    ctx.restore();
  };

  // Canvas Mouse / Gesture interactions
  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const clientY = e.clientY - rect.top;

    // Translate client coordinates back into simulation coordinates based on pan & zoom
    const simX = (clientX - transformRef.current.x) / transformRef.current.zoom;
    const simY = (clientY - transformRef.current.y) / transformRef.current.zoom;

    // Check if clicked a node
    let foundNode: SimulationNode | null = null;
    for (const n of simNodesRef.current) {
      const dx = n.x - simX;
      const dy = n.y - simY;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < n.radius) {
        foundNode = n;
        break;
      }
    }

    if (foundNode) {
      draggedNodeRef.current = foundNode;
      setSelectedNode(foundNode);
    } else {
      isDraggingCanvasRef.current = true;
      dragStartRef.current = { x: e.clientX, y: e.clientY };
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (draggedNodeRef.current) {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const clientX = e.clientX - rect.left;
      const clientY = e.clientY - rect.top;

      // Update node's position
      draggedNodeRef.current.x = (clientX - transformRef.current.x) / transformRef.current.zoom;
      draggedNodeRef.current.y = (clientY - transformRef.current.y) / transformRef.current.zoom;
      draggedNodeRef.current.vx = 0;
      draggedNodeRef.current.vy = 0;
    } else if (isDraggingCanvasRef.current) {
      const dx = e.clientX - dragStartRef.current.x;
      const dy = e.clientY - dragStartRef.current.y;
      transformRef.current.x += dx;
      transformRef.current.y += dy;
      dragStartRef.current = { x: e.clientX, y: e.clientY };
    }
  };

  const handleMouseUp = () => {
    draggedNodeRef.current = null;
    isDraggingCanvasRef.current = false;
  };

  const zoom = (factor: number) => {
    transformRef.current.zoom = Math.max(0.15, Math.min(transformRef.current.zoom * factor, 4));
  };

  const resetTransform = () => {
    transformRef.current = { x: 0, y: 0, zoom: 0.95 };
  };

  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Tab Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-sm z-10">
        <div>
          <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            Clinical Knowledge Graph Explorer
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Interactive visualization of extracted medical entities and relationships inside Neo4j.
          </p>
        </div>
        
        {/* Actions/Reload */}
        <button
          onClick={fetchData}
          className="flex items-center gap-2 text-xs bg-teal-50 text-teal-700 hover:bg-teal-100 font-semibold px-3.5 py-2 rounded-xl transition shadow-sm border border-teal-200/50 self-start"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Reload Graph
        </button>
      </header>

      {/* Main Panel splitting Visualizer and Detail Inspector */}
      <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
        
        {/* Visualizer Area */}
        <div className="flex-1 flex flex-col relative overflow-hidden bg-slate-100">
          
          {/* Controls Overlay */}
          <div className="absolute top-4 left-4 flex flex-wrap items-center gap-2.5 z-20">
            {/* Search Input */}
            <div className="relative bg-white shadow-md rounded-xl border border-slate-200">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
              <input
                type="text"
                placeholder="Search node name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 pr-4 py-2 text-sm text-slate-700 bg-transparent rounded-xl focus:outline-none w-52"
              />
            </div>

            {/* Label Filter tabs */}
            <div className="bg-white shadow-md rounded-xl border border-slate-200 p-1 flex gap-1 text-xs font-semibold text-slate-600">
              {['all', 'disease', 'drug', 'symptom', 'organ', 'treatment'].map((lbl) => (
                <button
                  key={lbl}
                  onClick={() => setSelectedLabel(lbl)}
                  className={`px-3 py-1.5 rounded-lg capitalize transition-colors ${
                    selectedLabel === lbl
                      ? 'bg-teal-600 text-white'
                      : 'hover:bg-slate-100 text-slate-600'
                  }`}
                >
                  {lbl}
                </button>
              ))}
            </div>
          </div>

          {/* Canvas Utilities (Zoom Buttons) */}
          <div className="absolute bottom-4 left-4 flex flex-col gap-1.5 z-20">
            <button
              onClick={() => zoom(1.25)}
              className="bg-white hover:bg-slate-50 text-slate-700 p-2.5 shadow-md rounded-xl border border-slate-200 transition-colors"
              title="Zoom In"
            >
              <ZoomIn size={16} />
            </button>
            <button
              onClick={() => zoom(0.8)}
              className="bg-white hover:bg-slate-50 text-slate-700 p-2.5 shadow-md rounded-xl border border-slate-200 transition-colors"
              title="Zoom Out"
            >
              <ZoomOut size={16} />
            </button>
            <button
              onClick={resetTransform}
              className="bg-white hover:bg-slate-50 text-slate-700 p-2.5 shadow-md rounded-xl border border-slate-200 transition-colors"
              title="Recenter"
            >
              <RotateCcw size={16} />
            </button>
          </div>

          {/* Legend Overlay */}
          <div className="absolute bottom-4 right-4 bg-white/95 backdrop-blur shadow-md rounded-xl border border-slate-200 p-3.5 z-20 text-[11px] font-semibold text-slate-600 flex flex-col gap-2.5">
            <div className="text-[10px] text-slate-400 uppercase tracking-wider font-bold">Node Category Colors</div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2">
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-[#ef4444]" /> Disease
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-[#3b82f6]" /> Drug
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-[#f59e0b]" /> Symptom
              </div>
              <div className="flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-[#10b981]" /> Organ
              </div>
              <div className="flex items-center gap-2 text-left">
                <span className="w-3 h-3 rounded-full bg-[#8b5cf6]" /> Treatment
              </div>
            </div>
          </div>

          {/* Core Interactive Canvas */}
          {loading ? (
            <div className="flex-1 flex flex-col items-center justify-center gap-3">
              <RefreshCw size={28} className="animate-spin text-teal-600" />
              <span className="text-sm font-semibold text-slate-500">Querying Neo4j Graph Database...</span>
            </div>
          ) : error ? (
            <div className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-md mx-auto gap-4">
              <div className="w-12 h-12 rounded-full bg-rose-50 flex items-center justify-center text-rose-500">
                <AlertCircle size={28} />
              </div>
              <h3 className="text-base font-bold text-slate-800">Connection Failed</h3>
              <p className="text-xs leading-relaxed text-slate-500">{error}</p>
              <button
                onClick={fetchData}
                className="bg-teal-600 text-white font-semibold hover:bg-teal-700 px-4 py-2 rounded-xl text-xs transition shadow-sm"
              >
                Retry Connection
              </button>
            </div>
          ) : nodes.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-6 gap-3">
              <Info size={28} className="text-slate-400" />
              <h3 className="text-sm font-bold text-slate-700">Graph is Currently Empty</h3>
              <p className="text-xs text-slate-500 max-w-xs leading-relaxed">
                Ingest medical research PDF documents using the Ingest Documents panel to populate the clinical graph.
              </p>
            </div>
          ) : (
            <canvas
              ref={canvasRef}
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
              className="flex-1 cursor-grab active:cursor-grabbing h-full w-full"
            />
          )}
        </div>

        {/* Sidebar Inspector Panel */}
        <div className="w-full lg:w-80 bg-white border-t lg:border-t-0 lg:border-l border-slate-200 p-6 flex flex-col overflow-y-auto z-10 shrink-0">
          <h3 className="text-sm font-bold text-slate-800 border-b border-slate-100 pb-3 mb-4 uppercase tracking-wider">
            Graph Inspector
          </h3>

          {selectedNode ? (
            <div className="flex flex-col gap-4">
              {/* Highlight Card */}
              <div className="bg-slate-50 rounded-2xl p-4 border border-slate-100">
                <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">Node Name</div>
                <div className="text-base font-extrabold text-slate-800 mt-1">{selectedNode.name}</div>
                
                <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold mt-4">Node Type</div>
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold text-white mt-1.5" style={{ backgroundColor: selectedNode.color }}>
                  {selectedNode.labels[0] || 'Unknown'}
                </div>
              </div>

              {/* Relationship listing */}
              <div>
                <h4 className="text-xs font-bold text-slate-600 mb-2 uppercase tracking-wide">Connected Relationships</h4>
                
                {simRelsRef.current.filter(r => r.source === selectedNode.name || r.target === selectedNode.name).length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No relationships recorded for this entity.</p>
                ) : (
                  <div className="flex flex-col gap-2">
                    {simRelsRef.current
                      .filter(r => r.source === selectedNode.name || r.target === selectedNode.name)
                      .map((rel, idx) => {
                        const isSource = rel.source === selectedNode.name;
                        const partner = isSource ? rel.target : rel.source;
                        return (
                          <div key={idx} className="flex flex-col p-3 border border-slate-100 rounded-xl bg-slate-50/50 hover:bg-slate-50 transition-colors">
                            <div className="flex items-center justify-between gap-2 text-xs">
                              <span className="font-bold text-slate-700 truncate">{selectedNode.name}</span>
                              <span className="px-2 py-0.5 rounded bg-teal-50 text-teal-700 font-extrabold text-[9px] uppercase border border-teal-100">
                                {rel.relation}
                              </span>
                              <span className="font-bold text-slate-700 truncate">{partner}</span>
                            </div>
                            <div className="text-[10px] text-slate-400 mt-1.5 italic">
                              Direction: {isSource ? 'Outbound relation' : 'Inbound relation'}
                            </div>
                          </div>
                        );
                      })}
                  </div>
                )}
              </div>

              {/* Helper */}
              <div className="text-[11px] leading-relaxed text-slate-400 bg-slate-50/50 rounded-xl p-3 mt-4 border border-slate-100 flex gap-2">
                <Info size={14} className="shrink-0 text-slate-400 mt-0.5" />
                <span>You can drag nodes to rearrange the visual layout and double click the background canvas to reset focus.</span>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-slate-400 gap-3 border-2 border-dashed border-slate-100 rounded-2xl my-2">
              <Info size={24} className="text-slate-300 animate-pulse" />
              <p className="text-xs font-medium max-w-[180px]">
                Click on any node in the graph layout to inspect its labels and relationships.
              </p>
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
