import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  MapPin,
  Globe,
  ShieldAlert,
  ShieldCheck,
  Lock,
  Unlock,
  AlertTriangle,
  Sliders,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Search,
  Filter,
  Layers,
  Radio
} from 'lucide-react';

const COUNTRY_COORDINATES = {
  US: { name: 'United States', x: 200, y: 160, region: 'NA' },
  CA: { name: 'Canada', x: 190, y: 110, region: 'NA' },
  DE: { name: 'Germany', x: 490, y: 140, region: 'EU' },
  GB: { name: 'United Kingdom', x: 460, y: 130, region: 'EU' },
  FR: { name: 'France', x: 470, y: 160, region: 'EU' },
  CH: { name: 'Switzerland', x: 485, y: 165, region: 'EU' },
  NL: { name: 'Netherlands', x: 475, y: 135, region: 'EU' },
  SE: { name: 'Sweden', x: 505, y: 105, region: 'EU' },
  JP: { name: 'Japan', x: 800, y: 180, region: 'APAC' },
  SG: { name: 'Singapore', x: 730, y: 280, region: 'APAC' },
  AU: { name: 'Australia', x: 810, y: 340, region: 'APAC' },
  BR: { name: 'Brazil', x: 310, y: 290, region: 'LATAM' },
  IN: { name: 'India', x: 670, y: 220, region: 'APAC' },
  RU: { name: 'Russia', x: 660, y: 110, region: 'EMEA' },
  CN: { name: 'China', x: 730, y: 180, region: 'APAC' },
  IR: { name: 'Iran', x: 580, y: 190, region: 'MENA' },
  KP: { name: 'North Korea', x: 775, y: 175, region: 'APAC' }
};

export default function GeoFencingMap() {
  const [policies, setPolicies] = useState([]);
  const [selectedCountry, setSelectedCountry] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  const loadPolicies = async () => {
    try {
      const list = await api.geofencing.listPolicies();
      setPolicies(Array.isArray(list) ? list : []);
      if (!selectedCountry && list?.length) {
        setSelectedCountry(list[0]);
      }
    } catch (err) {
      console.error('Failed to load geofencing policies:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPolicies();
  }, []);

  const handleUpdatePolicy = async (countryCode, newAction, egressAllowed = true) => {
    try {
      const updated = await api.geofencing.updatePolicy(countryCode, newAction, egressAllowed);
      setPolicies((prev) =>
        prev.map((p) => (p.country_code === countryCode ? updated : p))
      );
      if (selectedCountry?.country_code === countryCode) {
        setSelectedCountry(updated);
      }
    } catch (err) {
      console.error('Failed to update country policy:', err);
    }
  };

  const handleBulkSet = async (action) => {
    const updatedPolicies = policies.map((p) => ({
      country_code: p.country_code,
      action
    }));
    await api.geofencing.bulkUpdatePolicies(updatedPolicies);
    loadPolicies();
  };

  const filteredPolicies = policies.filter(
    (p) =>
      p.country_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.country_code.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getPolicyColor = (action) => {
    switch (action) {
      case 'ALLOW':
        return '#10b981'; // emerald
      case 'BLOCK':
        return '#ef4444'; // red
      case 'QUARANTINE':
        return '#f59e0b'; // amber
      default:
        return '#64748b'; // slate
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
            <MapPin className="w-5 h-5 text-accent-primary" />
            <span>Geo-Fencing 2D Map & PostGIS Policies</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-accent-primary/20 text-accent-primary border border-accent-primary/40">
              ISO-3166 Policy Engine
            </span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Country-level egress routing, zero-trust perimeter enforcement, and ingress blocking backed by PostGIS spatial queries.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => handleBulkSet('ALLOW')}
            className="px-3 py-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 hover:bg-emerald-500/30 text-xs font-mono font-bold"
          >
            Allow All
          </button>
          <button
            onClick={() => handleBulkSet('QUARANTINE')}
            className="px-3 py-1.5 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/40 hover:bg-amber-500/30 text-xs font-mono font-bold"
          >
            Strict Mode
          </button>
        </div>
      </div>

      {/* Interactive 2D World Map Viewport */}
      <div className="rounded-2xl bg-dark-card border border-dark-border p-5 shadow-2xl space-y-4">
        <div className="flex items-center justify-between border-b border-dark-border pb-3">
          <div className="flex items-center space-x-2 text-xs font-mono text-slate-300">
            <Globe className="w-4 h-4 text-accent-primary" />
            <span className="font-bold">Global Mesh Distribution & Policy Overlay</span>
          </div>

          <div className="flex items-center space-x-4 text-xs font-mono">
            <div className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
              <span className="text-slate-300">Allowed</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400"></span>
              <span className="text-slate-300">Quarantine</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-400"></span>
              <span className="text-slate-300">Blocked</span>
            </div>
          </div>
        </div>

        {/* SVG World Map Canvas */}
        <div className="relative w-full h-[360px] bg-slate-950 rounded-xl border border-dark-border overflow-hidden flex items-center justify-center">
          <svg viewBox="0 0 960 460" className="w-full h-full select-none">
            {/* World Map Background Grid */}
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1e293b" strokeWidth="0.8" />
              </pattern>
            </defs>
            <rect width="100%" height="100%" fill="url(#grid)" />

            {/* Continents Outline (Abstract Geometric Shapes) */}
            <path
              d="M 120 80 Q 240 60 280 140 Q 240 220 180 200 Z"
              fill="#1e293b"
              stroke="#334155"
              strokeWidth="1.2"
              opacity="0.6"
            />
            <path
              d="M 260 230 Q 340 250 320 380 Q 250 330 260 230 Z"
              fill="#1e293b"
              stroke="#334155"
              strokeWidth="1.2"
              opacity="0.6"
            />
            <path
              d="M 430 70 Q 560 60 550 180 Q 450 200 430 70 Z"
              fill="#1e293b"
              stroke="#334155"
              strokeWidth="1.2"
              opacity="0.6"
            />
            <path
              d="M 450 190 Q 540 200 520 340 Q 430 290 450 190 Z"
              fill="#1e293b"
              stroke="#334155"
              strokeWidth="1.2"
              opacity="0.6"
            />
            <path
              d="M 570 70 Q 850 60 840 230 Q 600 240 570 70 Z"
              fill="#1e293b"
              stroke="#334155"
              strokeWidth="1.2"
              opacity="0.6"
            />
            <path
              d="M 740 300 Q 860 300 840 400 Q 750 390 740 300 Z"
              fill="#1e293b"
              stroke="#334155"
              strokeWidth="1.2"
              opacity="0.6"
            />

            {/* Country Node Pins */}
            {policies.map((p) => {
              const coords = COUNTRY_COORDINATES[p.country_code];
              if (!coords) return null;
              const isSelected = selectedCountry?.country_code === p.country_code;
              const pinColor = getPolicyColor(p.action);

              return (
                <g
                  key={p.country_code}
                  className="cursor-pointer transition-transform hover:scale-125"
                  onClick={() => setSelectedCountry(p)}
                >
                  {/* Ping Animation for Active Node Centroids */}
                  {p.node_count > 0 && (
                    <circle
                      cx={coords.x}
                      cy={coords.y}
                      r={isSelected ? 18 : 12}
                      fill={pinColor}
                      opacity="0.25"
                      className="animate-ping"
                    />
                  )}

                  <circle
                    cx={coords.x}
                    cy={coords.y}
                    r={isSelected ? 9 : 6}
                    fill={pinColor}
                    stroke="#0f172a"
                    strokeWidth="2"
                    filter="drop-shadow(0 0 6px rgba(0,0,0,0.8))"
                  />

                  <text
                    x={coords.x}
                    y={coords.y - 10}
                    fill="#f1f5f9"
                    fontSize="10"
                    fontWeight="bold"
                    textAnchor="middle"
                    className="font-mono pointer-events-none"
                  >
                    {p.country_code} {p.node_count > 0 ? `(${p.node_count})` : ''}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Selected Country Map Floating HUD */}
          {selectedCountry && (
            <div className="absolute bottom-3 left-3 p-3.5 rounded-xl bg-dark-card/90 border border-dark-border backdrop-blur-md text-xs font-mono space-y-1 shadow-2xl">
              <div className="font-bold text-slate-100 flex items-center space-x-2">
                <span>{selectedCountry.country_name}</span>
                <span
                  className="text-[10px] px-1.5 py-0.2 rounded font-bold"
                  style={{
                    backgroundColor: `${getPolicyColor(selectedCountry.action)}20`,
                    color: getPolicyColor(selectedCountry.action)
                  }}
                >
                  {selectedCountry.action}
                </span>
              </div>
              <div className="text-[11px] text-slate-400">
                Active Nodes: <strong className="text-white">{selectedCountry.node_count}</strong> &bull; Egress: <strong className="text-emerald-400">{selectedCountry.egress_allowed ? 'Allowed' : 'Blocked'}</strong>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Country Policy Matrix Table & Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Policy Table (Left 2 cols) */}
        <div className="lg:col-span-2 rounded-2xl bg-dark-card border border-dark-border overflow-hidden shadow-xl">
          <div className="p-4 border-b border-dark-border flex items-center justify-between bg-dark-canvas/50">
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search country or code..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-8 pr-3 py-1.5 text-xs bg-dark-canvas border border-dark-border rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-accent-primary font-mono w-48 sm:w-64"
              />
            </div>
            <span className="text-xs font-mono text-slate-500">
              {filteredPolicies.length} Countries Configured
            </span>
          </div>

          <div className="overflow-x-auto max-h-96 overflow-y-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-dark-canvas/80 text-slate-400 border-b border-dark-border sticky top-0 z-10">
                <tr>
                  <th className="p-3.5">Country</th>
                  <th className="p-3.5">Nodes</th>
                  <th className="p-3.5">Policy Action</th>
                  <th className="p-3.5">Egress Allowed</th>
                  <th className="p-3.5 text-right">Toggle Rule</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dark-border">
                {filteredPolicies.map((p) => {
                  const isSelected = selectedCountry?.country_code === p.country_code;
                  return (
                    <tr
                      key={p.country_code}
                      onClick={() => setSelectedCountry(p)}
                      className={`hover:bg-dark-card-hover/50 transition-colors cursor-pointer ${
                        isSelected ? 'bg-dark-canvas/60' : ''
                      }`}
                    >
                      <td className="p-3.5">
                        <div className="font-bold text-slate-100 flex items-center space-x-1.5">
                          <span className="text-accent-primary font-mono">{p.country_code}</span>
                          <span>{p.country_name}</span>
                        </div>
                      </td>

                      <td className="p-3.5">
                        <span className="text-slate-300 font-bold">{p.node_count}</span>
                      </td>

                      <td className="p-3.5">
                        <span
                          className="inline-block text-[10px] font-bold px-2 py-0.5 rounded border"
                          style={{
                            backgroundColor: `${getPolicyColor(p.action)}20`,
                            color: getPolicyColor(p.action),
                            borderColor: `${getPolicyColor(p.action)}50`
                          }}
                        >
                          {p.action}
                        </span>
                      </td>

                      <td className="p-3.5">
                        <span className={p.egress_allowed ? 'text-emerald-400' : 'text-red-400'}>
                          {p.egress_allowed ? 'YES' : 'BLOCKED'}
                        </span>
                      </td>

                      <td className="p-3.5 text-right" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end space-x-1">
                          <button
                            onClick={() => handleUpdatePolicy(p.country_code, 'ALLOW', true)}
                            className={`px-2 py-1 rounded text-[10px] font-bold ${
                              p.action === 'ALLOW'
                                ? 'bg-emerald-500 text-slate-950'
                                : 'bg-dark-canvas text-slate-400 hover:text-white'
                            }`}
                          >
                            ALLOW
                          </button>
                          <button
                            onClick={() => handleUpdatePolicy(p.country_code, 'QUARANTINE', true)}
                            className={`px-2 py-1 rounded text-[10px] font-bold ${
                              p.action === 'QUARANTINE'
                                ? 'bg-amber-500 text-slate-950'
                                : 'bg-dark-canvas text-slate-400 hover:text-white'
                            }`}
                          >
                            QUAR
                          </button>
                          <button
                            onClick={() => handleUpdatePolicy(p.country_code, 'BLOCK', false)}
                            className={`px-2 py-1 rounded text-[10px] font-bold ${
                              p.action === 'BLOCK'
                                ? 'bg-red-500 text-white'
                                : 'bg-dark-canvas text-slate-400 hover:text-white'
                            }`}
                          >
                            BLOCK
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Country Policy Drawer / Inspector (Right col) */}
        {selectedCountry && (
          <div className="p-5 rounded-2xl bg-dark-card border border-dark-border space-y-4 shadow-xl flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-dark-border pb-3">
                <div>
                  <h3 className="font-bold text-sm text-slate-100 font-mono">
                    {selectedCountry.country_name} ({selectedCountry.country_code})
                  </h3>
                  <div className="text-[11px] text-slate-400 font-mono">
                    PostGIS Spatial Rule Inspector
                  </div>
                </div>
                <span
                  className="text-xs font-mono font-bold px-2 py-0.5 rounded border"
                  style={{
                    backgroundColor: `${getPolicyColor(selectedCountry.action)}20`,
                    color: getPolicyColor(selectedCountry.action),
                    borderColor: `${getPolicyColor(selectedCountry.action)}50`
                  }}
                >
                  {selectedCountry.action}
                </span>
              </div>

              <div className="space-y-2.5 text-xs font-mono">
                <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border space-y-1">
                  <div className="text-slate-400">PostGIS Filter Clause:</div>
                  <div className="text-accent-primary font-bold text-[11px]">
                    ST_Contains(country_boundary, ST_SetSRID(ST_Point(lon, lat), 4326))
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-dark-canvas border border-dark-border space-y-1.5">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Registered Devices:</span>
                    <span className="text-white font-bold">{selectedCountry.node_count} Nodes</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Egress Routing:</span>
                    <span className={selectedCountry.egress_allowed ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>
                      {selectedCountry.egress_allowed ? 'Allowed (Full WAN)' : 'Strictly Dropped'}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Last Policy Push:</span>
                    <span className="text-slate-300">{new Date(selectedCountry.updated_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-dark-border space-y-2">
              <div className="text-xs font-mono text-slate-400 font-semibold">Change Policy Rule:</div>
              <div className="grid grid-cols-3 gap-2 text-xs font-mono font-bold">
                <button
                  onClick={() => handleUpdatePolicy(selectedCountry.country_code, 'ALLOW', true)}
                  className="py-2 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 hover:bg-emerald-500/30 transition-colors"
                >
                  ALLOW
                </button>
                <button
                  onClick={() => handleUpdatePolicy(selectedCountry.country_code, 'QUARANTINE', true)}
                  className="py-2 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/40 hover:bg-amber-500/30 transition-colors"
                >
                  QUARANTINE
                </button>
                <button
                  onClick={() => handleUpdatePolicy(selectedCountry.country_code, 'BLOCK', false)}
                  className="py-2 rounded-lg bg-red-500/20 text-red-400 border border-red-500/40 hover:bg-red-500/30 transition-colors"
                >
                  BLOCK
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
