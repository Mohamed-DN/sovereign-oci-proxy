import React, { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import * as THREE from 'three';
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
  Search,
  Zap,
  Radio,
  Network,
  AlertTriangle,
  Flame,
  Info
} from 'lucide-react';

export default function Topology3D({ onSelectNode }) {
  const fgRef = useRef(null);
  const containerRef = useRef(null);
  const { role } = useAuth();

  const [nodes, setNodes] = useState([]);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [autoRotate, setAutoRotate] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedRoleFilter, setSelectedRoleFilter] = useState('ALL');
  const [dimensions, setDimensions] = useState({ width: 800, height: 580 });
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Measure container dimensions
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.clientWidth || 800,
          height: isFullscreen ? window.innerHeight - 40 : (containerRef.current.clientHeight || 580)
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, [isFullscreen]);

  // Load nodes from API based on role
  const loadNodes = useCallback(async () => {
    try {
      const nodeList = await api.nodes.list(role);
      setNodes(Array.isArray(nodeList) ? nodeList : []);
    } catch (err) {
      console.error('Failed to load topology nodes:', err);
    }
  }, [role]);

  useEffect(() => {
    loadNodes();
  }, [loadNodes]);

  const isSuperAdmin = role === 'super-admin';

  // Build Graph Data (Nodes + Mesh Links)
  const graphData = useMemo(() => {
    if (!nodes.length) return { nodes: [], links: [] };

    // Filter nodes by search and role
    const filtered = nodes.filter((n) => {
      const matchesSearch =
        (n.name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (n.overlay_ipv4 || '').includes(searchQuery);
      const matchesRole =
        selectedRoleFilter === 'ALL' ||
        (selectedRoleFilter === 'PEERED' && (n.is_peered || n.role === 'PEERED')) ||
        (selectedRoleFilter === 'QUARANTINED' && (n.is_quarantined || (n.risk_score || 0) > 75)) ||
        n.role === selectedRoleFilter;
      return matchesSearch && matchesRole;
    });

    const graphNodes = [];
    const graphLinks = [];

    if (isSuperAdmin) {
      // Super-Admin Global Mesh View
      filtered.forEach((node) => {
        const isQuarantined = Boolean(node.is_quarantined || (node.risk_score || 0) > 75);
        const isPeered = Boolean(node.is_peered || node.role === 'PEERED');
        let nodeColor = '#38bdf8'; // Client Sky
        let nodeVal = 7;

        if (isQuarantined) {
          nodeColor = '#ef4444'; // Critical Red
          nodeVal = 9;
        } else if (isPeered) {
          nodeColor = '#a855f7'; // Purple Peered
          nodeVal = 8;
        } else if (node.role === 'RELAY') {
          nodeColor = '#10b981'; // Emerald Relay
          nodeVal = 12;
        } else if (node.role === 'EXIT_BRIDGE') {
          nodeColor = '#6366f1'; // Indigo Exit
          nodeVal = 9;
        } else if (node.role === 'HYBRID') {
          nodeColor = '#06b6d4'; // Cyan Hybrid
          nodeVal = 8;
        }

        graphNodes.push({
          id: node.id,
          name: node.name,
          role: node.role,
          overlay_ipv4: node.overlay_ipv4,
          country_code: node.country_code,
          city: node.city,
          latency_ms: node.latency_ms || 14.5,
          risk_score: node.risk_score || 0,
          is_quarantined: isQuarantined,
          is_peered: isPeered,
          val: nodeVal,
          color: nodeColor,
          rawNode: node
        });
      });

      // Backbone Relay Links
      const relays = graphNodes.filter((n) => n.role === 'RELAY');
      for (let i = 0; i < relays.length; i++) {
        for (let j = i + 1; j < relays.length; j++) {
          graphLinks.push({
            source: relays[i].id,
            target: relays[j].id,
            color: 'rgba(16, 185, 129, 0.65)',
            curvature: 0.1,
            particles: 4,
            speed: 0.008
          });
        }
      }

      // Connect Non-Relay nodes to closest Relay
      graphNodes.forEach((node, idx) => {
        if (node.role !== 'RELAY' && relays.length > 0) {
          const nearestRelay = relays[idx % relays.length];
          let linkColor = 'rgba(56, 189, 248, 0.4)';
          let particles = 2;
          let speed = 0.005;

          if (node.is_quarantined) {
            linkColor = 'rgba(239, 68, 68, 0.35)';
            particles = 0;
          } else if (node.is_peered) {
            linkColor = 'rgba(168, 85, 247, 0.6)';
            particles = 3;
            speed = 0.006;
          } else if (node.role === 'EXIT_BRIDGE') {
            linkColor = 'rgba(99, 102, 241, 0.5)';
            particles = 3;
          }

          graphLinks.push({
            source: nearestRelay.id,
            target: node.id,
            color: linkColor,
            curvature: 0.15,
            particles,
            speed
          });
        }
      });
    } else {
      // Regular User Isolated Mesh View (Alice)
      const designatedRelay = {
        id: 'relay-iad-core',
        name: 'neronet-relay-iad-01',
        role: 'RELAY',
        overlay_ipv4: '100.64.0.1',
        country_code: 'US',
        city: 'Ashburn',
        latency_ms: 12.0,
        risk_score: 5,
        is_quarantined: false,
        is_peered: false,
        val: 14,
        color: '#10b981'
      };
      graphNodes.push(designatedRelay);

      filtered.forEach((node) => {
        if (node.id === designatedRelay.id) return;
        const isQuarantined = Boolean(node.is_quarantined || (node.risk_score || 0) > 75);
        const nodeColor = isQuarantined ? '#ef4444' : node.role === 'HYBRID' ? '#06b6d4' : '#38bdf8';

        const userGraphNode = {
          id: node.id,
          name: node.name,
          role: node.role,
          overlay_ipv4: node.overlay_ipv4,
          country_code: node.country_code,
          city: node.city,
          latency_ms: node.latency_ms || 18.0,
          risk_score: node.risk_score || 0,
          is_quarantined: isQuarantined,
          is_peered: false,
          val: 8,
          color: nodeColor,
          rawNode: node
        };
        graphNodes.push(userGraphNode);

        // Direct link to designated relay
        graphLinks.push({
          source: designatedRelay.id,
          target: node.id,
          color: isQuarantined ? 'rgba(239, 68, 68, 0.4)' : 'rgba(56, 189, 248, 0.65)',
          curvature: 0.1,
          particles: isQuarantined ? 0 : 3,
          speed: 0.007
        });
      });

      // P2P direct mesh link between Alice's devices
      const clientNodes = graphNodes.filter((n) => n.id !== designatedRelay.id);
      if (clientNodes.length >= 2) {
        graphLinks.push({
          source: clientNodes[0].id,
          target: clientNodes[1].id,
          color: 'rgba(99, 102, 241, 0.55)',
          curvature: 0.2,
          particles: 2,
          speed: 0.009
        });
      }
    }

    return { nodes: graphNodes, links: graphLinks };
  }, [nodes, isSuperAdmin, searchQuery, selectedRoleFilter]);

  // Handle smooth camera float on node hover
  const handleNodeHover = useCallback(
    (node) => {
      setHoveredNode(node || null);
      if (node && fgRef.current) {
        // Smooth camera float toward the hovered node
        const distance = 140;
        const distRatio = 1 + distance / Math.hypot(node.x || 1, node.y || 1, node.z || 1);
        fgRef.current.cameraPosition(
          {
            x: (node.x || 0) * distRatio,
            y: (node.y || 0) * distRatio + 15,
            z: (node.z || 0) * distRatio
          },
          node, // lookAt target
          1200 // 1.2s smooth tween
        );
      }
    },
    []
  );

  // Handle node click -> triggers right-side NodeActions drawer
  const handleNodeClick = useCallback(
    (node) => {
      if (node && onSelectNode) {
        const fullNode = node.rawNode || nodes.find((n) => n.id === node.id) || node;
        onSelectNode(fullNode);
      }
    },
    [nodes, onSelectNode]
  );

  // Reset Camera View
  const handleResetCamera = useCallback(() => {
    if (fgRef.current) {
      fgRef.current.cameraPosition({ x: 0, y: 0, z: 320 }, { x: 0, y: 0, z: 0 }, 1000);
    }
  }, []);

  // Custom 3D Object Rendering for Nodes (Three.js Spheres, Halos, Pulsing Shells)
  const nodeThreeObject = useCallback((node) => {
    const group = new THREE.Group();

    // Core Sphere
    const radius = node.role === 'RELAY' ? 6.5 : node.val * 0.65;
    const geometry = new THREE.SphereGeometry(radius, 24, 24);
    const material = new THREE.MeshPhongMaterial({
      color: new THREE.Color(node.color),
      emissive: new THREE.Color(node.color),
      emissiveIntensity: 0.45,
      shininess: 80,
      transparent: true,
      opacity: 0.95
    });
    const sphere = new THREE.Mesh(geometry, material);
    group.add(sphere);

    // Glowing Halo Shell
    const haloGeometry = new THREE.SphereGeometry(radius * 1.35, 16, 16);
    const haloMaterial = new THREE.MeshBasicMaterial({
      color: new THREE.Color(node.color),
      transparent: true,
      opacity: 0.22,
      wireframe: true
    });
    const halo = new THREE.Mesh(haloGeometry, haloMaterial);
    group.add(halo);

    // High Risk (>75) or Quarantined: Red Pulsing Outer Ring
    if (node.is_quarantined || (node.risk_score || 0) > 75) {
      const dangerGeometry = new THREE.TorusGeometry(radius * 1.9, 0.7, 8, 24);
      const dangerMaterial = new THREE.MeshBasicMaterial({
        color: new THREE.Color('#ef4444'),
        transparent: true,
        opacity: 0.85
      });
      const dangerRing = new THREE.Mesh(dangerGeometry, dangerMaterial);
      dangerRing.rotation.x = Math.PI / 2;
      group.add(dangerRing);
    }

    // Peered Nodes: Purple Outer Gyro Ring
    if (node.is_peered) {
      const peerGeometry = new THREE.TorusGeometry(radius * 1.7, 0.5, 8, 24);
      const peerMaterial = new THREE.MeshBasicMaterial({
        color: new THREE.Color('#a855f7'),
        transparent: true,
        opacity: 0.8
      });
      const peerRing = new THREE.Mesh(peerGeometry, peerMaterial);
      peerRing.rotation.y = Math.PI / 3;
      group.add(peerRing);
    }

    return group;
  }, []);

  return (
    <div className={`space-y-4 ${isFullscreen ? 'fixed inset-0 z-50 bg-dark-canvas p-6' : ''}`}>
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
            <Globe2 className="w-5 h-5 text-accent-primary animate-pulse" />
            <span>Interactive 3D Spiderweb Topology</span>
            <span
              className={`text-xs font-mono px-2 py-0.5 rounded border ${
                isSuperAdmin
                  ? 'bg-accent-primary/20 text-accent-primary border-accent-primary/40'
                  : 'bg-neon-emerald/20 text-neon-emerald border-neon-emerald/40'
              }`}
            >
              {isSuperAdmin ? 'Global Mesh (Super-Admin)' : 'Isolated Mesh (Tenant)'}
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            {isSuperAdmin
              ? 'Physics-based 3D graph: Regional Relays, Exit Gateways, Cross-Mesh Peering, and quarantined devices.'
              : 'Zero-Knowledge scoped view: Strictly Alice’s personal devices connected to regional relay.'}
          </p>
        </div>

        {/* Filters and Search Bar */}
        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Filter node or VIP..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8 pr-3 py-1.5 text-xs bg-dark-card border border-dark-border rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-accent-primary font-mono w-44 sm:w-56"
            />
          </div>

          <select
            value={selectedRoleFilter}
            onChange={(e) => setSelectedRoleFilter(e.target.value)}
            className="px-2.5 py-1.5 text-xs bg-dark-card border border-dark-border rounded-lg text-slate-200 focus:outline-none focus:border-accent-primary font-mono"
          >
            <option value="ALL">All Roles</option>
            <option value="RELAY">Relays (Emerald)</option>
            <option value="EXIT_BRIDGE">Exits (Indigo)</option>
            <option value="CLIENT_ORIGIN">Clients (Sky)</option>
            <option value="PEERED">Peered (Purple)</option>
            <option value="QUARANTINED">High Risk / Quarantined (Red)</option>
          </select>

          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-2 rounded-lg bg-dark-card border border-dark-border text-slate-400 hover:text-white transition-colors"
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* 3D Force Graph Viewport */}
      <div
        ref={containerRef}
        className="relative w-full h-[580px] rounded-2xl bg-dark-canvas border border-dark-border overflow-hidden shadow-2xl group"
      >
        <ForceGraph3D
          ref={fgRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={graphData}
          backgroundColor="#0f172a"
          showNavInfo={false}
          nodeThreeObject={nodeThreeObject}
          nodeLabel={(node) => `${node.name} (${node.overlay_ipv4})`}
          onNodeHover={handleNodeHover}
          onNodeClick={handleNodeClick}
          linkWidth={1.4}
          linkColor={(link) => link.color}
          linkCurvature={(link) => link.curvature || 0}
          linkDirectionalParticles={(link) => link.particles || 0}
          linkDirectionalParticleSpeed={(link) => link.speed || 0.005}
          linkDirectionalParticleWidth={2.4}
          linkDirectionalParticleColor={(link) => link.color}
          enableNodeDrag={true}
          enableNavigationControls={true}
          controlType="orbit"
        />

        {/* HUD Top Left: Active Stats */}
        <div className="absolute top-4 left-4 p-3.5 rounded-xl bg-dark-card/90 border border-dark-border/80 backdrop-blur-md text-xs font-mono space-y-1.5 pointer-events-none shadow-xl">
          <div className="flex items-center space-x-2 text-slate-200 font-bold">
            <Layers className="w-4 h-4 text-accent-primary" />
            <span>{isSuperAdmin ? 'SCOPE: GLOBAL MESH' : 'SCOPE: TENANT ISOLATED'}</span>
          </div>
          <div className="text-[11px] text-slate-400 space-y-0.5 pt-1">
            <div className="flex justify-between space-x-4">
              <span>Rendered Nodes:</span>
              <strong className="text-white">{graphData.nodes.length}</strong>
            </div>
            <div className="flex justify-between space-x-4">
              <span>Active Circuits:</span>
              <strong className="text-accent-primary">{graphData.links.length}</strong>
            </div>
            <div className="flex justify-between space-x-4">
              <span>Engine:</span>
              <strong className="text-emerald-400">Three.js WebGL Force-3D</strong>
            </div>
          </div>
        </div>

        {/* HUD Top Right: Controls */}
        <div className="absolute top-4 right-4 flex items-center space-x-1.5 p-1.5 rounded-xl bg-dark-card/90 border border-dark-border/80 backdrop-blur-md shadow-xl">
          <button
            onClick={() => {
              if (fgRef.current) {
                const controls = fgRef.current.controls();
                if (controls) {
                  controls.autoRotate = !autoRotate;
                  setAutoRotate(!autoRotate);
                }
              }
            }}
            className={`p-2 rounded-lg text-xs font-mono transition-all ${
              autoRotate
                ? 'bg-accent-primary/20 text-accent-primary border border-accent-primary/40'
                : 'text-slate-400 hover:text-white'
            }`}
            title="Toggle Auto-Rotation"
          >
            {autoRotate ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={handleResetCamera}
            className="p-2 rounded-lg text-slate-400 hover:text-white text-xs hover:bg-dark-border/60 transition-colors"
            title="Reset Perspective"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* HUD Bottom Left: Color Legend */}
        <div className="absolute bottom-4 left-4 p-3 rounded-xl bg-dark-card/90 border border-dark-border/80 backdrop-blur-md text-[11px] font-mono space-y-1.5 pointer-events-none shadow-xl">
          <div className="text-slate-400 font-bold mb-1 flex items-center space-x-1.5">
            <Info className="w-3 h-3 text-slate-400" />
            <span>3D Topology Legend</span>
          </div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1">
            <div className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
              <span className="text-slate-300">Regional Relay</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-500"></span>
              <span className="text-slate-300">Exit Gateway</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-sky-400"></span>
              <span className="text-slate-300">Client Device</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-500"></span>
              <span className="text-purple-300 font-semibold">Peered Node</span>
            </div>
            <div className="flex items-center space-x-1.5 col-span-2">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-ping"></span>
              <span className="text-red-400 font-semibold">Risk &gt; 75 / Quarantined</span>
            </div>
          </div>
        </div>

        {/* Hover Tooltip HUD */}
        {hoveredNode && (
          <div className="absolute bottom-4 right-4 p-4 rounded-xl bg-dark-card/95 border border-accent-primary/50 backdrop-blur-md text-xs font-mono shadow-2xl pointer-events-none min-w-[250px] animate-in fade-in duration-100">
            <div className="flex items-center justify-between border-b border-dark-border pb-1.5 mb-2">
              <span className="font-bold text-slate-100">{hoveredNode.name}</span>
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded border ${
                  hoveredNode.is_quarantined
                    ? 'bg-red-500/20 text-red-400 border-red-500/40'
                    : hoveredNode.is_peered
                    ? 'bg-purple-500/20 text-purple-300 border-purple-500/40'
                    : 'bg-accent-primary/20 text-accent-primary border-accent-primary/40'
                }`}
              >
                {hoveredNode.is_peered ? 'PEERED' : hoveredNode.role}
              </span>
            </div>
            <div className="space-y-1 text-[11px] text-slate-400">
              <div className="flex justify-between">
                <span>Overlay IPv4:</span>
                <span className="text-slate-200">{hoveredNode.overlay_ipv4}</span>
              </div>
              <div className="flex justify-between">
                <span>Location:</span>
                <span className="text-slate-200">
                  {hoveredNode.country_code} ({hoveredNode.city || 'Regional'})
                </span>
              </div>
              <div className="flex justify-between">
                <span>Wire Latency:</span>
                <span className="text-emerald-400 font-bold">{hoveredNode.latency_ms} ms</span>
              </div>
              <div className="flex justify-between">
                <span>Behavioral Risk:</span>
                <span
                  className={
                    (hoveredNode.risk_score || 0) > 75
                      ? 'text-red-400 font-bold'
                      : (hoveredNode.risk_score || 0) >= 40
                      ? 'text-amber-400 font-bold'
                      : 'text-emerald-400'
                  }
                >
                  {hoveredNode.risk_score || 0} / 100
                </span>
              </div>
              <div className="flex justify-between">
                <span>Zero-Trust Posture:</span>
                <span className={hoveredNode.is_quarantined ? 'text-red-400 font-bold' : 'text-emerald-400'}>
                  {hoveredNode.is_quarantined ? 'QUARANTINED (100.64.250.0/24)' : 'Compliant'}
                </span>
              </div>
            </div>
            <div className="mt-2.5 pt-2 border-t border-dark-border text-[10px] text-accent-primary font-bold text-center">
              Click Node to Open Action Drawer &rarr;
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
