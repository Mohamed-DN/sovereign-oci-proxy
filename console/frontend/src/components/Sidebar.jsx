import React from 'react';
import {
  LayoutDashboard,
  Globe2,
  Server,
  Share2,
  Users,
  Box,
  ShieldCheck,
  FileText,
  Settings,
  ShieldAlert,
  Cpu,
  Radio
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, nodeCount = 18, quarantinedCount = 1 }) {
  const navItems = [
    { id: 'overview', label: 'Global Overview', icon: LayoutDashboard },
    { id: 'topology', label: '3D Mesh Topology', icon: Globe2, badge: '3D' },
    { id: 'nodes', label: 'Node Matrix', icon: Server, count: nodeCount },
    { id: 'nerodrop', label: 'P2P NeroDrop', icon: Share2, highlight: true },
    { id: 'users', label: 'User Directory', icon: Users },
    { id: 'apps', label: 'App Bundles', icon: Box, count: 4 },
    { id: 'acls', label: 'Zero-Trust ACLs', icon: ShieldCheck },
    { id: 'audit', label: 'Security Audit', icon: FileText, alertCount: quarantinedCount },
    { id: 'settings', label: 'Mesh Settings', icon: Settings }
  ];

  return (
    <aside className="w-64 bg-dark-card border-r border-dark-border flex flex-col justify-between shrink-0 h-screen sticky top-0">
      {/* Brand Header */}
      <div>
        <div className="p-5 border-b border-dark-border/80 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-neon-cyan/20 to-neon-indigo/30 border border-neon-cyan/40 flex items-center justify-center glow-cyan">
              <Radio className="w-5 h-5 text-neon-cyan animate-pulse" />
            </div>
            <div>
              <div className="font-bold text-base tracking-wider bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-400 bg-clip-text text-transparent">
                NERONET
              </div>
              <div className="text-[10px] font-mono tracking-widest text-slate-400 uppercase">
                Sovereign Mesh v4.0
              </div>
            </div>
          </div>
        </div>

        {/* Live Status Banner */}
        <div className="mx-3 my-3 p-2.5 rounded-lg bg-dark-canvas/80 border border-dark-border flex items-center justify-between text-xs font-mono">
          <div className="flex items-center space-x-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-neon-emerald opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-neon-emerald"></span>
            </span>
            <span className="text-slate-300">CORE MESH</span>
          </div>
          <span className="text-neon-emerald text-[11px] font-bold">ONLINE</span>
        </div>

        {/* Nav Links */}
        <nav className="px-3 space-y-1 mt-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all group ${
                  isActive
                    ? 'bg-neon-cyan/10 text-neon-cyan border border-neon-cyan/30 shadow-[0_0_15px_-3px_rgba(6,182,212,0.25)]'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-dark-card-hover border border-transparent'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <Icon className={`w-4 h-4 transition-colors ${isActive ? 'text-neon-cyan' : 'text-slate-500 group-hover:text-slate-300'}`} />
                  <span>{item.label}</span>
                </div>

                <div className="flex items-center space-x-1.5">
                  {item.badge && (
                    <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-neon-indigo/20 text-neon-indigo border border-neon-indigo/40">
                      {item.badge}
                    </span>
                  )}
                  {item.count !== undefined && (
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-dark-border text-slate-400">
                      {item.count}
                    </span>
                  )}
                  {item.alertCount > 0 && (
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-neon-rose/20 text-neon-rose border border-neon-rose/40 animate-pulse">
                      {item.alertCount}
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer System Status */}
      <div className="p-4 border-t border-dark-border/80 bg-dark-canvas/40 space-y-3">
        <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
          <span className="flex items-center space-x-1.5">
            <Cpu className="w-3.5 h-3.5 text-slate-500" />
            <span>DirectFrame Engine</span>
          </span>
          <span className="text-neon-cyan">v4.0.0</span>
        </div>
        <div className="w-full bg-dark-border rounded-full h-1.5 overflow-hidden">
          <div className="bg-gradient-to-r from-neon-cyan to-neon-indigo h-full w-[98.4%]"></div>
        </div>
        <div className="flex justify-between text-[10px] font-mono text-slate-500">
          <span>Health Score: 98.4%</span>
          <span>Zero-Trust: ENFORCED</span>
        </div>
      </div>
    </aside>
  );
}
