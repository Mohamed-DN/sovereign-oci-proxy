import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  X,
  Radio,
  ShieldAlert,
  ShieldCheck,
  Compass,
  Zap,
  Activity,
  Server,
  Lock,
  Unlock,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  RotateCw,
  Copy,
  Check
} from 'lucide-react';

export default function NodeActions({ node, isOpen, onClose, onNodeUpdated, onNodeRevoked }) {
  const [currentNode, setCurrentNode] = useState(node);
  const [pingHistory, setPingHistory] = useState([]);
  const [isPinging, setIsPinging] = useState(false);
  const [pingStats, setPingStats] = useState(null);
  const [isUpdatingExit, setIsUpdatingExit] = useState(false);
  const [isTogglingOnion, setIsTogglingOnion] = useState(false);
  const [isQuarantining, setIsQuarantining] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);

  useEffect(() => {
    setCurrentNode(node);
    setPingHistory([]);
    setPingStats(null);
  }, [node]);

  if (!isOpen || !currentNode) return null;

  const handlePing = async () => {
    setIsPinging(true);
    try {
      const res = await api.nodes.action(currentNode.id, 'ping');
      if (res && res.result) {
        const newPing = {
          seq: pingHistory.length + 1,
          rtt: res.result.rtt_ms,
          jitter: res.result.jitter_ms,
          timestamp: new Date().toLocaleTimeString()
        };
        const updatedHistory = [...pingHistory.slice(-9), newPing];
        setPingHistory(updatedHistory);
        setPingStats(res.result);
      }
    } catch (err) {
      console.error('Ping failed:', err);
    } finally {
      setIsPinging(false);
    }
  };

  const handleToggleExit = async () => {
    setIsUpdatingExit(true);
    try {
      const res = await api.nodes.action(currentNode.id, 'set_exit');
      if (res && res.node) {
        setCurrentNode(res.node);
        if (onNodeUpdated) onNodeUpdated(res.node);
      }
    } catch (err) {
      console.error('Exit toggle failed:', err);
    } finally {
      setIsUpdatingExit(false);
    }
  };

  const handleToggleOnion = async () => {
    setIsTogglingOnion(true);
    try {
      const res = await api.nodes.action(currentNode.id, 'toggle_onion');
      if (res && res.node) {
        setCurrentNode(res.node);
        if (onNodeUpdated) onNodeUpdated(res.node);
      }
    } catch (err) {
      console.error('Onion toggle failed:', err);
    } finally {
      setIsTogglingOnion(false);
    }
  };

  const handleToggleQuarantine = async () => {
    setIsQuarantining(true);
    try {
      const actionType = currentNode.is_quarantined ? 'lift_quarantine' : 'quarantine';
      const res = await api.nodes.action(currentNode.id, actionType, {
        reason: "Manual operator security lockdown via Management Console"
      });
      if (res && res.node) {
        setCurrentNode(res.node);
        if (onNodeUpdated) onNodeUpdated(res.node);
      }
    } catch (err) {
      console.error('Quarantine action failed:', err);
    } finally {
      setIsQuarantining(false);
    }
  };

  const handleRevoke = async () => {
    if (window.confirm(`Are you sure you want to permanently revoke node "${currentNode.name}" from the mesh?`)) {
      await api.nodes.action(currentNode.id, 'revoke');
      if (onNodeRevoked) onNodeRevoked(currentNode.id);
      onClose();
    }
  };

  const handleCopyKey = (key) => {
    navigator.clipboard.writeText(key);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const isExitNode = currentNode.role === 'EXIT_BRIDGE';
  const isOnionEnabled = Boolean(currentNode.onion_routing_enabled || currentNode.onion_hops > 0);
  const isQuarantined = !!currentNode.is_quarantined;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-xs flex justify-end animate-in fade-in duration-150">
      <div className="w-full max-w-lg bg-dark-card border-l border-dark-border h-full flex flex-col shadow-2xl overflow-y-auto">
        {/* Drawer Header */}
        <div className="p-5 border-b border-dark-border flex items-center justify-between bg-dark-canvas/60 sticky top-0 z-10 backdrop-blur-md">
          <div className="flex items-center space-x-3">
            <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${
              isQuarantined
                ? 'bg-neon-rose/10 border-neon-rose/40 text-neon-rose glow-rose'
                : 'bg-neon-cyan/10 border-neon-cyan/40 text-neon-cyan glow-cyan'
            }`}>
              <Server className="w-5 h-5" />
            </div>
            <div>
              <div className="font-bold text-sm text-slate-100 flex items-center space-x-2">
                <span>{currentNode.name}</span>
                {isQuarantined ? (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neon-rose/20 text-neon-rose border border-neon-rose/40 font-semibold">
                    QUARANTINED
                  </span>
                ) : isExitNode ? (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/40 font-semibold">
                    EXIT NODE
                  </span>
                ) : (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neon-emerald/20 text-neon-emerald border border-neon-emerald/40 font-semibold">
                    HEALTHY
                  </span>
                )}
              </div>
              <div className="text-xs font-mono text-slate-400">
                {currentNode.overlay_ipv4} &bull; {currentNode.country_code} &bull; ASN {currentNode.asn || 0}
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-dark-card-hover transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Drawer Content */}
        <div className="p-5 space-y-6 flex-1">
          {/* Identity & Crypto Card */}
          <div className="p-4 rounded-xl bg-dark-canvas border border-dark-border space-y-3">
            <div className="text-xs font-semibold text-slate-300 flex items-center justify-between">
              <span>Cryptographic Identity</span>
              <span className="text-[10px] font-mono text-slate-500">Noise_IKpsk2</span>
            </div>

            <div className="space-y-2 text-xs font-mono">
              <div>
                <div className="text-[10px] text-slate-500">Public Key (Curve25519)</div>
                <div className="flex items-center justify-between bg-dark-card p-1.5 rounded border border-dark-border/80 mt-0.5">
                  <span className="truncate text-slate-300 text-[11px]">{currentNode.public_key}</span>
                  <button
                    onClick={() => handleCopyKey(currentNode.public_key)}
                    className="p-1 text-slate-400 hover:text-white"
                  >
                    {copiedKey ? <Check className="w-3.5 h-3.5 text-neon-emerald" /> : <Copy className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2 pt-1">
                <div>
                  <div className="text-[10px] text-slate-500">Overlay IPv6</div>
                  <div className="text-[11px] text-neon-indigo truncate">{currentNode.overlay_ipv6}</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500">Traffic Class</div>
                  <div className="text-[11px] text-slate-300">{currentNode.ip_class}</div>
                </div>
              </div>
            </div>
          </div>

          {/* Action 1: Live Ping Device */}
          <div className="p-4 rounded-xl bg-dark-canvas border border-dark-border space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Radio className={`w-4 h-4 ${isPinging ? 'text-neon-cyan animate-spin' : 'text-neon-cyan'}`} />
                <span className="text-xs font-semibold text-slate-200">Live Device Ping (RTT)</span>
              </div>
              <button
                onClick={handlePing}
                disabled={isPinging || isQuarantined}
                className="px-3 py-1 rounded bg-neon-cyan/20 text-neon-cyan border border-neon-cyan/40 hover:bg-neon-cyan/30 text-xs font-mono font-bold transition-all disabled:opacity-40 flex items-center space-x-1.5"
              >
                <RotateCw className={`w-3 h-3 ${isPinging ? 'animate-spin' : ''}`} />
                <span>{isPinging ? 'Pinging...' : 'Ping Node'}</span>
              </button>
            </div>

            {/* Sparkline / Ping History Bar */}
            {pingHistory.length > 0 ? (
              <div className="space-y-2">
                <div className="h-16 flex items-end space-x-1 p-2 bg-dark-card rounded-lg border border-dark-border">
                  {pingHistory.map((p, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center group relative">
                      <div
                        className="w-full rounded-t bg-gradient-to-t from-neon-cyan to-neon-indigo transition-all duration-300 group-hover:brightness-125"
                        style={{ height: `${Math.min(100, (p.rtt / 60) * 100)}%` }}
                      ></div>
                      <div className="text-[9px] font-mono text-slate-500 mt-1">{p.rtt}ms</div>
                    </div>
                  ))}
                </div>

                {pingStats && (
                  <div className="grid grid-cols-4 gap-2 text-center text-xs font-mono p-2 bg-dark-card/50 rounded border border-dark-border/60">
                    <div>
                      <div className="text-[9px] text-slate-500">LAST RTT</div>
                      <div className="text-neon-cyan font-bold">{pingStats.rtt_ms}ms</div>
                    </div>
                    <div>
                      <div className="text-[9px] text-slate-500">JITTER</div>
                      <div className="text-neon-indigo font-bold">{pingStats.jitter_ms}ms</div>
                    </div>
                    <div>
                      <div className="text-[9px] text-slate-500">MIN / MAX</div>
                      <div className="text-slate-300 font-bold">{pingStats.min_ms}/{pingStats.max_ms}</div>
                    </div>
                    <div>
                      <div className="text-[9px] text-slate-500">LOSS</div>
                      <div className="text-neon-emerald font-bold">{pingStats.packet_loss_pct}%</div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-slate-500 font-mono italic">
                {isQuarantined ? "Node is quarantined. ICMP echo requests dropped by Zero-Trust firewall." : "Click 'Ping Node' to measure real-time wire-level round-trip latency and jitter."}
              </p>
            )}
          </div>

          {/* Action 2: Set as Exit Node */}
          <div className="p-4 rounded-xl bg-dark-canvas border border-dark-border space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Compass className="w-4 h-4 text-neon-indigo" />
                <div>
                  <div className="text-xs font-semibold text-slate-200">Sovereign Exit Node</div>
                  <div className="text-[11px] text-slate-400">Route WAN egress through this node</div>
                </div>
              </div>
              <button
                onClick={handleToggleExit}
                disabled={isUpdatingExit || isQuarantined}
                className={`px-3 py-1.5 rounded text-xs font-mono font-bold transition-all border ${
                  isExitNode
                    ? 'bg-neon-indigo/30 text-neon-indigo border-neon-indigo shadow-[0_0_12px_rgba(99,102,241,0.3)]'
                    : 'bg-dark-card border-dark-border text-slate-400 hover:text-white'
                } disabled:opacity-40`}
              >
                {isUpdatingExit ? 'Updating...' : isExitNode ? 'Active Exit' : 'Set as Exit'}
              </button>
            </div>

            <div className="space-y-1.5 text-[11px] font-mono text-slate-400 bg-dark-card p-2.5 rounded-lg border border-dark-border/80">
              <div className="flex items-center justify-between">
                <span>DNS Leak Guard:</span>
                <span className="text-neon-emerald font-bold">100.64.0.1 (Internal)</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Egress IP Masking:</span>
                <span className="text-slate-200">{currentNode.country_code} ({currentNode.city || 'Regional'})</span>
              </div>
            </div>
          </div>

          {/* Action: 3-Hop Onion Obfuscation */}
          <div className="p-4 rounded-xl bg-dark-canvas border border-dark-border space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Zap className={`w-4 h-4 ${isOnionEnabled ? 'text-neon-cyan' : 'text-slate-400'}`} />
                <div>
                  <div className="text-xs font-semibold text-slate-200">3-Hop Onion Obfuscation</div>
                  <div className="text-[11px] text-slate-400">Tor-grade multi-hop traffic circuit routing</div>
                </div>
              </div>
              <button
                onClick={handleToggleOnion}
                disabled={isTogglingOnion || isQuarantined}
                className={`px-3 py-1.5 rounded text-xs font-mono font-bold transition-all border ${
                  isOnionEnabled
                    ? 'bg-neon-cyan/20 text-neon-cyan border-neon-cyan shadow-[0_0_12px_rgba(6,182,212,0.3)]'
                    : 'bg-dark-card border-dark-border text-slate-400 hover:text-white'
                } disabled:opacity-40`}
              >
                {isTogglingOnion ? 'Toggling...' : isOnionEnabled ? '3 Hops Active' : 'Direct (0-Hop)'}
              </button>
            </div>

            <div className="space-y-1.5 text-[11px] font-mono text-slate-400 bg-dark-card p-2.5 rounded-lg border border-dark-border/80">
              <div className="flex items-center justify-between">
                <span>Routing Circuit Hops:</span>
                <span className={`font-bold ${isOnionEnabled ? 'text-neon-cyan' : 'text-slate-300'}`}>
                  {isOnionEnabled ? '3 Relays (Multi-Hop)' : 'Direct Egress (0-Hop)'}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span>Latency Impact:</span>
                <span className={isOnionEnabled ? 'text-neon-amber' : 'text-neon-emerald'}>
                  {isOnionEnabled ? '+35ms (Tor-grade Privacy)' : '0ms (Lowest Latency)'}
                </span>
              </div>
            </div>
          </div>

          {/* Action 3: Quarantine / Posture Isolation */}
          <div className={`p-4 rounded-xl border space-y-3 ${
            isQuarantined
              ? 'bg-neon-rose/10 border-neon-rose/40'
              : 'bg-dark-canvas border-dark-border'
          }`}>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <ShieldAlert className={`w-4 h-4 ${isQuarantined ? 'text-neon-rose' : 'text-slate-400'}`} />
                <div>
                  <div className={`text-xs font-semibold ${isQuarantined ? 'text-neon-rose' : 'text-slate-200'}`}>
                    Zero-Trust Quarantine
                  </div>
                  <div className="text-[11px] text-slate-400">Instantly isolate node from mesh circuits</div>
                </div>
              </div>
              <button
                onClick={handleToggleQuarantine}
                disabled={isQuarantining}
                className={`px-3 py-1.5 rounded text-xs font-mono font-bold transition-all border flex items-center space-x-1.5 ${
                  isQuarantined
                    ? 'bg-neon-emerald/20 text-neon-emerald border-neon-emerald/40 hover:bg-neon-emerald/30'
                    : 'bg-neon-rose/20 text-neon-rose border-neon-rose/40 hover:bg-neon-rose/30 shadow-[0_0_12px_rgba(244,63,94,0.25)]'
                }`}
              >
                {isQuarantined ? <Unlock className="w-3.5 h-3.5" /> : <Lock className="w-3.5 h-3.5" />}
                <span>{isQuarantining ? 'Processing...' : isQuarantined ? 'Lift Quarantine' : 'Quarantine'}</span>
              </button>
            </div>

            {isQuarantined && currentNode.quarantine_reason && (
              <div className="p-2 rounded bg-dark-card border border-neon-rose/30 text-[11px] font-mono text-neon-rose">
                <strong>Reason:</strong> {currentNode.quarantine_reason}
              </div>
            )}
          </div>
        </div>

        {/* Drawer Footer: Revoke Device */}
        <div className="p-4 border-t border-dark-border bg-dark-canvas/80 flex items-center justify-between sticky bottom-0">
          <button
            onClick={handleRevoke}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded bg-dark-card border border-neon-rose/30 text-neon-rose hover:bg-neon-rose/20 text-xs font-mono transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Revoke Device</span>
          </button>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded bg-dark-border text-slate-300 hover:text-white text-xs font-mono transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
