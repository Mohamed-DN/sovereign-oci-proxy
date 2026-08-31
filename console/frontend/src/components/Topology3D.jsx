import React, { useRef, useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import {
  Globe2,
  Maximize2,
  Minimize2,
  RotateCcw,
  Play,
  Pause,
  ZoomIn,
  ZoomOut,
  Shield,
  UserCheck,
  Server,
  Activity,
  Layers,
  Search
} from 'lucide-react';

export default function Topology3D({ onSelectNode }) {
  const canvasRef = useRef(null);
  const containerRef = useRef(null);
  const { role, user } = useAuth();

  const [nodes, setNodes] = useState([]);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [autoRotate, setAutoRotate] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRoleFilter, setSelectedRoleFilter] = useState('ALL');

  // 3D Camera & Transform state
  const cameraRef = useRef({
    rotX: 0.35,
    rotY: 0.45,
    zoom: 1.0,
    isDragging: false,
    lastMouseX: 0,
    lastMouseY: 0
  });

  // Load nodes based on role
  useEffect(() => {
    async function fetchNodes() {
      try {
        const nodeList = await api.nodes.list(role);
        setNodes(nodeList);
      } catch (err) {
        console.error('Failed to load topology nodes:', err);
      }
    }
    fetchNodes();
  }, [role]);

  // Compute 3D node coordinates
  const graphData = React.useMemo(() => {
    if (!nodes.length) return { nodes3D: [], links3D: [] };

    const filteredNodes = nodes.filter((n) => {
      const matchesSearch =
        n.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        n.overlay_ipv4.includes(searchQuery);
      const matchesRole =
        selectedRoleFilter === 'ALL' || n.role === selectedRoleFilter;
      return matchesSearch && matchesRole;
    });

    const isSuperAdmin = role === 'super-admin';
    const nodes3D = [];
    const links3D = [];

    if (isSuperAdmin) {
      // Super-Admin 3D Spiderweb Layout
      // Ring 0: Relays (Center Sphere, Radius 80)
      const relays = filteredNodes.filter((n) => n.role === 'RELAY');
      relays.forEach((node, i) => {
        const theta = (i / Math.max(1, relays.length)) * Math.PI * 2;
        nodes3D.push({
          ...node,
          x: Math.cos(theta) * 75,
          y: Math.sin(theta) * 35,
          z: Math.sin(theta) * 75,
          ring: 'center',
          size: 11,
          color: '#10b981' // emerald
        });
      });

      // Ring 1: Exit Gateways (Mid Sphere, Radius 160)
      const exits = filteredNodes.filter((n) => n.role === 'EXIT_BRIDGE');
      exits.forEach((node, i) => {
        const theta = (i / Math.max(1, exits.length)) * Math.PI * 2 + 0.5;
        const phi = ((i % 2 === 0 ? 1 : -1) * Math.PI) / 6;
        nodes3D.push({
          ...node,
          x: Math.cos(theta) * Math.cos(phi) * 160,
          y: Math.sin(phi) * 90,
          z: Math.sin(theta) * Math.cos(phi) * 160,
          ring: 'mid',
          size: 9,
          color: '#6366f1' // indigo
        });
      });

      // Ring 2: Client & Hybrid Nodes (Outer Shell, Radius 240)
      const clients = filteredNodes.filter(
        (n) => n.role === 'CLIENT_ORIGIN' || n.role === 'HYBRID'
      );
      clients.forEach((node, i) => {
        const theta = (i / Math.max(1, clients.length)) * Math.PI * 2 + 1.2;
        const phi = ((i % 3 - 1) * Math.PI) / 4;
        const isQuarantined = !!node.is_quarantined;
        nodes3D.push({
          ...node,
          x: Math.cos(theta) * Math.cos(phi) * 240,
          y: Math.sin(phi) * 130,
          z: Math.sin(theta) * Math.cos(phi) * 240,
          ring: 'outer',
          size: 7,
          color: isQuarantined ? '#f43f5e' : node.role === 'HYBRID' ? '#06b6d4' : '#38bdf8'
        });
      });

      // Generate Mesh Links
      // 1. Connect all relays in a full mesh backbone
      const relayIndices = nodes3D
        .map((n, idx) => (n.role === 'RELAY' ? idx : -1))
        .filter((i) => i !== -1);
      for (let i = 0; i < relayIndices.length; i++) {
        for (let j = i + 1; j < relayIndices.length; j++) {
          links3D.push({
            source: relayIndices[i],
            target: relayIndices[j],
            color: 'rgba(16, 185, 129, 0.4)',
            pulseSpeed: 0.02
          });
        }
      }

      // 2. Connect Exits and Clients to nearest Relay
      nodes3D.forEach((targetNode, targetIdx) => {
        if (targetNode.role !== 'RELAY' && relayIndices.length > 0) {
          const nearestRelayIdx = relayIndices[targetIdx % relayIndices.length];
          links3D.push({
            source: nearestRelayIdx,
            target: targetIdx,
            color: targetNode.is_quarantined
              ? 'rgba(244, 63, 94, 0.2)'
              : 'rgba(6, 182, 212, 0.25)',
            pulseSpeed: targetNode.is_quarantined ? 0 : 0.015
          });
        }
      });
    } else {
      // Regular User Isolated Topology (Tenant Scoped)
      // Alice's personal nodes connected to designated Relay
      const relayNode = filteredNodes.find((n) => n.role === 'RELAY') || {
        id: 'node_relay_us_east',
        name: 'neronet-relay-iad-01',
        role: 'RELAY',
        overlay_ipv4: '100.64.0.1',
        country_code: 'US'
      };

      nodes3D.push({
        ...relayNode,
        x: 0,
        y: 0,
        z: 0,
        ring: 'center',
        size: 13,
        color: '#10b981'
      });

      const userNodes = filteredNodes.filter((n) => n.role !== 'RELAY');
      userNodes.forEach((node, i) => {
        const theta = (i / Math.max(1, userNodes.length)) * Math.PI * 2;
        nodes3D.push({
          ...node,
          x: Math.cos(theta) * 160,
          y: Math.sin(theta) * 60,
          z: Math.sin(theta) * 160,
          ring: 'outer',
          size: 9,
          color: node.role === 'HYBRID' ? '#06b6d4' : '#38bdf8'
        });

        // Direct connection to Relay
        links3D.push({
          source: 0,
          target: i + 1,
          color: 'rgba(6, 182, 212, 0.45)',
          pulseSpeed: 0.02
        });
      });

      // P2P link between Alice's devices
      if (userNodes.length >= 2) {
        links3D.push({
          source: 1,
          target: 2,
          color: 'rgba(99, 102, 241, 0.4)',
          pulseSpeed: 0.025,
          dashed: true
        });
      }
    }

    return { nodes3D, links3D };
  }, [nodes, role, searchQuery, selectedRoleFilter]);

  // 3D Canvas Projection & Animation Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;
    let pulsePhase = 0;

    const handleResize = () => {
      if (canvas && containerRef.current) {
        canvas.width = containerRef.current.clientWidth;
        canvas.height = containerRef.current.clientHeight || 560;
      }
    };
    handleResize();
    window.addEventListener('resize', handleResize);

    const render = () => {
      pulsePhase += 0.015;
      if (autoRotate && !cameraRef.current.isDragging) {
        cameraRef.current.rotY += 0.003;
      }

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const cx = canvas.width / 2;
      const cy = canvas.height / 2;
      const fov = 400;
      const { rotX, rotY, zoom } = cameraRef.current;

      const cosX = Math.cos(rotX);
      const sinX = Math.sin(rotX);
      const cosY = Math.cos(rotY);
      const sinY = Math.sin(rotY);

      // Project 3D to 2D
      const projectedNodes = graphData.nodes3D.map((node) => {
        // Y-axis rotation
        let x1 = node.x * cosY + node.z * sinY;
        let y1 = node.y;
        let z1 = -node.x * sinY + node.z * cosY;

        // X-axis rotation
        let x2 = x1;
        let y2 = y1 * cosX - z1 * sinX;
        let z2 = y1 * sinX + z1 * cosX + 450 / zoom;

        const scale = fov / Math.max(1, z2);
        const projX = cx + x2 * scale;
        const projY = cy + y2 * scale;

        return {
          ...node,
          projX,
          projY,
          scale,
          z2
        };
      });

      // Sort back-to-front for proper depth rendering
      projectedNodes.sort((a, b) => b.z2 - a.z2);

      // Draw 3D Radial Grid Rings (Spiderweb Plane)
      ctx.strokeStyle = 'rgba(39, 39, 42, 0.4)';
      ctx.lineWidth = 1;
      [80, 160, 240].forEach((radius) => {
        ctx.beginPath();
        for (let i = 0; i <= 64; i++) {
          const theta = (i / 64) * Math.PI * 2;
          const gx = Math.cos(theta) * radius;
          const gz = Math.sin(theta) * radius;
          const gy = 0;

          let x1 = gx * cosY + gz * sinY;
          let y1 = gy;
          let z1 = -gx * sinY + gz * cosY;
          let x2 = x1;
          let y2 = y1 * cosX - z1 * sinX;
          let z2 = y1 * sinX + z1 * cosX + 450 / zoom;

          const scale = fov / Math.max(1, z2);
          const px = cx + x2 * scale;
          const py = cy + y2 * scale;

          if (i === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.stroke();
      });

      // Draw Links
      graphData.links3D.forEach((link) => {
        const src = projectedNodes.find((n) => n.id === graphData.nodes3D[link.source]?.id);
        const tgt = projectedNodes.find((n) => n.id === graphData.nodes3D[link.target]?.id);

        if (src && tgt && src.z2 > 50 && tgt.z2 > 50) {
          ctx.beginPath();
          ctx.moveTo(src.projX, src.projY);
          ctx.lineTo(tgt.projX, tgt.projY);
          ctx.strokeStyle = link.color;
          ctx.lineWidth = Math.max(1, 1.5 * ((src.scale + tgt.scale) / 2));
          if (link.dashed) ctx.setLineDash([4, 4]);
          else ctx.setLineDash([]);
          ctx.stroke();
          ctx.setLineDash([]);

          // Animated pulse photons traversing the link
          if (link.pulseSpeed > 0) {
            const t = (pulsePhase * 2) % 1;
            const px = src.projX + (tgt.projX - src.projX) * t;
            const py = src.projY + (tgt.projY - src.projY) * t;
            ctx.beginPath();
            ctx.arc(px, py, 2.5 * src.scale, 0, Math.PI * 2);
            ctx.fillStyle = '#06b6d4';
            ctx.shadowColor = '#06b6d4';
            ctx.shadowBlur = 8;
            ctx.fill();
            ctx.shadowBlur = 0;
          }
        }
      });

      // Draw Nodes
      projectedNodes.forEach((node) => {
        if (node.z2 <= 50) return;

        const isHovered = hoveredNode?.id === node.id;
        const radius = node.size * node.scale * (isHovered ? 1.4 : 1.0);

        // Node Glow Aura
        ctx.beginPath();
        ctx.arc(node.projX, node.projY, radius * 2.2, 0, Math.PI * 2);
        ctx.fillStyle = node.color.replace(')', ', 0.15)').replace('rgb', 'rgba').replace('#', '');
        ctx.fillStyle = isHovered ? 'rgba(6, 182, 212, 0.3)' : 'rgba(99, 102, 241, 0.15)';
        ctx.fill();

        // Node Core Sphere
        ctx.beginPath();
        ctx.arc(node.projX, node.projY, radius, 0, Math.PI * 2);
        ctx.fillStyle = node.color;
        ctx.shadowColor = node.color;
        ctx.shadowBlur = isHovered ? 20 : 10;
        ctx.fill();
        ctx.shadowBlur = 0;

        // Inner highlight
        ctx.beginPath();
        ctx.arc(node.projX - radius * 0.3, node.projY - radius * 0.3, radius * 0.35, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
        ctx.fill();

        // Node Label
        if (node.scale > 0.6 || isHovered) {
          ctx.font = `${Math.max(10, Math.round(11 * node.scale))}px JetBrains Mono, monospace`;
          ctx.fillStyle = isHovered ? '#ffffff' : '#94a3b8';
          ctx.textAlign = 'center';
          ctx.fillText(node.name, node.projX, node.projY + radius + 13 * node.scale);
        }
      });

      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
    };
  }, [graphData, autoRotate, hoveredNode]);

  // Mouse & Touch Interaction Handlers
  const handleMouseDown = (e) => {
    cameraRef.current.isDragging = true;
    cameraRef.current.lastMouseX = e.clientX;
    cameraRef.current.lastMouseY = e.clientY;
  };

  const handleMouseMove = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    if (cameraRef.current.isDragging) {
      const deltaX = e.clientX - cameraRef.current.lastMouseX;
      const deltaY = e.clientY - cameraRef.current.lastMouseY;
      cameraRef.current.rotY += deltaX * 0.006;
      cameraRef.current.rotX = Math.max(-1.2, Math.min(1.2, cameraRef.current.rotX + deltaY * 0.006));
      cameraRef.current.lastMouseX = e.clientX;
      cameraRef.current.lastMouseY = e.clientY;
    }

    // Hit Testing for hover
    const canvas = canvasRef.current;
    if (!canvas) return;
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    const fov = 400;
    const { rotX, rotY, zoom } = cameraRef.current;
    const cosX = Math.cos(rotX);
    const sinX = Math.sin(rotX);
    const cosY = Math.cos(rotY);
    const sinY = Math.sin(rotY);

    let found = null;
    for (const node of graphData.nodes3D) {
      let x1 = node.x * cosY + node.z * sinY;
      let y1 = node.y;
      let z1 = -node.x * sinY + node.z * cosY;
      let x2 = x1;
      let y2 = y1 * cosX - z1 * sinX;
      let z2 = y1 * sinX + z1 * cosX + 450 / zoom;

      if (z2 > 50) {
        const scale = fov / z2;
        const px = cx + x2 * scale;
        const py = cy + y2 * scale;
        const dist = Math.hypot(mouseX - px, mouseY - py);
        if (dist < node.size * scale + 8) {
          found = node;
          break;
        }
      }
    }
    setHoveredNode(found);
  };

  const handleMouseUp = () => {
    cameraRef.current.isDragging = false;
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const zoomDelta = e.deltaY * -0.0015;
    cameraRef.current.zoom = Math.max(0.4, Math.min(2.5, cameraRef.current.zoom + zoomDelta));
  };

  const handleClick = () => {
    if (hoveredNode && onSelectNode) {
      onSelectNode(hoveredNode);
    }
  };

  const resetCamera = () => {
    cameraRef.current.rotX = 0.35;
    cameraRef.current.rotY = 0.45;
    cameraRef.current.zoom = 1.0;
  };

  const isSuperAdmin = role === 'super-admin';

  return (
    <div className="space-y-4">
      {/* Header Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
            <span>3D Spiderweb Mesh Topology</span>
            <span className={`text-xs font-mono px-2 py-0.5 rounded border ${
              isSuperAdmin
                ? 'bg-neon-indigo/20 text-neon-indigo border-neon-indigo/40'
                : 'bg-neon-emerald/20 text-neon-emerald border-neon-emerald/40'
            }`}>
              {isSuperAdmin ? 'Global Mesh (Super-Admin)' : 'Isolated Mesh (Alice)'}
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            {isSuperAdmin
              ? 'Complete sovereign topology visualizer: Regional Relays, Exit Gateways, and multi-tenant clients.'
              : 'Zero-Knowledge scoped view: Strictly Alice’s personal devices connected to regional relay.'}
          </p>
        </div>

        {/* Filter / Search Bar */}
        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter node..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs bg-dark-card border border-dark-border rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-neon-cyan font-mono"
            />
          </div>

          <select
            value={selectedRoleFilter}
            onChange={(e) => setSelectedRoleFilter(e.target.value)}
            className="px-2.5 py-1.5 text-xs bg-dark-card border border-dark-border rounded-lg text-slate-200 focus:outline-none focus:border-neon-cyan font-mono"
          >
            <option value="ALL">All Roles</option>
            <option value="RELAY">Relays</option>
            <option value="EXIT_BRIDGE">Exits</option>
            <option value="CLIENT_ORIGIN">Clients</option>
            <option value="HYBRID">Hybrid</option>
          </select>
        </div>
      </div>

      {/* 3D Canvas Viewport */}
      <div
        ref={containerRef}
        className="relative w-full h-[580px] rounded-2xl bg-dark-card border border-dark-border overflow-hidden shadow-2xl group cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        onClick={handleClick}
      >
        <canvas ref={canvasRef} className="w-full h-full block" />

        {/* HUD Top Left: Mode & Node Counts */}
        <div className="absolute top-4 left-4 p-3 rounded-xl bg-dark-canvas/90 border border-dark-border/80 backdrop-blur-md text-xs font-mono space-y-1.5 pointer-events-none">
          <div className="flex items-center space-x-2 text-slate-300">
            <Layers className="w-3.5 h-3.5 text-neon-cyan" />
            <span className="font-bold">
              {isSuperAdmin ? 'Mesh Scope: GLOBAL' : 'Mesh Scope: TENANT_ISOLATED'}
            </span>
          </div>
          <div className="text-[11px] text-slate-400 space-y-0.5">
            <div>Rendered Nodes: <strong className="text-white">{graphData.nodes3D.length}</strong></div>
            <div>Active Circuits: <strong className="text-neon-cyan">{graphData.links3D.length}</strong></div>
          </div>
        </div>

        {/* HUD Top Right: Controls */}
        <div className="absolute top-4 right-4 flex items-center space-x-1.5 p-1.5 rounded-xl bg-dark-canvas/90 border border-dark-border/80 backdrop-blur-md">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setAutoRotate(!autoRotate);
            }}
            className={`p-2 rounded-lg text-xs font-mono transition-all ${
              autoRotate
                ? 'bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/40'
                : 'text-slate-400 hover:text-white'
            }`}
            title="Toggle Auto-Rotation"
          >
            {autoRotate ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              cameraRef.current.zoom = Math.min(2.5, cameraRef.current.zoom + 0.2);
            }}
            className="p-2 rounded-lg text-slate-400 hover:text-white text-xs"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              cameraRef.current.zoom = Math.max(0.4, cameraRef.current.zoom - 0.2);
            }}
            className="p-2 rounded-lg text-slate-400 hover:text-white text-xs"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={(e) => {
              e.stopPropagation();
              resetCamera();
            }}
            className="p-2 rounded-lg text-slate-400 hover:text-white text-xs"
            title="Reset Perspective"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* HUD Bottom Left: Color Legend */}
        <div className="absolute bottom-4 left-4 p-3 rounded-xl bg-dark-canvas/90 border border-dark-border/80 backdrop-blur-md text-[11px] font-mono space-y-1.5 pointer-events-none">
          <div className="text-slate-400 font-bold mb-1">Topology Ring Legend</div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-neon-emerald"></span>
            <span className="text-slate-300">Regional Relays (Center Ring)</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-neon-indigo"></span>
            <span className="text-slate-300">Exit Gateways (Mid Ring)</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400"></span>
            <span className="text-slate-300">Client / Hybrid Devices (Outer Ring)</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-neon-rose"></span>
            <span className="text-slate-300">Zero-Trust Quarantined</span>
          </div>
        </div>

        {/* Hover Tooltip HUD */}
        {hoveredNode && (
          <div className="absolute bottom-4 right-4 p-4 rounded-xl bg-dark-canvas/95 border border-neon-cyan/50 backdrop-blur-md text-xs font-mono shadow-2xl pointer-events-none min-w-[240px] animate-in fade-in duration-100">
            <div className="flex items-center justify-between border-b border-dark-border pb-1.5 mb-2">
              <span className="font-bold text-slate-100">{hoveredNode.name}</span>
              <span className="text-[10px] text-neon-cyan px-1.5 py-0.5 rounded bg-neon-cyan/20">
                {hoveredNode.role}
              </span>
            </div>
            <div className="space-y-1 text-[11px] text-slate-400">
              <div className="flex justify-between">
                <span>Overlay IPv4:</span>
                <span className="text-slate-200">{hoveredNode.overlay_ipv4}</span>
              </div>
              <div className="flex justify-between">
                <span>Location:</span>
                <span className="text-slate-200">{hoveredNode.country_code} ({hoveredNode.city || 'Regional'})</span>
              </div>
              <div className="flex justify-between">
                <span>Latency:</span>
                <span className="text-neon-emerald font-bold">{hoveredNode.latency_ms || 12.0} ms</span>
              </div>
              <div className="flex justify-between">
                <span>Posture:</span>
                <span className={hoveredNode.is_quarantined ? 'text-neon-rose font-bold' : 'text-neon-emerald'}>
                  {hoveredNode.is_quarantined ? 'QUARANTINED' : 'Compliant'}
                </span>
              </div>
            </div>
            <div className="mt-2 pt-1.5 border-t border-dark-border text-[10px] text-neon-cyan font-bold text-center">
              Click to Open Node Action Drawer &rarr;
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
