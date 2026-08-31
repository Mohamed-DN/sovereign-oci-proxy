import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  ShieldCheck,
  ShieldAlert,
  Sliders,
  Network,
  Plus,
  Trash2,
  CheckCircle2,
  Lock,
  ArrowRight,
  Battery,
  Clock,
  Globe2,
  Sparkles
} from 'lucide-react';

export default function SettingsACL() {
  const [rules, setRules] = useState([]);
  const [isAddingRule, setIsAddingRule] = useState(false);

  // New Rule Form
  const [priority, setPriority] = useState(50);
  const [source, setSource] = useState('tag:developers');
  const [destination, setDestination] = useState('tag:cloud_pc');
  const [portProto, setPortProto] = useState('8443/TCP (WebRTC)');
  const [action, setAction] = useState('ACCEPT');
  const [description, setDescription] = useState('');

  // Posture settings toggles
  const [batteryCutoff, setBatteryCutoff] = useState(true);
  const [dnsLeakGuard, setDnsLeakGuard] = useState(true);
  const [heartbeatTimeoutSec, setHeartbeatTimeoutSec] = useState(60);

  const loadRules = async () => {
    const list = await api.acl.list();
    setRules(list);
  };

  useEffect(() => {
    loadRules();
  }, []);

  const handleCreateRule = async (e) => {
    e.preventDefault();
    await api.acl.create({
      priority,
      source,
      destination,
      port_proto: portProto,
      action,
      description: description || `${action} traffic from ${source} to ${destination}`
    });
    setIsAddingRule(false);
    setDescription('');
    loadRules();
  };

  const handleDeleteRule = async (id) => {
    await api.acl.delete(id);
    loadRules();
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
            <span>Zero-Trust ACL Rules & Network Policies</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-neon-emerald/20 text-neon-emerald border border-neon-emerald/40">
              Kernel WireGuard BPF Enforced
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Declarative security access control matrix, regional subnet failover routes, and posture threshold safeguards.
          </p>
        </div>

        <button
          onClick={() => setIsAddingRule(true)}
          className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-gradient-to-r from-neon-cyan to-neon-indigo text-dark-canvas font-bold font-mono text-xs hover:brightness-110 transition-all shadow-lg"
        >
          <Plus className="w-4 h-4" />
          <span>Add ACL Rule</span>
        </button>
      </div>

      {/* Visual ACL Rules Table */}
      <div className="rounded-xl bg-dark-card border border-dark-border overflow-hidden shadow-xl">
        <div className="p-4 border-b border-dark-border flex items-center justify-between">
          <div className="flex items-center space-x-2 font-bold text-slate-100 font-mono text-sm">
            <ShieldCheck className="w-4 h-4 text-neon-cyan" />
            <span>Active Access Control Matrix</span>
          </div>
          <span className="text-xs font-mono text-slate-500">{rules.length} Rules Enforced</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead className="bg-dark-canvas text-slate-400 uppercase text-[10px] tracking-wider border-b border-dark-border">
              <tr>
                <th className="p-3.5">Priority</th>
                <th className="p-3.5">Source Tag / Group</th>
                <th className="p-3.5">Destination</th>
                <th className="p-3.5">Port & Protocol</th>
                <th className="p-3.5">Action Policy</th>
                <th className="p-3.5">Description</th>
                <th className="p-3.5 text-right">Delete</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-border">
              {rules.map((r) => (
                <tr key={r.id} className="hover:bg-dark-card-hover transition-colors">
                  <td className="p-3.5 font-bold text-slate-200">#{r.priority}</td>
                  <td className="p-3.5 text-neon-cyan font-bold">{r.source}</td>
                  <td className="p-3.5 text-neon-indigo font-bold">{r.destination}</td>
                  <td className="p-3.5 text-slate-300">{r.port_proto}</td>
                  <td className="p-3.5">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      r.action === 'ACCEPT'
                        ? 'bg-neon-emerald/20 text-neon-emerald border border-neon-emerald/40'
                        : 'bg-neon-rose/20 text-neon-rose border border-neon-rose/40'
                    }`}>
                      {r.action}
                    </span>
                  </td>
                  <td className="p-3.5 text-slate-400 max-w-xs truncate">{r.description}</td>
                  <td className="p-3.5 text-right">
                    <button
                      onClick={() => handleDeleteRule(r.id)}
                      className="p-1.5 rounded bg-dark-canvas border border-dark-border text-slate-400 hover:text-neon-rose transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Subnet Route Failover & Posture Policies Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Card 1: Subnet Route Failover */}
        <div className="p-5 rounded-2xl bg-dark-card border border-dark-border space-y-4 shadow-xl">
          <div className="flex items-center space-x-2 font-bold text-slate-100 font-mono text-sm">
            <Network className="w-4 h-4 text-neon-indigo" />
            <span>Subnet Route Failover Priority</span>
          </div>
          <p className="text-xs text-slate-400">
            Autonomous multi-path routing order if regional relay experiences packet loss &gt; 5%.
          </p>

          <div className="space-y-2 text-xs font-mono">
            <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border flex items-center justify-between">
              <span className="text-slate-300">1. US-East (Ashburn IAD)</span>
              <span className="text-neon-emerald font-bold">PRIMARY (12ms)</span>
            </div>
            <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border flex items-center justify-between">
              <span className="text-slate-300">2. EU-Central (Frankfurt FRA)</span>
              <span className="text-neon-cyan font-bold">SECONDARY (20ms)</span>
            </div>
            <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border flex items-center justify-between">
              <span className="text-slate-300">3. AP-East (Tokyo TYO)</span>
              <span className="text-slate-500 font-bold">TERTIARY (38ms)</span>
            </div>
          </div>
        </div>

        {/* Card 2: Posture Engine Thresholds */}
        <div className="p-5 rounded-2xl bg-dark-card border border-dark-border space-y-4 shadow-xl">
          <div className="flex items-center space-x-2 font-bold text-slate-100 font-mono text-sm">
            <Sliders className="w-4 h-4 text-neon-emerald" />
            <span>Zero-Trust Posture Thresholds</span>
          </div>
          <p className="text-xs text-slate-400">
            Automated circuit shutdown and quarantine conditions for client devices.
          </p>

          <div className="space-y-3 text-xs font-mono">
            <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border flex items-center justify-between">
              <div>
                <div className="text-slate-200 font-bold">Battery Cutoff (&lt; 20%)</div>
                <div className="text-[10px] text-slate-500">Disable exit node relaying on low battery</div>
              </div>
              <button
                onClick={() => setBatteryCutoff(!batteryCutoff)}
                className={`px-3 py-1 rounded text-xs font-bold border transition-all ${
                  batteryCutoff
                    ? 'bg-neon-emerald/20 text-neon-emerald border-neon-emerald/40'
                    : 'bg-dark-card text-slate-500 border-dark-border'
                }`}
              >
                {batteryCutoff ? 'ENABLED' : 'DISABLED'}
              </button>
            </div>

            <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border flex items-center justify-between">
              <div>
                <div className="text-slate-200 font-bold">DNS Leak Guard</div>
                <div className="text-[10px] text-slate-500">Force overlay DNS (100.64.0.1) only</div>
              </div>
              <button
                onClick={() => setDnsLeakGuard(!dnsLeakGuard)}
                className={`px-3 py-1 rounded text-xs font-bold border transition-all ${
                  dnsLeakGuard
                    ? 'bg-neon-emerald/20 text-neon-emerald border-neon-emerald/40'
                    : 'bg-dark-card text-slate-500 border-dark-border'
                }`}
              >
                {dnsLeakGuard ? 'ENFORCED' : 'OFF'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Add Rule Modal */}
      {isAddingRule && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="bg-dark-card border border-dark-border rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl p-6 space-y-4">
            <h2 className="text-base font-bold text-slate-100 font-mono flex items-center space-x-2">
              <Plus className="w-4 h-4 text-neon-cyan" />
              <span>Create Zero-Trust ACL Rule</span>
            </h2>

            <form onSubmit={handleCreateRule} className="space-y-4 text-xs font-mono">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 mb-1">Priority (1-100)</label>
                  <input
                    type="number"
                    value={priority}
                    onChange={(e) => setPriority(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded text-slate-100 focus:outline-none focus:border-neon-cyan"
                  />
                </div>
                <div>
                  <label className="block text-slate-400 mb-1">Action</label>
                  <select
                    value={action}
                    onChange={(e) => setAction(e.target.value)}
                    className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded text-slate-100 focus:outline-none focus:border-neon-cyan"
                  >
                    <option value="ACCEPT">ACCEPT</option>
                    <option value="DROP">DROP</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Source Tag / Group / VIP</label>
                <input
                  type="text"
                  required
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded text-slate-100 focus:outline-none focus:border-neon-cyan"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Destination Tag / Group / Subnet</label>
                <input
                  type="text"
                  required
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded text-slate-100 focus:outline-none focus:border-neon-cyan"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Port & Protocol</label>
                <input
                  type="text"
                  required
                  value={portProto}
                  onChange={(e) => setPortProto(e.target.value)}
                  className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded text-slate-100 focus:outline-none focus:border-neon-cyan"
                />
              </div>

              <div>
                <label className="block text-slate-400 mb-1">Rule Description</label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Optional rationale"
                  className="w-full px-3 py-2 bg-dark-canvas border border-dark-border rounded text-slate-100 focus:outline-none focus:border-neon-cyan"
                />
              </div>

              <div className="flex justify-end space-x-3 pt-3">
                <button
                  type="button"
                  onClick={() => setIsAddingRule(false)}
                  className="px-4 py-2 rounded bg-dark-border text-slate-300 text-xs"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded bg-gradient-to-r from-neon-cyan to-neon-indigo text-dark-canvas font-bold text-xs hover:brightness-110"
                >
                  Save Rule
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
