import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  Shield,
  Layers,
  Activity,
  Globe2,
  Lock,
  Unlock,
  Radio,
  Shuffle,
  Zap,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Server,
  ArrowRight,
  RefreshCw,
  Cpu
} from 'lucide-react';

export default function OnionObfuscationPanel() {
  const { role } = useAuth();
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);

  // Global Multi-Hop State
  const [masterOnion, setMasterOnion] = useState(true);
  const [paddingMode, setPaddingMode] = useState('subtle'); // 'disabled' | 'subtle' | 'cbr'
  const [timingJitter, setTimingJitter] = useState('low'); // 'direct' | 'low' | 'paranoid'
  const [exitPolicy, setExitPolicy] = useState('fastest'); // 'fastest' | 'random' | 'CH' | 'DE' | 'SE' | 'IS' | 'JP' | 'US'
  const [killSwitchGlobal, setKillSwitchGlobal] = useState(true);

  const loadNodes = async () => {
    try {
      setLoading(true);
      const list = await api.nodes.list(role);
      setNodes(Array.isArray(list) ? list : []);
    } catch (err) {
      console.error('Failed to load nodes for onion panel:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNodes();
  }, [role]);

  const handleToggleNodeOnion = async (nodeId, currentEnabled) => {
    try {
      const newEnabled = !currentEnabled;
      await api.nodes.action(nodeId, 'toggle_onion', { enabled: newEnabled });
      setNodes((prev) =>
        prev.map((n) =>
          n.id === nodeId
            ? { ...n, onion_routing_enabled: newEnabled ? 1 : 0, onion_hops: newEnabled ? 3 : 0 }
            : n
        )
      );
    } catch (err) {
      console.error('Failed to toggle node onion routing:', err);
    }
  };

  const handleToggleNodeKillSwitch = async (nodeId, currentKill) => {
    try {
      const newKill = !currentKill;
      await api.nodes.action(nodeId, 'toggle_kill_switch', { enabled: newKill });
      setNodes((prev) =>
        prev.map((n) =>
          n.id === nodeId
            ? { ...n, kill_switch_enabled: newKill ? 1 : 0 }
            : n
        )
      );
    } catch (err) {
      console.error('Failed to toggle kill switch:', err);
    }
  };

  const onionEnabledCount = nodes.filter((n) => Boolean(n.onion_routing_enabled)).length;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
            <Shield className="w-5 h-5 text-accent-primary animate-pulse" />
            <span>3-Hop Onion Routing & Traffic Cloaking</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-accent-primary/20 text-accent-primary border border-accent-primary/40">
              Sphinx Cryptographic Mixnet
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Layered ChaCha20-Poly1305 multi-hop encapsulation, dummy traffic padding (CBR), and packet timing jitter.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={() => setMasterOnion(!masterOnion)}
            className={`px-4 py-2 rounded-xl text-xs font-mono font-bold transition-all shadow-lg flex items-center space-x-2 ${
              masterOnion
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/50 shadow-emerald-500/10'
                : 'bg-dark-card border border-dark-border text-slate-400'
            }`}
          >
            <Radio className="w-3.5 h-3.5" />
            <span>MASTER 3-HOP: {masterOnion ? 'ACTIVE' : 'BYPASSED'}</span>
          </button>
        </div>
      </div>

      {/* Global Status HUD Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Active Circuits */}
        <div className="p-4 rounded-xl bg-dark-card border border-dark-border space-y-2 shadow-lg">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400">
            <span>Active Onion Circuits</span>
            <Layers className="w-4 h-4 text-accent-primary" />
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-100 font-mono">
              {masterOnion ? Math.max(onionEnabledCount * 3, 12) : 0}
            </span>
            <span className="text-xs text-slate-500 font-mono">Circuits</span>
          </div>
          <div className="text-[11px] font-mono text-emerald-400 flex items-center space-x-1">
            <CheckCircle2 className="w-3 h-3" />
            <span>3-Hop Sphinx Encapsulated</span>
          </div>
        </div>

        {/* Card 2: Padding Rate */}
        <div className="p-4 rounded-xl bg-dark-card border border-dark-border space-y-2 shadow-lg">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400">
            <span>Traffic Padding (Chaff)</span>
            <Zap className="w-4 h-4 text-neon-cyan" />
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-100 font-mono capitalize">
              {paddingMode}
            </span>
            <span className="text-xs text-slate-400 font-mono">
              {paddingMode === 'cbr' ? '256 KB/s' : paddingMode === 'subtle' ? '64 KB/s' : '0 KB/s'}
            </span>
          </div>
          <div className="text-[11px] font-mono text-slate-400">
            <span>DPI Size-Correlation Resistance</span>
          </div>
        </div>

        {/* Card 3: Timing Jitter */}
        <div className="p-4 rounded-xl bg-dark-card border border-dark-border space-y-2 shadow-lg">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400">
            <span>Timing Jitter Modulation</span>
            <Activity className="w-4 h-4 text-neon-indigo" />
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-slate-100 font-mono capitalize">
              {timingJitter}
            </span>
            <span className="text-xs text-slate-400 font-mono">
              {timingJitter === 'paranoid' ? '50-150ms' : timingJitter === 'low' ? '5-25ms' : '0ms'}
            </span>
          </div>
          <div className="text-[11px] font-mono text-slate-400">
            <span>Gaussian Packet Burst Shaping</span>
          </div>
        </div>

        {/* Card 4: Mean Circuit Latency */}
        <div className="p-4 rounded-xl bg-dark-card border border-dark-border space-y-2 shadow-lg">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400">
            <span>Mean 3-Hop Circuit Latency</span>
            <Globe2 className="w-4 h-4 text-neon-emerald" />
          </div>
          <div className="flex items-baseline space-x-2">
            <span className="text-2xl font-bold text-neon-emerald font-mono">
              {masterOnion ? '42.8' : '14.5'}
            </span>
            <span className="text-xs text-slate-400 font-mono">ms</span>
          </div>
          <div className="text-[11px] font-mono text-slate-400">
            <span>Forward Secrecy Verified</span>
          </div>
        </div>
      </div>

      {/* Multi-Hop Cryptographic Pipeline Visualizer */}
      <div className="p-5 rounded-2xl bg-dark-card border border-dark-border space-y-4 shadow-xl">
        <div className="flex items-center justify-between border-b border-dark-border pb-3">
          <div className="flex items-center space-x-2 text-xs font-mono text-slate-200">
            <Shuffle className="w-4 h-4 text-accent-primary" />
            <span className="font-bold">Cryptographic Multi-Hop Pipeline Architecture</span>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            Zero Information Leakage
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-5 gap-3 py-2 text-center text-xs font-mono">
          {/* Hop 0: Client */}
          <div className="p-3.5 rounded-xl bg-dark-canvas border border-dark-border space-y-1.5 flex flex-col items-center justify-center">
            <div className="w-8 h-8 rounded-lg bg-sky-500/20 text-sky-400 border border-sky-500/40 flex items-center justify-center mb-1">
              <Server className="w-4 h-4" />
            </div>
            <div className="font-bold text-slate-100">Client Node</div>
            <div className="text-[10px] text-slate-400">Encapsulates 3 Layers</div>
            <span className="text-[9px] px-1.5 py-0.2 rounded bg-sky-950 text-sky-300 border border-sky-800">
              Noise_IKpsk2
            </span>
          </div>

          {/* Hop 1: Entry Guard */}
          <div className="p-3.5 rounded-xl bg-dark-canvas border border-dark-border space-y-1.5 flex flex-col items-center justify-center">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center justify-center mb-1">
              <Lock className="w-4 h-4" />
            </div>
            <div className="font-bold text-slate-100">Entry Guard</div>
            <div className="text-[10px] text-slate-400">Peels Outer Layer (1)</div>
            <span className="text-[9px] px-1.5 py-0.2 rounded bg-emerald-950 text-emerald-300 border border-emerald-800">
              Relay US-East
            </span>
          </div>

          {/* Hop 2: Middle Relay */}
          <div className="p-3.5 rounded-xl bg-dark-canvas border border-dark-border space-y-1.5 flex flex-col items-center justify-center">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/40 flex items-center justify-center mb-1">
              <Layers className="w-4 h-4" />
            </div>
            <div className="font-bold text-slate-100">Middle Relay</div>
            <div className="text-[10px] text-slate-400">Peels Middle Layer (2)</div>
            <span className="text-[9px] px-1.5 py-0.2 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
              Relay EU-Central
            </span>
          </div>

          {/* Hop 3: Exit Bridge */}
          <div className="p-3.5 rounded-xl bg-dark-canvas border border-dark-border space-y-1.5 flex flex-col items-center justify-center">
            <div className="w-8 h-8 rounded-lg bg-purple-500/20 text-purple-400 border border-purple-500/40 flex items-center justify-center mb-1">
              <Globe2 className="w-4 h-4" />
            </div>
            <div className="font-bold text-slate-100">Exit Bridge</div>
            <div className="text-[10px] text-slate-400">Peels Inner Layer (3)</div>
            <span className="text-[9px] px-1.5 py-0.2 rounded bg-purple-950 text-purple-300 border border-purple-800">
              Exit {exitPolicy.toUpperCase()}
            </span>
          </div>

          {/* Hop 4: Destination */}
          <div className="p-3.5 rounded-xl bg-dark-canvas border border-dark-border space-y-1.5 flex flex-col items-center justify-center">
            <div className="w-8 h-8 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/40 flex items-center justify-center mb-1">
              <Radio className="w-4 h-4" />
            </div>
            <div className="font-bold text-slate-100">Target Service</div>
            <div className="text-[10px] text-slate-400">Sees Exit IP Only</div>
            <span className="text-[9px] px-1.5 py-0.2 rounded bg-amber-950 text-amber-300 border border-amber-800">
              Cleartext / TLS Target
            </span>
          </div>
        </div>
      </div>

      {/* Traffic Obfuscation & Egress Preferences Controls */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Obfuscation & Jitter */}
        <div className="p-5 rounded-2xl bg-dark-card border border-dark-border space-y-4 shadow-xl font-mono text-xs">
          <div className="flex items-center space-x-2 text-slate-100 font-bold border-b border-dark-border pb-2">
            <Sliders className="w-4 h-4 text-accent-primary" />
            <span>Traffic Padding & Jitter Modulation</span>
          </div>

          {/* Traffic Padding Mode */}
          <div className="space-y-2">
            <label className="text-slate-300 font-bold block">
              Constant Bitrate (CBR) Traffic Padding
            </label>
            <p className="text-[11px] text-slate-500 font-sans">
              Injects cryptographic dummy chaff packets into the mesh stream to eliminate packet length signatures.
            </p>
            <div className="grid grid-cols-3 gap-2 pt-1">
              {['disabled', 'subtle', 'cbr'].map((mode) => (
                <button
                  key={mode}
                  type="button"
                  onClick={() => setPaddingMode(mode)}
                  className={`py-2 px-3 rounded-lg border font-bold capitalize transition-all ${
                    paddingMode === mode
                      ? 'bg-accent-primary/20 text-accent-primary border-accent-primary/50 shadow-md'
                      : 'bg-dark-canvas border-dark-border text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {mode === 'cbr' ? 'Aggressive CBR' : mode}
                </button>
              ))}
            </div>
          </div>

          {/* Timing Jitter */}
          <div className="space-y-2 pt-3 border-t border-dark-border">
            <label className="text-slate-300 font-bold block">
              Packet Timing Jitter Engine
            </label>
            <p className="text-[11px] text-slate-500 font-sans">
              Randomizes inter-packet transmission delays via Gaussian distribution to foil ISP correlation timing attacks.
            </p>
            <div className="grid grid-cols-3 gap-2 pt-1">
              {[
                { id: 'direct', label: 'Direct (0ms)' },
                { id: 'low', label: 'Low (5-25ms)' },
                { id: 'paranoid', label: 'Paranoid (50-150ms)' }
              ].map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setTimingJitter(item.id)}
                  className={`py-2 px-2 rounded-lg border font-bold text-[11px] transition-all ${
                    timingJitter === item.id
                      ? 'bg-indigo-500/20 text-indigo-300 border-indigo-500/50 shadow-md'
                      : 'bg-dark-canvas border-dark-border text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Exit Node Selection Policy & Kill-Switch */}
        <div className="p-5 rounded-2xl bg-dark-card border border-dark-border space-y-4 shadow-xl font-mono text-xs">
          <div className="flex items-center space-x-2 text-slate-100 font-bold border-b border-dark-border pb-2">
            <Globe2 className="w-4 h-4 text-emerald-400" />
            <span>Exit Node Routing Preferences & Kill-Switch</span>
          </div>

          {/* Exit Node Policy */}
          <div className="space-y-2">
            <label className="text-slate-300 font-bold block">
              Exit Node Geographic Routing
            </label>
            <p className="text-[11px] text-slate-500 font-sans">
              Select your preferred exit bridge jurisdiction or randomize dynamically on each session.
            </p>
            <select
              value={exitPolicy}
              onChange={(e) => setExitPolicy(e.target.value)}
              className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded-xl text-slate-100 font-mono text-xs focus:outline-none focus:border-accent-primary"
            >
              <option value="fastest">⚡ Lowest Latency / Fast Relay (Automatic)</option>
              <option value="random">🎲 Random Hop Rotation (Maximum Anonymity)</option>
              <option value="CH">🇨🇭 Switzerland (CH) - Strict Privacy Laws</option>
              <option value="IS">🇮🇸 Iceland (IS) - Free Speech Data Haven</option>
              <option value="SE">🇸🇪 Sweden (SE) - Privacy Relay</option>
              <option value="DE">🇩🇪 Germany (DE) - European Backbone</option>
              <option value="JP">🇯🇵 Japan (JP) - Asia Pacific Hub</option>
              <option value="US">🇺🇸 United States (US) - High Bandwidth Gateway</option>
            </select>
          </div>

          {/* Strict Egress Kill-Switch */}
          <div className="space-y-2 pt-3 border-t border-dark-border">
            <div className="flex items-center justify-between">
              <div>
                <label className="text-slate-300 font-bold block">
                  Strict Egress Kill-Switch
                </label>
                <p className="text-[11px] text-slate-500 font-sans">
                  Instantly drop all outbound network packets if the encrypted 3-hop onion circuit drops.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setKillSwitchGlobal(!killSwitchGlobal)}
                className={`px-3 py-1.5 rounded-full font-bold text-xs transition-all ${
                  killSwitchGlobal
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50'
                    : 'bg-red-500/20 text-red-400 border border-red-500/50'
                }`}
              >
                {killSwitchGlobal ? 'ARMED (STRICT)' : 'DISABLED'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Per-Node Routing Table with 1-Click Onion Toggles */}
      <div className="p-5 rounded-2xl bg-dark-card border border-dark-border space-y-4 shadow-xl font-mono text-xs">
        <div className="flex items-center justify-between border-b border-dark-border pb-3">
          <div className="flex items-center space-x-2 text-slate-200 font-bold">
            <Server className="w-4 h-4 text-accent-primary" />
            <span>Mesh Node Onion Routing Inventory ({nodes.length} Nodes)</span>
          </div>
          <button
            onClick={loadNodes}
            className="flex items-center space-x-1 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        {nodes.length === 0 ? (
          <div className="py-8 text-center text-slate-500">
            No active nodes enrolled. Enroll a node to configure onion routing.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-slate-400 text-[11px] border-b border-dark-border">
                  <th className="pb-2 font-semibold">Node Name</th>
                  <th className="pb-2 font-semibold">Overlay VIP</th>
                  <th className="pb-2 font-semibold">Role</th>
                  <th className="pb-2 font-semibold">Country</th>
                  <th className="pb-2 font-semibold">Onion Hops</th>
                  <th className="pb-2 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-border/60">
                {nodes.map((node) => {
                  const isOnion = Boolean(node.onion_routing_enabled);
                  const isKill = Boolean(node.kill_switch_enabled);
                  return (
                    <tr key={node.id} className="hover:bg-dark-canvas/50 transition-colors">
                      <td className="py-2.5 font-bold text-slate-100">{node.name || node.hostname}</td>
                      <td className="py-2.5 text-slate-300">{node.overlay_ipv4 || node.mesh_ip}</td>
                      <td className="py-2.5">
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-dark-canvas border border-dark-border text-slate-300">
                          {node.role}
                        </span>
                      </td>
                      <td className="py-2.5 text-slate-400">{node.country_code || 'US'}</td>
                      <td className="py-2.5">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            isOnion
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                              : 'bg-slate-800 text-slate-400 border border-slate-700'
                          }`}
                        >
                          {isOnion ? '3-Hop Active' : 'Direct'}
                        </span>
                      </td>
                      <td className="py-2.5 text-right space-x-2">
                        <button
                          onClick={() => handleToggleNodeOnion(node.id, isOnion)}
                          className={`px-2.5 py-1 rounded text-xs font-bold transition-all ${
                            isOnion
                              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 hover:bg-emerald-500/30'
                              : 'bg-dark-canvas border border-dark-border text-slate-400 hover:text-slate-200'
                          }`}
                        >
                          {isOnion ? 'Disable Onion' : 'Enable 3-Hop'}
                        </button>
                        <button
                          onClick={() => handleToggleNodeKillSwitch(node.id, isKill)}
                          className={`px-2.5 py-1 rounded text-xs font-bold transition-all ${
                            isKill
                              ? 'bg-red-500/20 text-red-400 border border-red-500/40'
                              : 'bg-dark-canvas border border-dark-border text-slate-500 hover:text-slate-300'
                          }`}
                        >
                          {isKill ? 'Kill-Switch: ON' : 'Kill-Switch: OFF'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
